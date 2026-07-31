#!/usr/bin/env bash

mask_telegram_bot_key() {
    local secret="$1"
    local length=${#secret}

    if [ -z "$secret" ]; then
        printf '%s\n' ""
        return 0
    fi

    if [ "$length" -le 6 ]; then
        printf '****%s\n' "$secret"
        return 0
    fi

    printf '****%s\n' "${secret: -6}"
}

filter_backup_cron_entries() {
    local source_file="$1"
    local target_file="$2"

    grep -F -v "# hpxpanel-backup-service" "$source_file" >"$target_file" || true
}

# Convert a backup interval expressed in minutes into a cron schedule.
# Echoes the schedule and returns 0 when the value maps to an evenly-spaced
# schedule; echoes nothing and returns 1 otherwise.
backup_cron_from_interval_minutes() {
    local minutes="$1"

    if ! [[ "$minutes" =~ ^[0-9]+$ ]] || [[ "$minutes" -lt 1 ]]; then
        return 1
    fi

    # Sub-hour: must divide evenly into 60 minutes.
    if [[ "$minutes" -lt 60 ]]; then
        if [[ $((60 % minutes)) -eq 0 ]]; then
            echo "*/$minutes * * * *"
            return 0
        fi
        return 1
    fi

    # Exactly one day: keep the existing daily-at-midnight format.
    if [[ "$minutes" -eq 1440 ]]; then
        echo "0 0 * * *"
        return 0
    fi

    # Between one hour and one day: must be a whole number of hours.
    if [[ "$minutes" -lt 1440 && $((minutes % 60)) -eq 0 ]]; then
        echo "0 */$((minutes / 60)) * * *"
        return 0
    fi

    return 1
}

# Convert a backup cron schedule back into an interval in minutes.
# Echoes the minutes, or an empty string for an unrecognized schedule.
backup_interval_minutes_from_cron() {
    local cron_schedule="$1"

    if [[ "$cron_schedule" == "0 0 * * *" ]]; then
        echo "1440"
        return 0
    fi

    if [[ "$cron_schedule" == "0 * * * *" ]]; then
        echo "60"
        return 0
    fi

    if [[ "$cron_schedule" =~ ^0[[:space:]]+\*/([0-9]+)[[:space:]]+\*[[:space:]]+\*[[:space:]]+\*$ ]]; then
        echo "$(( ${BASH_REMATCH[1]} * 60 ))"
        return 0
    fi

    if [[ "$cron_schedule" =~ ^\*/([0-9]+)[[:space:]]+\*[[:space:]]+\*[[:space:]]+\*[[:space:]]+\*$ ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    echo ""
}

# Render a backup interval (in minutes) as a human-readable string.
# Invalid/empty input echoes the optional fallback (default "Unknown").
format_backup_interval() {
    local minutes="$1"
    local fallback="${2:-Unknown}"

    if ! [[ "$minutes" =~ ^[0-9]+$ ]] || [[ "$minutes" -lt 1 ]]; then
        echo "$fallback"
        return 0
    fi

    if [[ "$minutes" -eq 1440 ]]; then
        echo "Daily at midnight (every 24 hours)"
    elif [[ "$minutes" -ge 120 && $((minutes % 60)) -eq 0 ]]; then
        echo "Every $((minutes / 60)) hours"
    elif [[ "$minutes" -eq 60 ]]; then
        echo "Every hour"
    else
        echo "Every $minutes minutes"
    fi
}

is_local_db_host() {
    local host="${1:-}"

    host="${host#[}"
    host="${host%]}"
    host="${host%.}"
    host="${host,,}"

    [[ -z "$host" ]] && return 1
    [[ "$host" == "localhost" ]] && return 0
    [[ "$host" == "localhost.localdomain" ]] && return 0
    [[ "$host" == "127" ]] && return 0
    [[ "$host" =~ ^127\.([0-9]{1,3}\.){2}[0-9]{1,3}$ ]] && return 0
    [[ "$host" == "::1" ]] && return 0
    [[ "$host" == "0:0:0:0:0:0:0:1" ]] && return 0

    return 1
}

# Stable per-database dump filename for index N (1-based): db-001.sql, db-002.sql ...
pg_dump_index_filename() {
    printf 'db-%03d.sql' "$1"
}

# Encode one manifest line:
#   dbname<TAB>owner<TAB>has_ts<TAB>filename<TAB>ts_version
# ts_version is the source timescaledb extension version (empty for non-timescale
# databases). Rejects (returns 1) any field that would corrupt the TSV.
pg_manifest_encode() {
    local dbname="$1" owner="$2" has_ts="$3" filename="$4" ts_version="${5:-}"
    case "${dbname}${owner}${filename}${ts_version}" in
        *$'\t'* | *$'\n'*) return 1 ;;
    esac
    printf '%s\t%s\t%s\t%s\t%s' "$dbname" "$owner" "$has_ts" "$filename" "$ts_version"
}

send_backup_to_telegram() {
    if [ -f "$ENV_FILE" ]; then
        while IFS='=' read -r key value; do
            if [[ -z "$key" || "$key" =~ ^# ]]; then
                continue
            fi
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            value=$(echo "$value" | sed -E 's/^["'"'"'](.*)["'"'"']$/\1/')
            if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
                export "$key"="$value"
            else
                colorized_echo yellow "Skipping invalid line in .env: $key=$value"
            fi
        done <"$ENV_FILE"
    else
        colorized_echo red "Environment file (.env) not found."
        exit 1
    fi

    if [ "$BACKUP_SERVICE_ENABLED" != "true" ]; then
        colorized_echo yellow "Backup service is not enabled. Skipping Telegram upload."
        return
    fi

    # Validate Telegram configuration
    if [ -z "$BACKUP_TELEGRAM_BOT_KEY" ]; then
        colorized_echo red "Error: BACKUP_TELEGRAM_BOT_KEY is not set in .env file"
        return 1
    fi

    if [ -z "$BACKUP_TELEGRAM_CHAT_ID" ]; then
        colorized_echo red "Error: BACKUP_TELEGRAM_CHAT_ID is not set in .env file"
        return 1
    fi

    local proxy_url=""
    local curl_proxy_args=()
    if proxy_url=$(get_backup_proxy_url); then
        curl_proxy_args=(--proxy "$proxy_url")
    fi

    local server_ip="$(curl "${curl_proxy_args[@]}" -4 -s --max-time 5 ifconfig.me 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')"
    if [ -z "$server_ip" ]; then
        server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    if [ -z "$server_ip" ]; then
        server_ip="Unknown IP"
    fi
    local backup_dir="$APP_DIR/backup"
    local latest_backup=""
    latest_backup=$(find "$backup_dir" -maxdepth 1 -type f \
        \( -name 'backup_*.tar.gz' -o -name 'backup_*.zip' -o -name 'backup_*.z[0-9][0-9]' -o -name 'backup_*.part[0-9][0-9].zip' \) \
        -printf '%T@ %f\n' 2>/dev/null | sort -nr | head -n 1 | cut -d' ' -f2-)

    if [ -z "$latest_backup" ]; then
        colorized_echo red "No backups found to send."
        return 1
    fi

    local backup_paths=()
    local uploaded_files=()
    local cleanup_dir=""
    local extraction_mode="zip"

    local telegram_split_bytes=$((49 * 1000 * 1000))

    if [[ "$latest_backup" =~ \.part[0-9]{2}\.zip$ ]]; then
        extraction_mode="part_zip"
        local base="${latest_backup%%.part*}"
        while IFS= read -r file; do
            [ -n "$file" ] && backup_paths+=("$file")
        done < <(find "$backup_dir" -maxdepth 1 -type f -name "${base}.part*.zip" | sort)
        if [ ${#backup_paths[@]} -eq 0 ]; then
            colorized_echo red "Incomplete backup parts for $base"
            return 1
        fi
    elif [[ "$latest_backup" =~ \.z[0-9]{2}$ ]]; then
        extraction_mode="split_zip"
        local base="${latest_backup%.z??}"
        while IFS= read -r file; do
            [ -n "$file" ] && backup_paths+=("$file")
        done < <(find "$backup_dir" -maxdepth 1 -type f -name "${base}.z[0-9][0-9]" | sort)
        if [ -f "$backup_dir/${base}.zip" ]; then
            backup_paths+=("$backup_dir/${base}.zip")
        else
            colorized_echo red "Missing final .zip file for split archive $base"
            return 1
        fi
    elif [[ "$latest_backup" =~ \.zip$ ]]; then
        local base="${latest_backup%.zip}"
        local split_files=()
        while IFS= read -r file; do
            [ -n "$file" ] && split_files+=("$file")
        done < <(find "$backup_dir" -maxdepth 1 -type f -name "${base}.z[0-9][0-9]" | sort)
        if [ ${#split_files[@]} -gt 0 ]; then
            extraction_mode="split_zip"
            backup_paths=("${split_files[@]}")
        fi
        backup_paths+=("$backup_dir/$latest_backup")
    elif [[ "$latest_backup" =~ \.tar\.gz$ ]]; then
        extraction_mode="tar"
        cleanup_dir="/tmp/hpxpanel_backup_split"
        rm -rf "$cleanup_dir"
        mkdir -p "$cleanup_dir"
        local legacy_backup="$backup_dir/$latest_backup"
        local backup_size=$(du -m "$legacy_backup" | cut -f1)
        if [ "$backup_size" -gt 49 ]; then
            colorized_echo yellow "Legacy backup is larger than 49MB. Splitting before upload..."
            split -b "$telegram_split_bytes" "$legacy_backup" "$cleanup_dir/${latest_backup}_part_"
        else
            cp "$legacy_backup" "$cleanup_dir/$latest_backup"
        fi
        while IFS= read -r file; do
            [ -n "$file" ] && backup_paths+=("$file")
        done < <(find "$cleanup_dir" -maxdepth 1 -type f -print | sort)
        if [ ${#backup_paths[@]} -eq 0 ]; then
            colorized_echo red "Failed to prepare legacy backup for upload."
            rm -rf "$cleanup_dir"
            return 1
        fi
    else
        colorized_echo red "Unsupported backup format: $latest_backup"
        return 1
    fi

    local backup_time=$(date "+%Y-%m-%d %H:%M:%S %Z")

    for part in "${backup_paths[@]}"; do
        local part_name=$(basename "$part")
        local custom_filename="$part_name"

        local escaped_server_ip=$(printf '%s' "$server_ip" | sed 's/[_*\[\]()~`>#+\-=|{}!.]/\\&/g')
        local escaped_filename=$(printf '%s' "$custom_filename" | sed 's/[_*\[\]()~`>#+\-=|{}!.]/\\&/g')
        local escaped_time=$(printf '%s' "$backup_time" | sed 's/[_*\[\]()~`>#+\-=|{}!.]/\\&/g')
        local caption="📦 *Backup Information*\n🌐 *Server IP*: \`$escaped_server_ip\`\n📁 *Backup File*: \`$escaped_filename\`\n⏰ *Backup Time*: \`$escaped_time\`"

        local response=$(curl "${curl_proxy_args[@]}" -s -w "\n%{http_code}" -F chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
            -F document=@"$part;filename=$custom_filename" \
            -F caption="$(printf '%b' "$caption")" \
            -F parse_mode="MarkdownV2" \
            "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendDocument" 2>&1)

        local http_code=$(echo "$response" | tail -n1)
        local response_body=$(echo "$response" | sed '$d')

        if [ "$http_code" == "200" ]; then
            # Check if response contains "ok":true
            if echo "$response_body" | grep -q '"ok":true'; then
                uploaded_files+=("$custom_filename")
                colorized_echo green "Backup part $custom_filename successfully sent to Telegram."
            else
                # Extract error message from Telegram response
                local error_msg=$(echo "$response_body" | grep -o '"description":"[^"]*"' | cut -d'"' -f4 || echo "Unknown error")
                colorized_echo red "Failed to send backup part $custom_filename to Telegram: $error_msg"
                echo "Telegram API status: $http_code" >&2
                echo "Telegram API Response: $response_body" >&2
            fi
        else
            local error_msg=$(echo "$response_body" | grep -o '"description":"[^"]*"' | cut -d'"' -f4 || echo "HTTP $http_code")
            colorized_echo red "Failed to send backup part $custom_filename to Telegram: $error_msg"
            echo "Telegram API Response: $response_body" >&2
        fi
    done

    if [ ${#uploaded_files[@]} -gt 0 ]; then
        local files_list=""
        for file in "${uploaded_files[@]}"; do
            files_list+="- $file"$'\n'
        done
        files_list="${files_list%$'\n'}"

        local info_message=$'📦 Backup Upload Summary\n'
        info_message+=$'──────────────────────\n'
        info_message+="🌐 Server IP: $server_ip"$'\n'
        info_message+="⏰ Time: $backup_time"$'\n'
        info_message+=$'\n✅ Files Uploaded:\n'
        info_message+="$files_list"$'\n'
        info_message+=$'\n📂 Extraction Guide:\n'
        if [ "$extraction_mode" = "part_zip" ]; then
            info_message+=$'🪟 Windows: Rebuild the archive first, e.g. copy /b backup_xxx.part01.zip+backup_xxx.part02.zip+... backup_xxx.zip, then extract backup_xxx.zip with 7-Zip.\n'
            info_message+=$'🐧 Linux: Run cat backup_xxx.part*.zip > backup_xxx.zip && unzip backup_xxx.zip.\n'
            info_message+=$'🍎 macOS: Run cat backup_xxx.part*.zip > backup_xxx.zip && unzip backup_xxx.zip.\n'
            info_message+=$'⚠️ Always download every .partNN.zip file before rebuilding the archive.'
        elif [ "$extraction_mode" = "split_zip" ]; then
            info_message+=$'🪟 Windows: Install and use 7-Zip. Place the .zip and every .zXX part together, then start extraction from the .zip file.\n'
            info_message+=$'🐧 Linux: Run unzip (e.g., unzip backup_xxx.zip) with all .zXX parts in the same directory.\n'
            info_message+=$'🍎 macOS: Use Archive Utility or run unzip backup_xxx.zip from Terminal with the .zXX parts beside the .zip file.\n'
            info_message+=$'⚠️ Always download the .zip and every .zXX part before extracting.'
        else
            info_message+=$'🪟 Windows: Extract the uploaded archive with 7-Zip.\n'
            info_message+=$'🐧 Linux: Run unzip backup_xxx.zip.\n'
            info_message+=$'🍎 macOS: Open the archive with Archive Utility or run unzip backup_xxx.zip.\n'
            info_message+=$'⚠️ Download the complete archive before extracting.'
        fi

        curl "${curl_proxy_args[@]}" -s -X POST "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendMessage" \
            -d chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
            -d text="$info_message" >/dev/null 2>&1 || true
    fi

    if [ -n "$cleanup_dir" ]; then
        rm -rf "$cleanup_dir"
    fi
}

send_backup_error_to_telegram() {
    local error_messages=$1
    local log_file=$2
    local proxy_url=""
    local curl_proxy_args=()
    if proxy_url=$(get_backup_proxy_url); then
        curl_proxy_args=(--proxy "$proxy_url")
    fi
    local server_ip="$(curl "${curl_proxy_args[@]}" -4 -s --max-time 5 ifconfig.me 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$')"
    if [ -z "$server_ip" ]; then
        server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    if [ -z "$server_ip" ]; then
        server_ip="Unknown IP"
    fi
    local error_time=$(date "+%Y-%m-%d %H:%M:%S %Z")
    local message="⚠️ Backup Error Notification
🌐 Server IP: $server_ip
❌ Errors: $error_messages
⏰ Time: $error_time"

    local max_length=1000
    if [ ${#message} -gt $max_length ]; then
        message="${message:0:$((max_length - 25))}...
[Message truncated]"
    fi

    curl "${curl_proxy_args[@]}" -s -X POST "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendMessage" \
        -d chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
        -d text="$message" >/dev/null 2>&1 &&
        colorized_echo green "Backup error notification sent to Telegram." ||
        colorized_echo red "Failed to send error notification to Telegram."

    if [ -f "$log_file" ]; then

        response=$(curl "${curl_proxy_args[@]}" -s -w "%{http_code}" -o /tmp/tg_response.json \
            -F chat_id="$BACKUP_TELEGRAM_CHAT_ID" \
            -F document=@"$log_file;filename=backup_error.log" \
            -F caption="📜 Backup Error Log - $error_time" \
            "https://api.telegram.org/bot$BACKUP_TELEGRAM_BOT_KEY/sendDocument")

        http_code="${response:(-3)}"
        if [ "$http_code" -eq 200 ]; then
            colorized_echo green "Backup error log sent to Telegram."
        else
            colorized_echo red "Failed to send backup error log to Telegram. HTTP code: $http_code"
            cat /tmp/tg_response.json
        fi
    else
        colorized_echo red "Log file not found: $log_file"
    fi
}

backup_service() {
    local telegram_bot_key=""
    local telegram_chat_id=""
    local cron_schedule=""
    local interval_minutes=""
    local backup_proxy_enabled="false"
    local backup_proxy_url=""

    colorized_echo blue "====================================="
    colorized_echo blue "      Welcome to Backup Service      "
    colorized_echo blue "====================================="

    if grep -q "BACKUP_SERVICE_ENABLED=true" "$ENV_FILE"; then
        while true; do
            telegram_bot_key=$(awk -F'=' '/^BACKUP_TELEGRAM_BOT_KEY=/ {print $2}' "$ENV_FILE")
            telegram_chat_id=$(awk -F'=' '/^BACKUP_TELEGRAM_CHAT_ID=/ {print $2}' "$ENV_FILE")
            cron_schedule=$(awk -F'=' '/^BACKUP_CRON_SCHEDULE=/ {print $2}' "$ENV_FILE" | tr -d '"')
            backup_proxy_enabled=$(awk -F'=' '/^BACKUP_PROXY_ENABLED=/ {print $2}' "$ENV_FILE")
            backup_proxy_url=$(awk -F'=' '/^BACKUP_PROXY_URL=/ {print substr($0, index($0,"=")+1); exit}' "$ENV_FILE")
            backup_proxy_url=$(echo "$backup_proxy_url" | sed -e 's/^"//' -e 's/"$//')
            [ -z "$backup_proxy_enabled" ] && backup_proxy_enabled="false"
            local masked_telegram_bot_key=""

            interval_minutes=$(backup_interval_minutes_from_cron "$cron_schedule")

            masked_telegram_bot_key=$(mask_telegram_bot_key "$telegram_bot_key")

            colorized_echo green "====================================="
            colorized_echo green "Current Backup Configuration:"
            colorized_echo cyan "Telegram Bot API Key: $masked_telegram_bot_key"
            colorized_echo cyan "Telegram Chat ID: $telegram_chat_id"
            colorized_echo cyan "Backup Interval: $(format_backup_interval "$interval_minutes" "$cron_schedule")"
            if [[ "$backup_proxy_enabled" == "true" && -n "$backup_proxy_url" ]]; then
                colorized_echo cyan "Proxy: Enabled ($backup_proxy_url)"
            else
                colorized_echo cyan "Proxy: Disabled"
            fi
            colorized_echo green "====================================="
            echo "Choose an option:"
            echo "1. Check Backup Service"
            echo "2. Edit Backup Service"
            echo "3. Reconfigure Backup Service"
            echo "4. Remove Backup Service"
            echo "5. Request Instant Backup"
            echo "6. Exit"
            read -p "Enter your choice (1-6): " user_choice

            case $user_choice in
            1)
                view_backup_service
                echo ""
                ;;
            2)
                edit_backup_service
                echo ""
                ;;
            3)
                colorized_echo yellow "Starting reconfiguration..."
                remove_backup_service
                break
                ;;
            4)
                colorized_echo yellow "Removing Backup Service..."
                remove_backup_service
                return
                ;;
            5)
                colorized_echo yellow "Starting instant backup..."
                backup_command
                colorized_echo green "Instant backup completed."
                echo ""
                ;;
            6)
                colorized_echo yellow "Exiting..."
                return
                ;;
            *)
                colorized_echo red "Invalid choice. Please try again."
                echo ""
                ;;
            esac
        done
    else
        colorized_echo yellow "No backup service is currently configured."
    fi

    while true; do
        printf "Enter your Telegram bot API key: "
        read telegram_bot_key
        if [[ -n "$telegram_bot_key" ]]; then
            break
        else
            colorized_echo red "API key cannot be empty. Please try again."
        fi
    done

    while true; do
        printf "Enter your Telegram chat ID: "
        read telegram_chat_id
        if [[ -n "$telegram_chat_id" ]]; then
            break
        else
            colorized_echo red "Chat ID cannot be empty. Please try again."
        fi
    done

    while true; do
        printf "How often should backups run? Enter minutes\n(e.g. 30 = every 30 min, 60 = hourly, 1440 = once a day): "
        read interval_minutes

        if cron_schedule=$(backup_cron_from_interval_minutes "$interval_minutes"); then
            colorized_echo green "Backups will run: $(format_backup_interval "$interval_minutes")."
            break
        else
            colorized_echo red "Please enter a number that divides evenly into an hour (5, 10, 15, 20, 30) or a whole number of hours (60, 120, 180 ... up to 1440 for once a day)."
        fi
    done

    while true; do
        read -p "Do you need to use an HTTP/SOCKS proxy for Telegram backups? (y/N): " proxy_choice
        case "$proxy_choice" in
        [Yy]*)
            backup_proxy_enabled="true"
            break
            ;;
        [Nn]*|"")
            backup_proxy_enabled="false"
            break
            ;;
        *)
            colorized_echo red "Invalid choice. Please enter y or n."
            ;;
        esac
    done

    if [ "$backup_proxy_enabled" = "true" ]; then
        while true; do
            read -p "Enter proxy URL (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:1080): " backup_proxy_url
            backup_proxy_url=$(echo "$backup_proxy_url" | xargs)
            if [ -z "$backup_proxy_url" ]; then
                colorized_echo red "Proxy URL cannot be empty."
                continue
            fi
            if is_valid_proxy_url "$backup_proxy_url"; then
                break
            else
                colorized_echo red "Invalid proxy URL. Supported prefixes: http://, https://, socks5://, socks5h://, socks4://."
            fi
        done
    else
        backup_proxy_url=""
    fi

    sed -i '/^BACKUP_SERVICE_ENABLED/d' "$ENV_FILE"
    sed -i '/^BACKUP_TELEGRAM_BOT_KEY/d' "$ENV_FILE"
    sed -i '/^BACKUP_TELEGRAM_CHAT_ID/d' "$ENV_FILE"
    sed -i '/^BACKUP_CRON_SCHEDULE/d' "$ENV_FILE"
    sed -i '/^BACKUP_PROXY_ENABLED/d' "$ENV_FILE"
    sed -i '/^BACKUP_PROXY_URL/d' "$ENV_FILE"

    {
        echo ""
        echo "# Backup service configuration"
        echo "BACKUP_SERVICE_ENABLED=true"
        echo "BACKUP_TELEGRAM_BOT_KEY=$telegram_bot_key"
        echo "BACKUP_TELEGRAM_CHAT_ID=$telegram_chat_id"
        echo "BACKUP_CRON_SCHEDULE=\"$cron_schedule\""
        echo "BACKUP_PROXY_ENABLED=$backup_proxy_enabled"
        echo "BACKUP_PROXY_URL=\"$backup_proxy_url\""
    } >>"$ENV_FILE"

    colorized_echo green "Backup service configuration saved in $ENV_FILE."

    # Use full path to the script for cron job
    local script_path="/usr/local/bin/$APP_NAME"
    if [ ! -f "$script_path" ]; then
        script_path=$(which "$APP_NAME" 2>/dev/null || echo "/usr/local/bin/$APP_NAME")
    fi
    # Set PATH for cron to ensure docker and other tools are found
    local backup_command="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin bash $script_path backup"
    add_cron_job "$cron_schedule" "$backup_command"

    colorized_echo green "Backup service successfully configured."

    # Run initial backup
    colorized_echo blue "Running initial backup..."
    backup_command
    if [ $? -eq 0 ]; then
        colorized_echo green "Initial backup completed successfully."
    else
        colorized_echo yellow "Initial backup completed with warnings. Check logs if needed."
    fi
    colorized_echo cyan "Backups will be sent to Telegram: $(format_backup_interval "$interval_minutes")."
    colorized_echo green "====================================="
}

add_cron_job() {
    local schedule="$1"
    local command="$2"
    local temp_cron=$(mktemp)
    local filtered_cron="${temp_cron}.tmp"

    crontab -l 2>/dev/null >"$temp_cron" || true
    filter_backup_cron_entries "$temp_cron" "$filtered_cron"
    mv "$filtered_cron" "$temp_cron"
    echo "$schedule $command # hpxpanel-backup-service" >>"$temp_cron"

    if crontab "$temp_cron"; then
        colorized_echo green "Cron job successfully added."
    else
        colorized_echo red "Failed to add cron job. Please check manually."
    fi
    rm -f "$temp_cron"
}

view_backup_service() {
    if ! grep -q "BACKUP_SERVICE_ENABLED=true" "$ENV_FILE"; then
        colorized_echo red "Backup service is not configured."
        return 1
    fi

    local telegram_bot_key=$(awk -F'=' '/^BACKUP_TELEGRAM_BOT_KEY=/ {print $2}' "$ENV_FILE")
    local telegram_chat_id=$(awk -F'=' '/^BACKUP_TELEGRAM_CHAT_ID=/ {print $2}' "$ENV_FILE")
    local cron_schedule=$(awk -F'=' '/^BACKUP_CRON_SCHEDULE=/ {print $2}' "$ENV_FILE" | tr -d '"')
    local backup_proxy_enabled=$(awk -F'=' '/^BACKUP_PROXY_ENABLED=/ {print $2}' "$ENV_FILE")
    local backup_proxy_url=$(awk -F'=' '/^BACKUP_PROXY_URL=/ {print substr($0, index($0,"=")+1); exit}' "$ENV_FILE")
    backup_proxy_url=$(echo "$backup_proxy_url" | sed -e 's/^"//' -e 's/"$//')
    [ -z "$backup_proxy_enabled" ] && backup_proxy_enabled="false"
    local interval_minutes=""
    local masked_telegram_bot_key=""

    interval_minutes=$(backup_interval_minutes_from_cron "$cron_schedule")

    masked_telegram_bot_key=$(mask_telegram_bot_key "$telegram_bot_key")

    colorized_echo blue "====================================="
    colorized_echo blue "      Backup Service Details         "
    colorized_echo blue "====================================="
    colorized_echo green "Status: Enabled"
    colorized_echo cyan "Telegram Bot API Key: $masked_telegram_bot_key"
    colorized_echo cyan "Telegram Chat ID: $telegram_chat_id"
    colorized_echo cyan "Cron Schedule: $cron_schedule"
    colorized_echo cyan "Backup Interval: $(format_backup_interval "$interval_minutes" "$cron_schedule")"
    if [[ "$backup_proxy_enabled" == "true" && -n "$backup_proxy_url" ]]; then
        colorized_echo cyan "Proxy: Enabled ($backup_proxy_url)"
    else
        colorized_echo cyan "Proxy: Disabled"
    fi
    colorized_echo blue "====================================="
    echo ""
    read -p "Press Enter to continue..."
}

edit_backup_service() {
    if ! grep -q "BACKUP_SERVICE_ENABLED=true" "$ENV_FILE"; then
        colorized_echo red "Backup service is not configured."
        return 1
    fi

    local telegram_bot_key=$(awk -F'=' '/^BACKUP_TELEGRAM_BOT_KEY=/ {print $2}' "$ENV_FILE")
    local telegram_chat_id=$(awk -F'=' '/^BACKUP_TELEGRAM_CHAT_ID=/ {print $2}' "$ENV_FILE")
    local cron_schedule=$(awk -F'=' '/^BACKUP_CRON_SCHEDULE=/ {print $2}' "$ENV_FILE" | tr -d '"')
    local backup_proxy_enabled=$(awk -F'=' '/^BACKUP_PROXY_ENABLED=/ {print $2}' "$ENV_FILE")
    local backup_proxy_url=$(awk -F'=' '/^BACKUP_PROXY_URL=/ {print substr($0, index($0,"=")+1); exit}' "$ENV_FILE")
    backup_proxy_url=$(echo "$backup_proxy_url" | sed -e 's/^"//' -e 's/"$//')
    [ -z "$backup_proxy_enabled" ] && backup_proxy_enabled="false"
    local interval_minutes=""
    local masked_telegram_bot_key=""

    interval_minutes=$(backup_interval_minutes_from_cron "$cron_schedule")

    masked_telegram_bot_key=$(mask_telegram_bot_key "$telegram_bot_key")

    colorized_echo blue "====================================="
    colorized_echo blue "      Edit Backup Service            "
    colorized_echo blue "====================================="
    echo "Current configuration:"
    local proxy_display="Disabled"
    if [[ "$backup_proxy_enabled" == "true" && -n "$backup_proxy_url" ]]; then
        proxy_display="Enabled ($backup_proxy_url)"
    fi
    colorized_echo cyan "1. Telegram Bot API Key: $masked_telegram_bot_key"
    colorized_echo cyan "2. Telegram Chat ID: $telegram_chat_id"
    colorized_echo cyan "3. Backup Interval: $(format_backup_interval "$interval_minutes" "$cron_schedule")"
    colorized_echo cyan "4. Proxy: $proxy_display"
    colorized_echo yellow "5. Cancel"
    echo ""
    read -p "Which setting would you like to edit? (1-5): " edit_choice

    case $edit_choice in
    1)
        while true; do
            printf "Enter new Telegram bot API key [current: %s]: " "$masked_telegram_bot_key"
            read new_bot_key
            if [[ -n "$new_bot_key" ]]; then
                sed -i "s|^BACKUP_TELEGRAM_BOT_KEY=.*|BACKUP_TELEGRAM_BOT_KEY=$new_bot_key|" "$ENV_FILE"
                colorized_echo green "Telegram Bot API Key updated successfully."
                break
            else
                colorized_echo red "API key cannot be empty. Please try again."
            fi
        done
        ;;
    2)
        while true; do
            printf "Enter new Telegram chat ID [current: $telegram_chat_id]: "
            read new_chat_id
            if [[ -n "$new_chat_id" ]]; then
                sed -i "s|^BACKUP_TELEGRAM_CHAT_ID=.*|BACKUP_TELEGRAM_CHAT_ID=$new_chat_id|" "$ENV_FILE"
                colorized_echo green "Telegram Chat ID updated successfully."
                break
            else
                colorized_echo red "Chat ID cannot be empty. Please try again."
            fi
        done
        ;;
    3)
        while true; do
            printf "How often should backups run? Enter minutes\n(e.g. 30 = every 30 min, 60 = hourly, 1440 = once a day) [current: %s]: " "$(format_backup_interval "$interval_minutes" "$cron_schedule")"
            read new_interval_minutes

            local new_cron_schedule=""
            if new_cron_schedule=$(backup_cron_from_interval_minutes "$new_interval_minutes"); then
                colorized_echo green "Backups will run: $(format_backup_interval "$new_interval_minutes")."
            else
                colorized_echo red "Please enter a number that divides evenly into an hour (5, 10, 15, 20, 30) or a whole number of hours (60, 120, 180 ... up to 1440 for once a day)."
                continue
            fi

            sed -i "s|^BACKUP_CRON_SCHEDULE=.*|BACKUP_CRON_SCHEDULE=\"$new_cron_schedule\"|" "$ENV_FILE"

            # Use full path to the script for cron job
            local script_path="/usr/local/bin/$APP_NAME"
            if [ ! -f "$script_path" ]; then
                script_path=$(which "$APP_NAME" 2>/dev/null || echo "/usr/local/bin/$APP_NAME")
            fi
            # Set PATH for cron to ensure docker and other tools are found
            local backup_command="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin bash $script_path backup"
            local temp_cron=$(mktemp)
            local filtered_cron="${temp_cron}.tmp"
            crontab -l 2>/dev/null >"$temp_cron" || true
            filter_backup_cron_entries "$temp_cron" "$filtered_cron"
            mv "$filtered_cron" "$temp_cron"
            echo "$new_cron_schedule $backup_command # hpxpanel-backup-service" >>"$temp_cron"

            if crontab "$temp_cron"; then
                colorized_echo green "Backup interval and cron schedule updated successfully."
            else
                colorized_echo red "Failed to update cron job. Please check manually."
            fi
            rm -f "$temp_cron"
            break
        done
        ;;
    4)
        local new_proxy_enabled="$backup_proxy_enabled"
        local new_proxy_url="$backup_proxy_url"
        while true; do
            read -p "Enable proxy for Telegram backups? (y/N) [current: $proxy_display]: " proxy_choice
            case "$proxy_choice" in
            [Yy]*)
                new_proxy_enabled="true"
                break
                ;;
            [Nn]*|"")
                new_proxy_enabled="false"
                break
                ;;
            *)
                colorized_echo red "Invalid choice. Please enter y or n."
                ;;
            esac
        done

        if [ "$new_proxy_enabled" = "true" ]; then
            while true; do
                read -p "Enter proxy URL (e.g. http://127.0.0.1:8080 or socks5://127.0.0.1:1080) [current: $backup_proxy_url]: " input_proxy_url
                if [ -z "$input_proxy_url" ]; then
                    if [ -n "$backup_proxy_url" ]; then
                        input_proxy_url="$backup_proxy_url"
                    else
                        colorized_echo red "Proxy URL cannot be empty."
                        continue
                    fi
                fi
                input_proxy_url=$(echo "$input_proxy_url" | xargs)
                if is_valid_proxy_url "$input_proxy_url"; then
                    new_proxy_url="$input_proxy_url"
                    break
                else
                    colorized_echo red "Invalid proxy URL. Supported prefixes: http://, https://, socks5://, socks5h://, socks4://."
                fi
            done
        else
            new_proxy_url=""
        fi

        replace_or_append_env_var "BACKUP_PROXY_ENABLED" "$new_proxy_enabled"
        replace_or_append_env_var "BACKUP_PROXY_URL" "$new_proxy_url" true
        colorized_echo green "Backup proxy configuration updated successfully."
        ;;
    5)
        colorized_echo yellow "Edit cancelled."
        return
        ;;
    *)
        colorized_echo red "Invalid choice."
        return
        ;;
    esac

    colorized_echo green "Backup service configuration updated successfully."
}

remove_backup_service() {
    colorized_echo red "in process..."

    sed -i '/^# Backup service configuration/d' "$ENV_FILE"
    sed -i '/BACKUP_SERVICE_ENABLED/d' "$ENV_FILE"
    sed -i '/BACKUP_TELEGRAM_BOT_KEY/d' "$ENV_FILE"
    sed -i '/BACKUP_TELEGRAM_CHAT_ID/d' "$ENV_FILE"
    sed -i '/BACKUP_CRON_SCHEDULE/d' "$ENV_FILE"
    sed -i '/BACKUP_PROXY_ENABLED/d' "$ENV_FILE"
    sed -i '/BACKUP_PROXY_URL/d' "$ENV_FILE"

    local temp_cron=$(mktemp)
    local filtered_cron="${temp_cron}.tmp"
    crontab -l 2>/dev/null >"$temp_cron" || true

    filter_backup_cron_entries "$temp_cron" "$filtered_cron"
    mv "$filtered_cron" "$temp_cron"

    if crontab "$temp_cron"; then
        colorized_echo green "Backup service task removed from crontab."
    else
        colorized_echo red "Failed to update crontab. Please check manually."
    fi

    rm -f "$temp_cron"

    colorized_echo green "Backup service has been removed."
}


# Dump every real user database (plus cluster globals) from a local
# PostgreSQL/TimescaleDB container into <temp_dir>/pg_dump/.
# Layout: globals.sql, db-NNN.sql per database, manifest.tsv
# (dbname<TAB>owner<TAB>has_timescaledb<TAB>filename<TAB>ts_version).
# Returns 0 when at least one database was dumped; otherwise removes the
# pg_dump dir and returns 1 so the caller can fall back to single-database mode.
pg_dump_all_user_databases() {
    local container_name="$1"
    local backup_user="$2"
    local backup_password="$3"
    local temp_dir="$4"
    local log_file="$5"

    local out_dir="$temp_dir/pg_dump"
    local manifest="$out_dir/manifest.tsv"
    mkdir -p "$out_dir" || return 1

    # Cluster-wide roles/grants so owners exist on restore.
    if ! docker exec -e PGPASSWORD="$backup_password" "$container_name" \
        pg_dumpall -U "$backup_user" --globals-only >"$out_dir/globals.sql" 2>>"$log_file"; then
        echo "pg_dumpall --globals-only failed" >>"$log_file"
        rm -rf "$out_dir"
        return 1
    fi

    # Enumerate real user databases (skip templates and the postgres maintenance DB).
    local databases=""
    databases=$(docker exec -e PGPASSWORD="$backup_password" "$container_name" \
        psql -U "$backup_user" -d postgres -At \
        -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres';" \
        2>>"$log_file")
    if [ -z "$databases" ]; then
        echo "No user databases enumerated for multi-DB backup" >>"$log_file"
        rm -rf "$out_dir"
        return 1
    fi

    : >"$manifest"
    local index=0
    local dumped=0
    local dbname=""
    while IFS= read -r dbname; do
        [ -n "$dbname" ] || continue
        index=$((index + 1))
        local filename
        filename=$(pg_dump_index_filename "$index")

        # Owner of this database (empty if it can't be determined; restore
        # falls back to the admin role).
        local owner=""
        if ! owner=$(docker exec -e PGPASSWORD="$backup_password" "$container_name" \
            psql -U "$backup_user" -d postgres -At \
            -c "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname = '${dbname//\'/\'\'}';" \
            2>>"$log_file") || [ -z "$owner" ]; then
            echo "Could not determine owner for database '$dbname'; restore will fall back to the admin role" >>"$log_file"
            owner=""
        fi

        # TimescaleDB presence + version for this database. One query gives both:
        # a non-empty result means the extension is installed, and the value is
        # its version (recorded so restore can detect a version mismatch before
        # doing anything destructive). Check psql's own exit status so a
        # connection failure isn't silently recorded as "not installed".
        local has_ts="0"
        local ts_version=""
        local ext_check=""
        if ext_check=$(docker exec -e PGPASSWORD="$backup_password" "$container_name" \
            psql -U "$backup_user" -d "$dbname" -At \
            -c "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';" 2>>"$log_file"); then
            if [ -n "$ext_check" ]; then
                has_ts="1"
                ts_version="$ext_check"
            fi
        else
            echo "Could not check timescaledb extension for database '$dbname'; assuming not present" >>"$log_file"
        fi

        # Dump this database.
        if ! docker exec -e PGPASSWORD="$backup_password" "$container_name" \
            pg_dump -U "$backup_user" -d "$dbname" --clean --if-exists >"$out_dir/$filename" 2>>"$log_file"; then
            echo "pg_dump failed for database '$dbname'" >>"$log_file"
            rm -f "$out_dir/$filename"
            continue
        fi

        # Never trust an empty/garbage dump.
        if ! postgres_dump_looks_restorable "$out_dir/$filename"; then
            echo "Dump for database '$dbname' failed content validation; skipping" >>"$log_file"
            rm -f "$out_dir/$filename"
            continue
        fi

        local line
        if ! line=$(pg_manifest_encode "$dbname" "$owner" "$has_ts" "$filename" "$ts_version"); then
            echo "Database name '$dbname' is not manifest-safe; skipping" >>"$log_file"
            rm -f "$out_dir/$filename"
            continue
        fi
        printf '%s\n' "$line" >>"$manifest"
        dumped=$((dumped + 1))
    done <<<"$databases"

    if [ "$dumped" -eq 0 ]; then
        rm -rf "$out_dir"
        return 1
    fi
    return 0
}

backup_command() {
    colorized_echo blue "Starting backup process..."

    # Check if HPXPANEL is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        return 1
    fi

    local backup_dir="$APP_DIR/backup"
    local timestamp=$(date +"%Y%m%d%H%M%S")
    local backup_file="$backup_dir/backup_$timestamp.zip"
    local error_messages=()
    local final_backup_paths=()
    local split_size_bytes="${BACKUP_SPLIT_SIZE_BYTES:-$((47 * 1024 * 1024))}" # keep Telegram chunks under 50MB
    local split_threshold_bytes="${BACKUP_SPLIT_THRESHOLD_BYTES:-$split_size_bytes}"
    local staging_root=""
    local temp_dir=""
    local log_file=""
    # Keep the lock with the backup artifacts so it is not affected by sticky-dir
    # protections on /tmp when different users invoke the command.
    local lock_dir="${backup_dir}/.${APP_NAME}-backup.lock.d"
    local keep_log_file=false

    if ! mkdir -p "$backup_dir"; then
        colorized_echo red "Failed to prepare backup directory: $backup_dir"
        return 1
    fi

    # Backups can be large, so avoid /tmp by default and stage beside the final
    # archive unless BACKUP_TMPDIR is explicitly set.
    staging_root="${BACKUP_TMPDIR:-$backup_dir}"
    if ! mkdir -p "$staging_root"; then
        colorized_echo red "Failed to prepare backup staging directory: $staging_root"
        return 1
    fi

    if ! temp_dir=$(mktemp -d "${staging_root}/hpxpanel_backup.XXXXXX"); then
        colorized_echo red "Failed to create backup temp directory."
        return 1
    fi

    if ! log_file=$(mktemp "${staging_root}/hpxpanel_backup_error.XXXXXX.log"); then
        colorized_echo red "Failed to create backup log file."
        rm -rf "$temp_dir"
        return 1
    fi

    acquire_backup_lock() {
        local lock_pid=""

        if mkdir "$lock_dir" 2>/dev/null; then
            printf '%s\n' "$$" >"$lock_dir/pid"
            return 0
        fi

        if [ -f "$lock_dir/pid" ]; then
            lock_pid=$(cat "$lock_dir/pid" 2>/dev/null || true)
            if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
                return 1
            fi
        fi

        if rm -rf "$lock_dir" 2>/dev/null && mkdir "$lock_dir" 2>/dev/null; then
            printf '%s\n' "$$" >"$lock_dir/pid"
            return 0
        fi

        return 2
    }

    local lock_status=0
    if acquire_backup_lock; then
        lock_status=0
    else
        lock_status=$?
    fi

    case "$lock_status" in
    0)
        ;;
    1)
        colorized_echo yellow "Another backup process is already running."
        rm -rf "$temp_dir"
        rm -f "$log_file"
        return 1
        ;;
    *)
        colorized_echo red "Failed to acquire backup lock: $lock_dir"
        rm -rf "$temp_dir"
        rm -f "$log_file"
        return 1
        ;;
    esac

    cleanup_backup_command() {
        rm -rf "$temp_dir"
        if [ "$keep_log_file" != true ] && [ -n "$log_file" ]; then
            rm -f "$log_file"
        fi
        rm -rf "$lock_dir"
    }

    >"$log_file"
    echo "Backup Log - $(date)" >>"$log_file"

    colorized_echo blue "Reading environment configuration..."

    if ! command -v rsync >/dev/null 2>&1; then
        detect_os
        install_package rsync
    fi

    if ! command -v zip >/dev/null 2>&1; then
        detect_os
        install_package zip
    fi

    if [ -f "$ENV_FILE" ]; then
        while IFS='=' read -r key value; do
            if [[ -z "$key" || "$key" =~ ^# ]]; then
                continue
            fi
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            # Remove surrounding quotes from value if present
            value=$(echo "$value" | sed -E 's/^["'\''](.*)["'\'']$/\1/')
            if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
                export "$key"="$value"
            else
                echo "Skipping invalid line in .env: $key=$value" >>"$log_file"
            fi
        done <"$ENV_FILE"
    else
        error_messages+=("Environment file (.env) not found.")
        echo "Environment file (.env) not found." >>"$log_file"
        send_backup_error_to_telegram "${error_messages[*]}" "$log_file"
        keep_log_file=true
        cleanup_backup_command
        return 1
    fi

    local db_type=""
    local sqlite_file=""
    local db_host=""
    local db_port=""
    local db_user=""
    local db_password=""
    local db_name=""
    local container_name=""
    local safe_sqlalchemy_url=""

    safe_sqlalchemy_url=$(printf '%s' "${SQLALCHEMY_DATABASE_URL:-not set}" | sed -E 's#^([^:]+://)([^@/]+)@#\1REDACTED@#')

    # SQLALCHEMY_DATABASE_URL should already be loaded from .env above
    # Just log what we have
    echo "SQLALCHEMY_DATABASE_URL from environment: ${safe_sqlalchemy_url}" >>"$log_file"

    if [ -z "$SQLALCHEMY_DATABASE_URL" ]; then
        colorized_echo red "Error: SQLALCHEMY_DATABASE_URL not found in .env file or not set"
        echo "Please check $ENV_FILE for SQLALCHEMY_DATABASE_URL" >>"$log_file"
        error_messages+=("SQLALCHEMY_DATABASE_URL not found in .env file")
        colorized_echo yellow "Please check the log file for details: $log_file"
        keep_log_file=true
        send_backup_error_to_telegram "${error_messages[*]}" "$log_file"
        cleanup_backup_command
        return 1
    fi

    if [ -n "$SQLALCHEMY_DATABASE_URL" ]; then
        echo "Parsing SQLALCHEMY_DATABASE_URL: ${safe_sqlalchemy_url}" >>"$log_file"

        # Extract database type from scheme
        if [[ "$SQLALCHEMY_DATABASE_URL" =~ ^sqlite ]]; then
        db_type="sqlite"
            # Extract SQLite file path
            # SQLite URLs: sqlite:///relative/path or sqlite:////absolute/path
            local sqlite_url_part="${SQLALCHEMY_DATABASE_URL#*://}"
            sqlite_url_part="${sqlite_url_part%%\?*}"
            sqlite_url_part="${sqlite_url_part%%#*}"

            # SQLite URL format:
            # sqlite:////absolute/path (4 slashes = absolute path /path)
            # After removing 'sqlite://', //absolute/path remains, convert to /absolute/path
            if [[ "$sqlite_url_part" =~ ^//(.*)$ ]]; then
                # Absolute path: sqlite:////absolute/path -> /absolute/path
                sqlite_file="/${BASH_REMATCH[1]}"
            elif [[ "$sqlite_url_part" =~ ^/(.*)$ ]]; then
                # Could be absolute (sqlite:///path) or relative depending on context
                # In practice, treat as absolute since SQLAlchemy uses 4 slashes for absolute
                sqlite_file="/${BASH_REMATCH[1]}"
            else
                # Relative path (no leading slash)
                sqlite_file="$sqlite_url_part"
            fi
        elif [[ "$SQLALCHEMY_DATABASE_URL" =~ ^(mysql|mariadb|postgresql)[^:]*:// ]]; then
            # Extract scheme to determine type
            if [[ "$SQLALCHEMY_DATABASE_URL" =~ ^mariadb[^:]*:// ]]; then
                db_type="mariadb"
            elif [[ "$SQLALCHEMY_DATABASE_URL" =~ ^mysql[^:]*:// ]]; then
                db_type="mysql"
            elif [[ "$SQLALCHEMY_DATABASE_URL" =~ ^postgresql[^:]*:// ]]; then
                # Check if it's timescaledb by checking for specific patterns or container
                if grep -q "image: timescale/timescaledb" "$COMPOSE_FILE" 2>/dev/null; then
                    db_type="timescaledb"
                else
                    db_type="postgresql"
                fi
            fi

            # Parse connection string: scheme://[user[:password]@]host[:port]/database[?query]
            # Remove scheme prefix
            local url_part="${SQLALCHEMY_DATABASE_URL#*://}"
            # Remove query parameters if present
            url_part="${url_part%%\?*}"
            url_part="${url_part%%#*}"

            # Extract auth part (user:password@)
            # Use the last '@' as the separator between auth and host
            if [[ "$url_part" == *@* ]]; then
                local auth_part="${url_part%@*}"
                url_part="${url_part##*@}"

                # Extract username and password (first ':' is the separator)
                if [[ "$auth_part" == *:* ]]; then
                    db_user="${auth_part%%:*}"
                    db_password="${auth_part#*:}"
                else
                    db_user="$auth_part"
                fi
            fi

            # Extract host, port, and database
            if [[ "$url_part" =~ ^\[([^]]+)\](:([0-9]+))?/(.+)$ ]]; then
                db_host="${BASH_REMATCH[1]}"
                db_port="${BASH_REMATCH[3]:-}"
                db_name="${BASH_REMATCH[4]}"
            elif [[ "$url_part" =~ ^([^:/]+)(:([0-9]+))?/(.+)$ ]]; then
                db_host="${BASH_REMATCH[1]}"
                db_port="${BASH_REMATCH[3]:-}"
                db_name="${BASH_REMATCH[4]}"
            fi

            if [ -n "$db_host" ]; then
                # Remove query parameters from database name if any
                db_name="${db_name%%\?*}"
                db_name="${db_name%%#*}"

                urldecode() { local url_encoded="${1//+/ }"; printf '%b' "${url_encoded//%/\\x}"; }
                db_user=$(urldecode "$db_user")
                db_password=$(urldecode "$db_password")
                db_name=$(urldecode "$db_name")

                # Set default ports if not specified
                if [ -z "$db_port" ]; then
                    if [[ "$db_type" =~ ^(mysql|mariadb)$ ]]; then
                        db_port="3306"
                    elif [[ "$db_type" =~ ^(postgresql|timescaledb)$ ]]; then
                        db_port="5432"
                    fi
                fi
            fi

            # For local databases, try to find container name from docker-compose
            if is_local_db_host "$db_host"; then
                container_name=$(find_container "$db_type")
                echo "Container name/ID for $db_type: $container_name" >>"$log_file"
            fi
        fi
    fi

    if [ -n "$db_type" ]; then
        echo "Database detected: $db_type" >>"$log_file"
        echo "Database host: ${db_host:-localhost}" >>"$log_file"
        colorized_echo blue "Database detected: $db_type"
        colorized_echo blue "Backing up database..."
        case $db_type in
        mariadb)
            if is_local_db_host "$db_host"; then
                if [ -z "$container_name" ]; then
                    colorized_echo red "Error: MariaDB container not found. Is the container running?"
                    echo "MariaDB container not found. Container name: ${container_name:-empty}" >>"$log_file"
                    error_messages+=("MariaDB container not found or not running.")
                else
                    local verified_container=$(check_container "$container_name" "$db_type")
                    if [ -z "$verified_container" ]; then
                        colorized_echo red "Error: MariaDB container not found or not running."
                        echo "Container not found or not running: $container_name" >>"$log_file"
                        error_messages+=("MariaDB container not found or not running.")
                    else
                        container_name="$verified_container"
                # Local Docker container
                # Try root user with MYSQL_ROOT_PASSWORD first for all databases backup
                if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
                    colorized_echo blue "Backing up all MariaDB databases from container: $container_name (using root user)"
                    if docker exec -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" "$container_name" mariadb-dump -u root --all-databases --ignore-database=mysql --ignore-database=performance_schema --ignore-database=information_schema --ignore-database=sys --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                        colorized_echo green "MariaDB backup completed successfully (all databases)"
                    else
                        # Fallback to SQL URL credentials for specific database
                        colorized_echo yellow "Root backup failed, falling back to app user for specific database"
                        local backup_user="${db_user:-${DB_USER:-}}"
                        local backup_password="${db_password:-${DB_PASSWORD:-}}"

                        if [ -z "$backup_password" ] || [ -z "$db_name" ]; then
                            colorized_echo red "Error: Cannot fallback - missing database name or password in SQLALCHEMY_DATABASE_URL"
                            error_messages+=("MariaDB backup failed - root backup failed and fallback credentials incomplete.")
                        else
                            colorized_echo blue "Backing up MariaDB database '$db_name' from container: $container_name (using app user)"
                            if ! docker exec -e MYSQL_PWD="$backup_password" "$container_name" mariadb-dump -u "$backup_user" "$db_name" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                colorized_echo red "MariaDB dump failed. Check log file for details."
                                error_messages+=("MariaDB dump failed.")
                            else
                                colorized_echo green "MariaDB backup completed successfully"
                            fi
                        fi
                    fi
                else
                    # No MYSQL_ROOT_PASSWORD, use SQL URL credentials for specific database
                    local backup_user="${db_user:-${DB_USER:-}}"
                    local backup_password="${db_password:-${DB_PASSWORD:-}}"

                    if [ -z "$backup_password" ]; then
                        colorized_echo red "Error: Database password not found. Check MYSQL_ROOT_PASSWORD or SQLALCHEMY_DATABASE_URL in .env"
                        error_messages+=("MariaDB password not found.")
                    elif [ -z "$db_name" ]; then
                        colorized_echo red "Error: Database name not found in SQLALCHEMY_DATABASE_URL"
                        error_messages+=("MariaDB database name not found.")
                    else
                        colorized_echo blue "Backing up MariaDB database '$db_name' from container: $container_name (using app user)"
                        if ! docker exec -e MYSQL_PWD="$backup_password" "$container_name" mariadb-dump -u "$backup_user" "$db_name" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                            colorized_echo red "MariaDB dump failed. Check log file for details."
                            error_messages+=("MariaDB dump failed.")
                        else
                            colorized_echo green "MariaDB backup completed successfully"
                        fi
                    fi
                fi
                    fi
                fi
            else
                # Remote database - would need mariadb-client installed
                colorized_echo red "Remote MariaDB backup not yet supported. Please use local database or install mariadb-client."
                error_messages+=("Remote MariaDB backup not yet supported. Please use local database or install mariadb-client.")
            fi
            ;;
        mysql)
            if is_local_db_host "$db_host"; then
                if [ -z "$container_name" ]; then
                    colorized_echo red "Error: MySQL container not found. Is the container running?"
                    echo "MySQL container not found. Container name: ${container_name:-empty}" >>"$log_file"
                    error_messages+=("MySQL container not found or not running.")
                else
                    local verified_container=$(check_container "$container_name" "$db_type")
                    if [ -z "$verified_container" ]; then
                        colorized_echo red "Error: MySQL/MariaDB container not found or not running."
                        echo "Container not found or not running: $container_name" >>"$log_file"
                        error_messages+=("MySQL/MariaDB container not found or not running.")
                    else
                        container_name="$verified_container"
                            # Check if this is actually a MariaDB container (try mariadb-dump first)
                            local is_mariadb=false
                            if docker exec "$container_name" mariadb-dump --version >/dev/null 2>&1; then
                                is_mariadb=true
                            fi

                    # Local Docker container
                    # Try root user with MYSQL_ROOT_PASSWORD first for all databases backup
                    if [ -n "${MYSQL_ROOT_PASSWORD:-}" ]; then
                                # Choose command based on whether it's MariaDB or MySQL
                                local mysql_cmd="mysql"
                                local dump_cmd="mysqldump"
                                local db_type_name="MySQL"
                                if [ "$is_mariadb" = true ]; then
                                    mysql_cmd="mariadb"
                                    dump_cmd="mariadb-dump"
                                    db_type_name="MariaDB"
                                fi

                                colorized_echo blue "Backing up all $db_type_name databases from container: $container_name (using root user)"
                                databases=$(docker exec -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" "$container_name" "$mysql_cmd" -u root -e "SHOW DATABASES;" 2>>"$log_file" | grep -Ev "^(Database|mysql|performance_schema|information_schema|sys)$" || true)
                                # Collect DB names into an array so each is passed as one argument
                                # (a name containing a space must not be word-split).
                                local -a database_list=()
                                while IFS= read -r _db_line; do
                                    [ -n "$_db_line" ] && database_list+=("$_db_line")
                                done <<<"$databases"
                        if [ -z "$databases" ]; then
                            colorized_echo yellow "No user databases found, falling back to specific database backup"
                            # Fallback to SQL URL credentials
                            local backup_user="${db_user:-${DB_USER:-}}"
                            local backup_password="${db_password:-${DB_PASSWORD:-}}"

                            if [ -z "$backup_password" ] || [ -z "$db_name" ]; then
                                colorized_echo red "Error: Cannot fallback - missing database name or password in SQLALCHEMY_DATABASE_URL"
                                error_messages+=("MySQL backup failed - no databases found and fallback credentials incomplete.")
                            else
                                        colorized_echo blue "Backing up $db_type_name database '$db_name' from container: $container_name (using app user)"
                                        if ! docker exec -e MYSQL_PWD="$backup_password" "$container_name" "$dump_cmd" -u "$backup_user" "$db_name" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                            colorized_echo red "$db_type_name dump failed. Check log file for details."
                                            error_messages+=("$db_type_name dump failed.")
                                        else
                                            colorized_echo green "$db_type_name backup completed successfully"
                                        fi
                                    fi
                                elif ! docker exec -e MYSQL_PWD="$MYSQL_ROOT_PASSWORD" "$container_name" "$dump_cmd" -u root --databases "${database_list[@]}" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                            # Root backup failed, fallback to SQL URL credentials
                            colorized_echo yellow "Root backup failed, falling back to app user for specific database"
                            local backup_user="${db_user:-${DB_USER:-}}"
                            local backup_password="${db_password:-${DB_PASSWORD:-}}"

                            if [ -z "$backup_password" ] || [ -z "$db_name" ]; then
                                colorized_echo red "Error: Cannot fallback - missing database name or password in SQLALCHEMY_DATABASE_URL"
                                error_messages+=("MySQL backup failed - root backup failed and fallback credentials incomplete.")
                            else
                                        colorized_echo blue "Backing up $db_type_name database '$db_name' from container: $container_name (using app user)"
                                        if ! docker exec -e MYSQL_PWD="$backup_password" "$container_name" "$dump_cmd" -u "$backup_user" "$db_name" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                            colorized_echo red "$db_type_name dump failed. Check log file for details."
                                            error_messages+=("$db_type_name dump failed.")
                                        else
                                            colorized_echo green "$db_type_name backup completed successfully"
                                        fi
                            fi
                        else
                                    colorized_echo green "$db_type_name backup completed successfully (all databases)"
                        fi
                    else
                        # No MYSQL_ROOT_PASSWORD, use SQL URL credentials for specific database
                        local backup_user="${db_user:-${DB_USER:-}}"
                        local backup_password="${db_password:-${DB_PASSWORD:-}}"
                                local dump_cmd="mysqldump"
                                local db_type_name="MySQL"
                                if [ "$is_mariadb" = true ]; then
                                    dump_cmd="mariadb-dump"
                                    db_type_name="MariaDB"
                                fi

                        if [ -z "$backup_password" ]; then
                            colorized_echo red "Error: Database password not found. Check MYSQL_ROOT_PASSWORD or SQLALCHEMY_DATABASE_URL in .env"
                            error_messages+=("MySQL password not found.")
                        elif [ -z "$db_name" ]; then
                            colorized_echo red "Error: Database name not found in SQLALCHEMY_DATABASE_URL"
                            error_messages+=("MySQL database name not found.")
                        else
                                    colorized_echo blue "Backing up $db_type_name database '$db_name' from container: $container_name (using app user)"
                                    if ! docker exec -e MYSQL_PWD="$backup_password" "$container_name" "$dump_cmd" -u "$backup_user" "$db_name" --events --triggers >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                        colorized_echo red "$db_type_name dump failed. Check log file for details."
                                        error_messages+=("$db_type_name dump failed.")
                                    else
                                        colorized_echo green "$db_type_name backup completed successfully"
                                    fi
                                fi
                        fi
                    fi
                fi
            else
                # Remote database - would need mysql-client installed
                colorized_echo red "Remote MySQL backup not yet supported. Please use local database or install mysql-client."
                error_messages+=("Remote MySQL backup not yet supported. Please use local database or install mysql-client.")
            fi
            ;;
        postgresql)
            if is_local_db_host "$db_host"; then
                if [ -z "$container_name" ]; then
                    colorized_echo red "Error: PostgreSQL container not found. Is the container running?"
                    echo "PostgreSQL container not found. Container name: ${container_name:-empty}" >>"$log_file"
                    error_messages+=("PostgreSQL container not found or not running.")
                else
                    local verified_container=$(check_container "$container_name" "$db_type")
                    if [ -z "$verified_container" ]; then
                        colorized_echo red "Error: PostgreSQL container not found or not running."
                        echo "Container not found or not running: $container_name" >>"$log_file"
                        error_messages+=("PostgreSQL container not found or not running.")
                    else
                        container_name="$verified_container"
                        local backup_user="${db_user:-${DB_USER:-postgres}}"
                        local backup_password="${db_password:-${DB_PASSWORD:-}}"

                        if [ -z "$backup_password" ]; then
                            colorized_echo red "Error: Database password not found. Check DB_PASSWORD or SQLALCHEMY_DATABASE_URL in .env"
                            error_messages+=("PostgreSQL password not found.")
                        elif [ -z "$db_name" ]; then
                            colorized_echo red "Error: Database name not found in SQLALCHEMY_DATABASE_URL"
                            error_messages+=("PostgreSQL database name not found.")
                        else
                            colorized_echo blue "Backing up all PostgreSQL databases from container: $container_name (using user: $backup_user)"
                            if pg_dump_all_user_databases "$container_name" "$backup_user" "$backup_password" "$temp_dir" "$log_file"; then
                                colorized_echo green "PostgreSQL backup completed successfully (all databases)"
                            else
                                colorized_echo yellow "Multi-database backup unavailable; falling back to single database '$db_name'."
                                if ! docker exec -e PGPASSWORD="$backup_password" "$container_name" pg_dump -U "$backup_user" -d "$db_name" --clean --if-exists >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                    colorized_echo red "PostgreSQL dump failed. Check log file for details."
                                    error_messages+=("PostgreSQL dump failed.")
                                else
                                    colorized_echo green "PostgreSQL backup completed successfully"
                                fi
                            fi
                        fi
                    fi
                fi
            else
                # Remote database - would need postgresql-client installed
                colorized_echo red "Remote PostgreSQL backup not yet supported. Please use local database or install postgresql-client."
                error_messages+=("Remote PostgreSQL backup not yet supported. Please use local database or install postgresql-client.")
            fi
            ;;
        timescaledb)
            if is_local_db_host "$db_host"; then
                if [ -z "$container_name" ]; then
                    colorized_echo red "Error: TimescaleDB container not found. Is the container running?"
                    echo "Container name detection failed. Checked for: timescaledb, postgresql" >>"$log_file"
                    error_messages+=("TimescaleDB container not found or not running.")
                else
                    # Get actual container name/ID - ps -q returns container ID, which is what we need
                    # But first verify the container exists
                    local actual_container=""
                    if docker inspect "$container_name" >/dev/null 2>&1; then
                        actual_container="$container_name"
                    else
                        # Try to find container by service name using docker compose
                        actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q timescaledb 2>/dev/null)
                        if [ -z "$actual_container" ]; then
                            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q postgresql 2>/dev/null)
                        fi
                        if [ -z "$actual_container" ]; then
                            # Try with full container name pattern
                            local full_container_name="${APP_NAME}-timescaledb-1"
                            if docker inspect "$full_container_name" >/dev/null 2>&1; then
                                actual_container="$full_container_name"
                            else
                                full_container_name="${APP_NAME}-postgresql-1"
                                if docker inspect "$full_container_name" >/dev/null 2>&1; then
                                    actual_container="$full_container_name"
                                fi
                            fi
                        fi
                    fi

                    if [ -z "$actual_container" ]; then
                        colorized_echo red "Error: TimescaleDB container not found. Is the container running?"
                        echo "Container not found. Tried: $container_name and various patterns" >>"$log_file"
                        error_messages+=("TimescaleDB container not found or not running.")
                    else
                        container_name="$actual_container"
                        # Local Docker container
                        # Use SQL URL credentials directly for pg_dump (more reliable than pg_dumpall)
                        local backup_user="${db_user:-${DB_USER:-postgres}}"
                        local backup_password="${db_password:-${DB_PASSWORD:-}}"

                        if [ -z "$backup_password" ]; then
                            colorized_echo red "Error: Database password not found. Check DB_PASSWORD or SQLALCHEMY_DATABASE_URL in .env"
                            error_messages+=("TimescaleDB password not found.")
                        elif [ -z "$db_name" ]; then
                            colorized_echo red "Error: Database name not found in SQLALCHEMY_DATABASE_URL"
                            error_messages+=("TimescaleDB database name not found.")
                        else
                            colorized_echo blue "Backing up all TimescaleDB databases from container: $container_name (using user: $backup_user)"
                            if pg_dump_all_user_databases "$container_name" "$backup_user" "$backup_password" "$temp_dir" "$log_file"; then
                                colorized_echo green "TimescaleDB backup completed successfully (all databases)"
                            else
                                colorized_echo yellow "Multi-database backup unavailable; falling back to single database '$db_name'."
                                if ! docker exec -e PGPASSWORD="$backup_password" "$container_name" pg_dump -U "$backup_user" -d "$db_name" --clean --if-exists >"$temp_dir/db_backup.sql" 2>>"$log_file"; then
                                    colorized_echo red "TimescaleDB dump failed. Check log file for details: $log_file"
                                    error_messages+=("TimescaleDB dump failed for database '$db_name'.")
                                else
                                    colorized_echo green "TimescaleDB backup completed successfully"
                                fi
                            fi
                        fi
                    fi
                fi
            else
                # Remote database - would need postgresql-client installed
                colorized_echo red "Remote TimescaleDB backup not yet supported. Please use local database or install postgresql-client."
                error_messages+=("Remote TimescaleDB backup not yet supported. Please use local database or install postgresql-client.")
            fi
            ;;
        sqlite)
            if [ -f "$sqlite_file" ]; then
                if ! command -v sqlite3 >/dev/null 2>&1; then
                    detect_os
                    # Best-effort: if sqlite3 can't be installed, continue (the
                    # presence check below skips the snapshot). install_package
                    # aborts on failure, so use the non-aborting variant here.
                    try_install_package sqlite3 || true
                fi

                local sqlite_basename=$(basename "$sqlite_file")
                if command -v sqlite3 >/dev/null 2>&1; then
                    if ! sqlite3 "$sqlite_file" ".backup '$temp_dir/$sqlite_basename'" >>"$log_file" 2>&1; then
                        error_messages+=("Failed to create SQLite backup snapshot.")
                    fi
                elif ! cp "$sqlite_file" "$temp_dir/$sqlite_basename" 2>>"$log_file"; then
                    error_messages+=("Failed to copy SQLite database.")
                fi
            else
                error_messages+=("SQLite database file not found at $sqlite_file.")
            fi
            ;;
        esac
    else
        colorized_echo yellow "Warning: No database type detected. Skipping database backup."
        echo "Warning: No database type detected." >>"$log_file"
        echo "SQLALCHEMY_DATABASE_URL: ${safe_sqlalchemy_url}" >>"$log_file"
    fi

    colorized_echo blue "Copying app directory..."
    if [ -d "$APP_DIR" ]; then
        # Use rsync to copy the entire app directory, excluding the backup folder
        if ! rsync -av --exclude 'backup' "$APP_DIR/" "$temp_dir/" >>"$log_file" 2>&1; then
            error_messages+=("Failed to copy app directory.")
            echo "Failed to copy app directory" >>"$log_file"
        fi
    else
        colorized_echo yellow "Warning: App directory $APP_DIR does not exist. Copying individual files as fallback."
        if [ -f "$APP_DIR/.env" ]; then
            cp "$APP_DIR/.env" "$temp_dir/" 2>>"$log_file" || true
        fi
        if [ -f "$APP_DIR/docker-compose.yml" ]; then
            cp "$APP_DIR/docker-compose.yml" "$temp_dir/" 2>>"$log_file" || true
        fi
    fi

    colorized_echo blue "Copying data directory..."
    # Ensure destination directory exists and is empty (already cleaned above, but be explicit)
    if [ -d "$DATA_DIR" ]; then
        local rsync_args=(-av --exclude 'xray-core' --exclude 'mysql' --exclude 'mariadb' --exclude 'postgresql' --exclude 'timescaledb')

        if [ "$db_type" = "sqlite" ] && [ -n "$sqlite_file" ] && [[ "$sqlite_file" == "$DATA_DIR/"* ]]; then
            local sqlite_relative_path="${sqlite_file#$DATA_DIR/}"
            rsync_args+=(--exclude "$sqlite_relative_path")
            rsync_args+=(--exclude "${sqlite_relative_path}-wal")
            rsync_args+=(--exclude "${sqlite_relative_path}-shm")
            echo "Excluding SQLite database from data directory copy: $sqlite_relative_path" >>"$log_file"
        fi

        if ! rsync "${rsync_args[@]}" "$DATA_DIR/" "$temp_dir/hpxpanel_data/" >>"$log_file" 2>&1; then
            error_messages+=("Failed to copy data directory.")
            echo "Failed to copy data directory" >>"$log_file"
        elif [ "$db_type" = "sqlite" ] && [ -n "$sqlite_file" ] && [[ "$sqlite_file" == "$DATA_DIR/"* ]]; then
            local sqlite_relative_path="${sqlite_file#$DATA_DIR/}"
            rm -f "$temp_dir/hpxpanel_data/$sqlite_relative_path" \
                "$temp_dir/hpxpanel_data/${sqlite_relative_path}-wal" \
                "$temp_dir/hpxpanel_data/${sqlite_relative_path}-shm" 2>>"$log_file" || true
        fi
    else
        colorized_echo yellow "Data directory $DATA_DIR does not exist. Skipping data directory backup."
        echo "Data directory $DATA_DIR does not exist. Skipping." >>"$log_file"
        # Create empty directory structure so tar doesn't fail
        mkdir -p "$temp_dir/hpxpanel_data"
    fi

    # Remove Unix socket files so zip doesn't fail with ENXIO ("No such device or address")
    if [ -d "$temp_dir" ]; then
        local socket_files
        socket_files=$(find "$temp_dir" -type s -print 2>/dev/null || true)
        if [ -n "$socket_files" ]; then
            colorized_echo yellow "Removing Unix socket files before archiving (zip cannot archive sockets)."
            printf "%s\n" "$socket_files" >>"$log_file"
            find "$temp_dir" -type s -delete >>"$log_file" 2>&1 || true
        fi
    fi

    colorized_echo blue "Creating backup archive..."
    # Verify temp_dir exists and has content before creating archive
    if [ ! -d "$temp_dir" ] || [ -z "$(ls -A "$temp_dir" 2>/dev/null)" ]; then
        error_messages+=("Temporary directory is empty or missing. Cannot create archive.")
        echo "Temporary directory is empty or missing: $temp_dir" >>"$log_file"
    elif ! (cd "$temp_dir" && zip -rq "$backup_file" .) 2>>"$log_file"; then
        error_messages+=("Failed to create backup archive.")
        echo "Failed to create backup archive." >>"$log_file"
    else
        local archive_size_bytes=0
        archive_size_bytes=$(stat -c%s "$backup_file" 2>/dev/null || wc -c <"$backup_file")

        if [ "$archive_size_bytes" -gt "$split_threshold_bytes" ]; then
            colorized_echo blue "Splitting backup archive into Telegram-sized parts..."
            if ! split -d -a 2 --numeric-suffixes=1 -b "$split_size_bytes" --additional-suffix=".zip" \
                "$backup_file" "$backup_dir/backup_${timestamp}.part" 2>>"$log_file"; then
                error_messages+=("Failed to split backup archive.")
                echo "Failed to split backup archive." >>"$log_file"
            else
                rm -f "$backup_file"
            fi
        fi

        if [ ${#error_messages[@]} -eq 0 ]; then
            find "$backup_dir" -maxdepth 1 -type f \
                \( -name "backup_*.tar.gz" -o -name "backup_*.zip" -o -name "backup_*.z[0-9][0-9]" -o -name "backup_*.part[0-9][0-9].zip" \) \
                ! -name "backup_${timestamp}.zip" \
                ! -name "backup_${timestamp}.z[0-9][0-9]" \
                ! -name "backup_${timestamp}.part[0-9][0-9].zip" \
                -delete 2>/dev/null || true
        fi
    fi

    while IFS= read -r file; do
        final_backup_paths+=("$file")
    done < <(find "$backup_dir" -maxdepth 1 -type f -name "backup_${timestamp}.part[0-9][0-9].zip" | sort)

    if [ ${#final_backup_paths[@]} -eq 0 ] && [ -f "$backup_file" ]; then
        final_backup_paths+=("$backup_file")
    fi

    if [ ${#error_messages[@]} -eq 0 ] && [ ${#final_backup_paths[@]} -gt 0 ]; then
        local backup_size_bytes=0
        local size_file=""
        for size_file in "${final_backup_paths[@]}"; do
            [ -n "$size_file" ] || continue
            local size_bytes=0
            size_bytes=$(stat -c%s "$size_file" 2>/dev/null || wc -c <"$size_file")
            backup_size_bytes=$((backup_size_bytes + size_bytes))
        done

        local backup_size=""
        if command -v numfmt >/dev/null 2>&1; then
            backup_size=$(numfmt --to=iec --suffix=B "$backup_size_bytes" 2>/dev/null || awk -v size="$backup_size_bytes" 'BEGIN { printf "%.2f MB", size/1048576 }')
        else
            backup_size=$(awk -v size="$backup_size_bytes" 'BEGIN { printf "%.2f MB", size/1048576 }')
        fi
        if [ ${#final_backup_paths[@]} -eq 1 ]; then
            colorized_echo green "Backup archive created: ${final_backup_paths[0]} (Size: $backup_size)"
        else
            colorized_echo green "Backup archive created in ${#final_backup_paths[@]} parts (Total Size: $backup_size)"
        fi
    fi

    if [ ${#error_messages[@]} -gt 0 ]; then
        keep_log_file=true
        colorized_echo red "Backup completed with errors:"
        for error in "${error_messages[@]}"; do
            colorized_echo red "  - $error"
        done
        colorized_echo yellow "Check log file: $log_file"
        if [ -f "$ENV_FILE" ]; then
            send_backup_error_to_telegram "${error_messages[*]}" "$log_file"
        fi
        cleanup_backup_command
        return 1
    fi

    if [ ${#final_backup_paths[@]} -eq 0 ]; then
        keep_log_file=true
        colorized_echo red "Backup file was not created. Check log file: $log_file"
        cleanup_backup_command
        return 1
    fi

    if [ ${#final_backup_paths[@]} -eq 1 ]; then
        colorized_echo green "Backup completed successfully: ${final_backup_paths[0]}"
    else
        colorized_echo green "Backup completed successfully in ${#final_backup_paths[@]} parts:"
        for part in "${final_backup_paths[@]}"; do
            colorized_echo green "  - $(basename "$part")"
        done
    fi
    if [ -f "$ENV_FILE" ]; then
        send_backup_to_telegram "$backup_file"
    fi
    cleanup_backup_command
}
