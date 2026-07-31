#!/usr/bin/env bash

colorized_echo() {
    local color="$1"
    local text="$2"
    local style="${3:-0}"

    case "$color" in
    red)
        printf "\e[${style};91m%s\e[0m\n" "$text"
        ;;
    green)
        printf "\e[${style};92m%s\e[0m\n" "$text"
        ;;
    yellow)
        printf "\e[${style};93m%s\e[0m\n" "$text"
        ;;
    blue)
        printf "\e[${style};94m%s\e[0m\n" "$text"
        ;;
    magenta)
        printf "\e[${style};95m%s\e[0m\n" "$text"
        ;;
    cyan)
        printf "\e[${style};96m%s\e[0m\n" "$text"
        ;;
    *)
        printf "%s\n" "$text"
        ;;
    esac
}

die() {
    colorized_echo red "$*"
    exit 1
}

# Ensure a secret-bearing file (e.g. .env, TLS private key) is only readable by
# its owner. Creates the file with 0600 if it is missing so callers can harden
# it *before* writing secrets; tightens it to 0600 if it already exists. A
# truncating writer such as `curl -o` preserves the inode's mode, so writing
# into the pre-created file keeps it private.
harden_secret_file() {
    local path="$1"
    [ -n "$path" ] || return 1
    if [ ! -e "$path" ]; then
        (umask 077 && : >"$path") || return 1
    fi
    chmod 600 "$path"
}

temp_root_dir() {
    local root=""

    if [ -n "${APP_TMP_DIR:-}" ]; then
        root="$APP_TMP_DIR"
    elif [ -n "${DATA_DIR:-}" ]; then
        root="$DATA_DIR/tmp"
    elif [ -n "${APP_NAME:-}" ]; then
        root="/var/lib/$APP_NAME/tmp"
    else
        root="/var/lib/hpxpanel-scripts/tmp"
    fi

    mkdir -p "$root"
    printf '%s\n' "$root"
}

create_temp_dir() {
    local prefix="${1:-tmpdir}"
    local root=""
    local candidate=""
    local attempt=0

    root=$(temp_root_dir)
    while [ "$attempt" -lt 20 ]; do
        candidate="${root}/${prefix}-$$-${RANDOM}-${attempt}"
        if mkdir "$candidate" 2>/dev/null; then
            printf '%s\n' "$candidate"
            return 0
        fi
        attempt=$((attempt + 1))
    done

    die "Failed to create temporary directory in $root"
}

create_temp_file() {
    local prefix="${1:-tmpfile}"
    local suffix="${2:-}"
    local root=""

    root=$(temp_root_dir)
    create_temp_file_in_dir "$root" "$prefix" "$suffix"
}

create_temp_file_in_dir() {
    local dir="$1"
    local prefix="${2:-tmpfile}"
    local suffix="${3:-}"
    local candidate=""
    local attempt=0

    mkdir -p "$dir"
    while [ "$attempt" -lt 20 ]; do
        candidate="${dir}/${prefix}-$$-${RANDOM}-${attempt}${suffix}"
        if (set -C; : >"$candidate") 2>/dev/null; then
            printf '%s\n' "$candidate"
            return 0
        fi
        attempt=$((attempt + 1))
    done

    die "Failed to create temporary file in $dir"
}
