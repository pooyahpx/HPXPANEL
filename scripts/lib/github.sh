#!/usr/bin/env bash

SHARED_LIB_INSTALL_DIR="${SHARED_LIB_INSTALL_DIR:-/usr/local/lib/hpxpanel-scripts/lib}"

github_raw_url() {
    local repo="$1"
    local path="$2"

    printf 'https://github.com/%s/raw/main/%s\n' "$repo" "$path"
}

github_download_file() {
    local url="$1"
    local target_path="$2"

    curl -fsSL "$url" -o "$target_path"
}

backup_scripts() {
    local backup_dir=""
    backup_dir=$(create_temp_dir "scripts-backup")

    # Backup main scripts
    [ -f "/usr/local/bin/hpxpanel" ] && cp "/usr/local/bin/hpxpanel" "$backup_dir/"
    [ -f "/usr/local/bin/hpx-node" ] && cp "/usr/local/bin/hpx-node" "$backup_dir/"

    # Backup shared libraries
    if [ -d "$SHARED_LIB_INSTALL_DIR" ]; then
        mkdir -p "$backup_dir/lib"
        # Only copy if directory is not empty
        if [ "$(ls -A "$SHARED_LIB_INSTALL_DIR")" ]; then
            cp -r "$SHARED_LIB_INSTALL_DIR/"* "$backup_dir/lib/"
        fi
    fi

    printf '%s\n' "$backup_dir"
}

restore_scripts() {
    local backup_dir="$1"
    [ -z "$backup_dir" ] && return 1

    # Restore main scripts
    [ -f "$backup_dir/hpxpanel" ] && install -m 755 "$backup_dir/hpxpanel" "/usr/local/bin/hpxpanel"
    [ -f "$backup_dir/hpx-node" ] && install -m 755 "$backup_dir/hpx-node" "/usr/local/bin/hpx-node"

    # Restore shared libraries
    if [ -d "$backup_dir/lib" ]; then
        mkdir -p "$SHARED_LIB_INSTALL_DIR"
        if [ "$(ls -A "$backup_dir/lib")" ]; then
            install -m 644 "$backup_dir/lib/"* "$SHARED_LIB_INSTALL_DIR/"
        fi
    fi
}

cleanup_backup() {
    local backup_dir="$1"
    if [ -n "$backup_dir" ]; then
        rm -rf "$backup_dir"
    fi
}

github_install_script_from_repo() {
    local repo="$1"
    local script_name="$2"
    local install_name="$3"
    local tmp_file=""

    tmp_file=$(mktemp) || return 1
    trap 'rm -f "$tmp_file"' RETURN

    if ! curl -fSL "$(github_raw_url "$repo" "$script_name")" -o "$tmp_file"; then
        trap - RETURN
        rm -f "$tmp_file"
        return 1
    fi

    if ! chmod 755 "$tmp_file"; then
        trap - RETURN
        rm -f "$tmp_file"
        return 1
    fi

    if ! install -m 755 "$tmp_file" "/usr/local/bin/$install_name"; then
        trap - RETURN
        rm -f "$tmp_file"
        return 1
    fi

    trap - RETURN
    rm -f "$tmp_file"
}

install_shared_libs_from_local() {
    local source_dir="$1"
    shift
    local lib_name=""

    mkdir -p "$SHARED_LIB_INSTALL_DIR"
    for lib_name in "$@"; do
        if [ -f "$source_dir/lib/$lib_name" ]; then
            install -m 644 "$source_dir/lib/$lib_name" "$SHARED_LIB_INSTALL_DIR/$lib_name"
        fi
    done
}

install_shared_libs_from_repo() {
    local fetch_repo="$1"
    shift
    local tmp_dir=""
    local lib_name=""

    tmp_dir=$(create_temp_dir "shared-libs")
    mkdir -p "$SHARED_LIB_INSTALL_DIR"

    for lib_name in "$@"; do
        if ! github_download_file "$(github_raw_url "$fetch_repo" "scripts/lib/$lib_name")" "$tmp_dir/$lib_name"; then
            rm -rf "$tmp_dir"
            return 1
        fi
        if ! install -m 644 "$tmp_dir/$lib_name" "$SHARED_LIB_INSTALL_DIR/$lib_name"; then
            rm -rf "$tmp_dir"
            return 1
        fi
    done

    rm -rf "$tmp_dir"
}
