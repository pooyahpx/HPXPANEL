#!/usr/bin/env bash

replace_or_append_env_var() {
    local key="$1"
    local value="$2"
    local quote_value="${3:-false}"
    local target_file="${4:-$ENV_FILE}"
    local formatted_value="$value"
    local escaped_value=""

    if [ "$quote_value" = "true" ]; then
        local sanitized_value="${value//\"/\\\"}"
        formatted_value="\"$sanitized_value\""
    fi

    escaped_value=$(printf '%s' "$formatted_value" | sed -e 's/[&|\\]/\\&/g')

    if grep -q "^$key=" "$target_file"; then
        sed -i "s|^$key=.*|$key=$escaped_value|" "$target_file"
    else
        printf '%s=%s\n' "$key" "$formatted_value" >>"$target_file"
    fi
}

set_or_uncomment_env_var() {
    local key="$1"
    local value="$2"
    local quote_value="${3:-false}"
    local target_file="${4:-$ENV_FILE}"
    local formatted_value="$value"
    local tmp_file=""
    local target_dir=""

    if [ "$quote_value" = "true" ]; then
        local sanitized_value="${value//\"/\\\"}"
        formatted_value="\"$sanitized_value\""
    fi

    [ -f "$target_file" ] || touch "$target_file"
    target_dir=$(dirname "$target_file")
    tmp_file=$(create_temp_file_in_dir "$target_dir" "env-edit" ".tmp")

    # Pass key/value through the environment and read them via ENVIRON so awk
    # does not interpret backslash escapes (-v would turn \t, \n, etc. in the
    # value into a tab/newline).
    env_key="$key" env_line="${key} = ${formatted_value}" awk '
        BEGIN { ekey = ENVIRON["env_key"]; eline = ENVIRON["env_line"]; replaced = 0 }
        {
            if ($0 ~ "^[[:space:]]*#?[[:space:]]*" ekey "[[:space:]]*=") {
                if (replaced == 0) {
                    print eline
                    replaced = 1
                }
                next
            }
            print
        }
        END {
            if (replaced == 0) {
                print eline
            }
        }
    ' "$target_file" >"$tmp_file"

    mv "$tmp_file" "$target_file"
}

comment_out_env_var() {
    local key="$1"
    local target_file="${2:-$ENV_FILE}"
    local tmp_file=""
    local target_dir=""

    [ -f "$target_file" ] || return 0
    target_dir=$(dirname "$target_file")
    tmp_file=$(create_temp_file_in_dir "$target_dir" "env-comment" ".tmp")

    awk -v env_key="$key" '
        BEGIN { done = 0 }
        {
            if ($0 ~ "^[[:space:]]*#?[[:space:]]*" env_key "[[:space:]]*=") {
                if (done == 0) {
                    line = $0
                    sub("^[[:space:]]*#?[[:space:]]*" env_key "[[:space:]]*=[[:space:]]*", "", line)
                    print "# " env_key " = " line
                    done = 1
                }
                next
            }
            print
        }
    ' "$target_file" >"$tmp_file"

    mv "$tmp_file" "$target_file"
}

delete_env_var() {
    local key="$1"
    local target_file="${2:-$ENV_FILE}"

    [ -f "$target_file" ] || return 0
    sed -i "/^[[:space:]]*${key}[[:space:]]*=/d" "$target_file"
}
