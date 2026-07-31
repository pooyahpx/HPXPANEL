#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SHARED_LIB_DIR="${SCRIPT_DIR}/lib"
REQUIRED_SHARED_LIBS="common.sh system.sh docker.sh github.sh env.sh hpxpanel-backup.sh hpxpanel-restore.sh"
# Running from a local checkout/bundle (libs sit next to this script) vs. an
# installed copy (libs live under /usr/local/lib). Only the installed copy is
# auto-refreshed below; a checkout's libs are used as-is.
running_from_checkout=true
if [ ! -f "$SHARED_LIB_DIR/common.sh" ]; then
    SHARED_LIB_DIR="/usr/local/lib/hpxpanel-scripts/lib"
    running_from_checkout=false
fi

# Refresh every shared library from the repo into the install dir. All files are
# downloaded to a staging dir first and only swapped in if EVERY download
# succeeds, so a partial/failed refresh never leaves a half-updated set and any
# existing copy is preserved on failure.
bootstrap_hpxpanel_shared_libs() {
    local fetch_repo="pooyahpx/HPXPANEL"
    local bootstrap_dir="/usr/local/lib/hpxpanel-scripts/lib"
    local tmp_dir=""
    local shared_lib=""

    tmp_dir=$(mktemp -d) || return 1

    for shared_lib in $REQUIRED_SHARED_LIBS; do
        if ! curl -fsSL --connect-timeout 5 "https://github.com/${fetch_repo}/raw/main/scripts/lib/${shared_lib}" -o "$tmp_dir/$shared_lib"; then
            rm -rf "$tmp_dir"
            return 1
        fi
    done

    mkdir -p "$bootstrap_dir" || {
        rm -rf "$tmp_dir"
        return 1
    }
    for shared_lib in $REQUIRED_SHARED_LIBS; do
        if ! install -m 644 "$tmp_dir/$shared_lib" "$bootstrap_dir/$shared_lib"; then
            rm -rf "$tmp_dir"
            return 1
        fi
    done

    rm -rf "$tmp_dir"
    SHARED_LIB_DIR="$bootstrap_dir"
    return 0
}

# For an installed copy, always refresh the shared libraries from the repo so an
# outdated copy can never be sourced (the files are small). Best-effort: if the
# refresh fails (e.g. no network) any existing copy is kept and the presence
# check below still guards against a genuinely missing library.
if [ "$running_from_checkout" = false ]; then
    bootstrap_hpxpanel_shared_libs || true
fi

for shared_lib in $REQUIRED_SHARED_LIBS; do
    if [ ! -f "$SHARED_LIB_DIR/$shared_lib" ]; then
        printf 'Missing shared library: %s\n' "$SHARED_LIB_DIR/$shared_lib" >&2
        exit 1
    fi
done

# shellcheck source=lib/common.sh
source "$SHARED_LIB_DIR/common.sh"
# shellcheck source=lib/system.sh
source "$SHARED_LIB_DIR/system.sh"
# shellcheck source=lib/docker.sh
source "$SHARED_LIB_DIR/docker.sh"
# shellcheck source=lib/github.sh
source "$SHARED_LIB_DIR/github.sh"
# shellcheck source=lib/env.sh
source "$SHARED_LIB_DIR/env.sh"
# shellcheck source=lib/hpxpanel-backup.sh
source "$SHARED_LIB_DIR/hpxpanel-backup.sh"
# shellcheck source=lib/hpxpanel-restore.sh
source "$SHARED_LIB_DIR/hpxpanel-restore.sh"

# Handle @ symbol if used in installation (skip it)
if [ "${1:-}" = "@" ]; then
    shift
fi

INSTALL_DIR="/opt"
if [ -z "${APP_NAME:-}" ]; then
    APP_NAME="hpxpanel"
fi
APP_DIR="${APP_DIR:-$INSTALL_DIR/$APP_NAME}"
DATA_DIR="${DATA_DIR:-/var/lib/$APP_NAME}"
THEMES_DIR="$APP_DIR/themes"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"
ENV_FILE="$APP_DIR/.env"
LAST_XRAY_CORES=10

is_valid_proxy_url() {
    local proxy_url="$1"
    [[ -z "$proxy_url" ]] && return 1
    if [[ "$proxy_url" =~ ^(http|https|socks|socks4|socks4a|socks5|socks5h):// ]]; then
        return 0
    fi
    return 1
}

get_backup_proxy_url() {
    local proxy_value="${BACKUP_PROXY_URL:-${BACKUP_PROXY:-}}"
    local proxy_enabled="${BACKUP_PROXY_ENABLED:-}"

    if [ -z "$proxy_value" ]; then
        return 1
    fi

    if [ -n "$proxy_enabled" ] && [[ ! "$proxy_enabled" =~ ^([Tt]rue|[Yy]es|1)$ ]]; then
        return 1
    fi

    printf '%s\n' "$proxy_value"
    return 0
}

is_domain() {
    [[ "$1" =~ ^([A-Za-z0-9](-*[A-Za-z0-9])*\.)+(xn--[a-z0-9]{2,}|[A-Za-z]{2,})$ ]] && return 0 || return 1
}

is_ipv4() {
    local ip="$1"
    local IFS='.'
    local octets=()

    [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
    read -r -a octets <<<"$ip"
    [ "${#octets[@]}" -eq 4 ] || return 1

    for octet in "${octets[@]}"; do
        if [ "$octet" -lt 0 ] || [ "$octet" -gt 255 ]; then
            return 1
        fi
    done

    return 0
}

is_ipv6() {
    [[ "$1" =~ : ]] && return 0 || return 1
}

get_public_ipv4() {
    local urls=(
        "https://api4.ipify.org"
        "https://ipv4.icanhazip.com"
        "https://v4.ident.me"
        "https://ipv4.myexternalip.com/raw"
        "https://ifconfig.me/ip"
    )
    local server_ip=""
    local url=""

    for url in "${urls[@]}"; do
        server_ip=$(curl -4 -fsS --max-time 5 "$url" 2>/dev/null | tr -d '[:space:]' || true)
        if is_ipv4 "$server_ip"; then
            echo "$server_ip"
            return 0
        fi
    done

    return 1
}

is_port_in_use() {
    local port="$1"

    if command -v ss >/dev/null 2>&1; then
        ss -ltn 2>/dev/null | awk -v p=":${port}$" '$4 ~ p {found=1; exit} END {exit found ? 0 : 1}'
        return
    fi

    if command -v netstat >/dev/null 2>&1; then
        netstat -lnt 2>/dev/null | awk -v p=":${port} " '$4 ~ p {found=1; exit} END {exit found ? 0 : 1}'
        return
    fi

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1 && return 0
    fi

    return 1
}

describe_port_listener() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltnp 2>/dev/null | awk -v p=":${port}$" '$4 ~ p {print; exit}'
        return 0
    fi
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | tail -n +2 | head -1
        return 0
    fi
    echo "(unknown process)"
}

resolve_domain_ipv4() {
    local domain="$1"
    local ip=""

    if command -v dig >/dev/null 2>&1; then
        ip=$(dig +short A "$domain" 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)
    fi
    if [ -z "$ip" ] && command -v getent >/dev/null 2>&1; then
        ip=$(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1; exit}' || true)
    fi
    if [ -z "$ip" ] && command -v python3 >/dev/null 2>&1; then
        ip=$(python3 -c "import socket; print(socket.gethostbyname('${domain}'))" 2>/dev/null || true)
    fi
    if [ -z "$ip" ] && command -v host >/dev/null 2>&1; then
        ip=$(host -t A "$domain" 2>/dev/null | awk '/has address/ {print $4; exit}' || true)
    fi

    if is_ipv4 "$ip"; then
        echo "$ip"
        return 0
    fi
    return 1
}

print_ssl_troubleshoot() {
    local target="$1"
    local http_port="${2:-80}"
    local server_ip=""
    server_ip=$(get_public_ipv4 || true)

    colorized_echo yellow "SSL checklist (Let's Encrypt HTTP-01):"
    echo "  1) Domain/IP A record must point to THIS server${server_ip:+ ($server_ip)}"
    echo "  2) Cloud firewall (Vultr/AWS/…) must allow inbound TCP ${http_port}"
    echo "  3) Cloudflare orange-cloud proxy must be OFF while issuing (grey cloud / DNS only)"
    echo "  4) Nothing else may listen on port ${http_port} during issue"
    echo "  5) Retry later with:  hpxpanel ssl"
    if [ -f "${HOME}/.acme.sh/acme.sh.log" ]; then
        colorized_echo yellow "Last acme.sh log lines:"
        tail -n 20 "${HOME}/.acme.sh/acme.sh.log" 2>/dev/null || true
    elif [ -f "/root/.acme.sh/acme.sh.log" ]; then
        colorized_echo yellow "Last acme.sh log lines:"
        tail -n 20 "/root/.acme.sh/acme.sh.log" 2>/dev/null || true
    fi
    [ -n "$target" ] || true
}

prepare_acme_account() {
    local acme_bin="$1"
    local domain_hint="${2:-}"
    local email="ssl@hpxpanel.local"

    if [ -n "$domain_hint" ] && is_domain "$domain_hint"; then
        if [[ "$domain_hint" == *.*.* ]]; then
            email="ssl@${domain_hint#*.}"
        else
            email="ssl@${domain_hint}"
        fi
    fi

    "$acme_bin" --set-default-ca --server letsencrypt >/dev/null 2>&1 || true
    "$acme_bin" --register-account -m "$email" >/dev/null 2>&1 || true
}

preflight_http01_challenge() {
    local http_port="$1"
    local domain="${2:-}"
    local expect_ip="${3:-}"
    local server_ip=""
    local resolved=""
    local listener=""

    server_ip=$(get_public_ipv4 || true)

    if is_port_in_use "$http_port"; then
        listener=$(describe_port_listener "$http_port" || true)
        colorized_echo red "Port ${http_port} is already in use — Let's Encrypt standalone cannot bind it."
        [ -n "$listener" ] && echo "  Listener: ${listener}"
        colorized_echo yellow "Stop that service, or pass a free port: --ssl-http-port <port> (must be reachable from the internet)."
        return 1
    fi

    if [ -n "$domain" ]; then
        colorized_echo blue "Checking DNS for ${domain}..."
        if ! resolved=$(resolve_domain_ipv4 "$domain"); then
            colorized_echo red "Could not resolve A record for ${domain}."
            colorized_echo yellow "Point ${domain} to this server${server_ip:+ ($server_ip)} and wait for DNS, then retry: hpxpanel ssl"
            return 1
        fi
        colorized_echo green "DNS ${domain} -> ${resolved}"
        if [ -n "$server_ip" ] && [ "$resolved" != "$server_ip" ]; then
            colorized_echo red "DNS mismatch: ${domain} points to ${resolved}, but this server is ${server_ip}."
            colorized_echo yellow "If you use Cloudflare, set the record to DNS-only (grey cloud), then retry."
            return 1
        fi
    fi

    if [ -n "$expect_ip" ] && [ -n "$server_ip" ] && [ "$expect_ip" != "$server_ip" ]; then
        colorized_echo yellow "Warning: requested IP ${expect_ip} differs from detected public IP ${server_ip}."
        colorized_echo yellow "Let's Encrypt must reach ${expect_ip}:${http_port} on this machine."
    fi

    return 0
}

# Map the detected OS to its cron daemon package name, mirroring the OS matrix
# in lib/system.sh: Debian/Ubuntu ship "cron"; the Red Hat family, Fedora,
# Arch and openSUSE ship "cronie". Returns non-zero for an unrecognized OS.
get_cron_package_name() {
    if [ -z "${OS:-}" ]; then
        detect_os
    fi
    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        echo "cron"
    elif is_redhat_family_os ||
        [[ "$OS" == "Fedora"* ]] ||
        [[ "$OS" == "Arch Linux" ]] || [[ "$OS" == "Arch"* ]] ||
        [[ "$OS" == "openSUSE"* ]]; then
        echo "cronie"
    else
        return 1
    fi
}

ensure_acme_dependencies() {
    command -v socat >/dev/null 2>&1 || install_package socat
    command -v openssl >/dev/null 2>&1 || install_package openssl

    # acme.sh's installer pre-check requires crontab to schedule auto-renewal.
    if ! command -v crontab >/dev/null 2>&1; then
        local cron_pkg
        if cron_pkg="$(get_cron_package_name)"; then
            install_package "$cron_pkg"
        else
            colorized_echo yellow "Could not determine the cron package for this OS; skipping. acme.sh auto-renewal may not be scheduled."
        fi
    fi
}

install_acme() {
    colorized_echo blue "Installing acme.sh for SSL certificate management..."
    # curl | sh exits 0 even when acme.sh's own installer bails (e.g. a failed
    # pre-check), so confirm the binary actually landed before claiming success.
    if curl -s https://get.acme.sh | sh >/dev/null 2>&1; then
        local acme_bin=""
        acme_bin="$(get_acme_sh_binary)" || true
        if [ -n "$acme_bin" ] && [ -x "$acme_bin" ]; then
            colorized_echo green "acme.sh installed successfully"
            return 0
        fi
    fi
    colorized_echo red "Failed to install acme.sh"
    return 1
}

get_acme_sh_binary() {
    if [ -x "${HOME}/.acme.sh/acme.sh" ]; then
        echo "${HOME}/.acme.sh/acme.sh"
        return 0
    fi

    if [ -x "/root/.acme.sh/acme.sh" ]; then
        echo "/root/.acme.sh/acme.sh"
        return 0
    fi

    if command -v acme.sh >/dev/null 2>&1; then
        command -v acme.sh
        return 0
    fi

    return 1
}

ensure_acme_auto_renew() {
    local acme_bin="$1"

    [ -n "$acme_bin" ] || return 0
    "$acme_bin" --upgrade --auto-upgrade >/dev/null 2>&1 || true
    "$acme_bin" --install-cronjob >/dev/null 2>&1 || true
}

build_hpxpanel_ssl_reload_command() {
    local backend_service=""
    backend_service=$(detect_hpxpanel_backend_service 2>/dev/null || true)

    if [ -n "$backend_service" ]; then
        echo "docker compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart ${backend_service} >/dev/null 2>&1 || docker-compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart ${backend_service} >/dev/null 2>&1 || docker compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart >/dev/null 2>&1 || docker-compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart >/dev/null 2>&1 || true"
    else
        echo "docker compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart >/dev/null 2>&1 || docker-compose -f ${COMPOSE_FILE} -p ${APP_NAME} restart >/dev/null 2>&1 || true"
    fi
}

has_nonempty_ssl_pair() {
    local cert_file="$1"
    local key_file="$2"

    [ -s "$cert_file" ] && [ -s "$key_file" ]
}

copy_acme_cert_pair_from_store() {
    local identifier="$1"
    local cert_file="$2"
    local key_file="$3"
    local acme_home=""
    local candidate_dir=""
    local candidate_cert=""
    local candidate_key=""

    for acme_home in "${HOME}/.acme.sh" "/root/.acme.sh"; do
        [ -d "$acme_home" ] || continue
        for candidate_dir in "${acme_home}/${identifier}" "${acme_home}/${identifier}_ecc"; do
            [ -d "$candidate_dir" ] || continue

            candidate_cert="${candidate_dir}/fullchain.cer"
            [ -s "$candidate_cert" ] || candidate_cert="${candidate_dir}/${identifier}.cer"
            candidate_key="${candidate_dir}/${identifier}.key"

            if [ -s "$candidate_cert" ] && [ -s "$candidate_key" ] &&
                cp "$candidate_cert" "$cert_file" &&
                cp "$candidate_key" "$key_file"; then
                return 0
            fi
        done
    done

    return 1
}

install_acme_cert_pair() {
    local acme_bin="$1"
    local identifier="$2"
    local cert_dir="$3"
    local reload_cmd="$4"
    local cert_file="${cert_dir}/fullchain.pem"
    local key_file="${cert_dir}/privkey.pem"

    "$acme_bin" --installcert -d "$identifier" \
        --key-file "$key_file" \
        --fullchain-file "$cert_file" \
        --reloadcmd "$reload_cmd" >/dev/null 2>&1 || true
    if has_nonempty_ssl_pair "$cert_file" "$key_file"; then
        return 0
    fi

    "$acme_bin" --installcert -d "$identifier" --ecc \
        --key-file "$key_file" \
        --fullchain-file "$cert_file" \
        --reloadcmd "$reload_cmd" >/dev/null 2>&1 || true
    if has_nonempty_ssl_pair "$cert_file" "$key_file"; then
        return 0
    fi

    if copy_acme_cert_pair_from_store "$identifier" "$cert_file" "$key_file" &&
        has_nonempty_ssl_pair "$cert_file" "$key_file"; then
        return 0
    fi

    rm -f "$cert_file" "$key_file" 2>/dev/null || true
    return 1
}

setup_ssl_certificate() {
    local domain="$1"
    local http_port="${2:-80}"
    local acme_bin=""
    local cert_dir="$DATA_DIR/certs/${domain}"
    local reload_cmd=""
    local issue_log=""
    local force_flag=()

    if [ -z "$domain" ]; then
        colorized_echo red "Domain is required for SSL certificate issuance."
        return 1
    fi

    if ! is_domain "$domain"; then
        colorized_echo red "Invalid domain format: ${domain}"
        return 1
    fi

    if ! [[ "$http_port" =~ ^[0-9]+$ ]] || [ "$http_port" -lt 1 ] || [ "$http_port" -gt 65535 ]; then
        colorized_echo red "Invalid HTTP challenge port: ${http_port}"
        return 1
    fi

    ensure_acme_dependencies

    if ! acme_bin=$(get_acme_sh_binary); then
        install_acme || return 1
        acme_bin=$(get_acme_sh_binary) || {
            colorized_echo red "acme.sh binary not found after installation."
            return 1
        }
    fi

    if ! preflight_http01_challenge "$http_port" "$domain"; then
        print_ssl_troubleshoot "$domain" "$http_port"
        return 1
    fi

    mkdir -p "$cert_dir"
    reload_cmd=$(build_hpxpanel_ssl_reload_command)
    prepare_acme_account "$acme_bin" "$domain"

    # Only force-reissue when a broken/partial store already exists.
    if [ -d "${HOME}/.acme.sh/${domain}" ] || [ -d "${HOME}/.acme.sh/${domain}_ecc" ] ||
        [ -d "/root/.acme.sh/${domain}" ] || [ -d "/root/.acme.sh/${domain}_ecc" ]; then
        force_flag=(--force)
        colorized_echo yellow "Existing ACME order found — reissuing with --force."
    fi

    issue_log=$(mktemp)
    colorized_echo blue "Issuing Let's Encrypt certificate for ${domain} (HTTP-01 on :${http_port})..."
    if ! "$acme_bin" --issue -d "$domain" --standalone --httpport "$http_port" \
        --keylength ec-256 --server letsencrypt "${force_flag[@]}" 2>&1 | tee "$issue_log"; then
        colorized_echo red "Failed to issue certificate for ${domain}."
        print_ssl_troubleshoot "$domain" "$http_port"
        rm -rf "${HOME}/.acme.sh/${domain}" "${HOME}/.acme.sh/${domain}_ecc" \
            "/root/.acme.sh/${domain}" "/root/.acme.sh/${domain}_ecc" "$cert_dir" 2>/dev/null || true
        rm -f "$issue_log"
        return 1
    fi
    rm -f "$issue_log"

    if ! install_acme_cert_pair "$acme_bin" "$domain" "$cert_dir" "$reload_cmd"; then
        colorized_echo red "Failed to install certificate for ${domain}."
        print_ssl_troubleshoot "$domain" "$http_port"
        return 1
    fi

    ensure_acme_auto_renew "$acme_bin"
    chmod 600 "${cert_dir}/privkey.pem" 2>/dev/null || true
    chmod 644 "${cert_dir}/fullchain.pem" 2>/dev/null || true

    colorized_echo green "SSL certificate installed successfully."
    colorized_echo green "Certificate: ${cert_dir}/fullchain.pem"
    colorized_echo green "Private key: ${cert_dir}/privkey.pem"
    return 0
}

setup_ip_ssl_certificate() {
    local ipv4="$1"
    local ipv6="$2"
    local http_port="${3:-80}"
    local acme_bin=""
    local cert_dir="$DATA_DIR/certs/ip"
    local reload_cmd=""
    local domain_args=()
    local force_flag=()

    if ! is_ipv4 "$ipv4"; then
        colorized_echo red "Invalid IPv4 address: ${ipv4}"
        return 1
    fi

    if [ -n "$ipv6" ] && ! is_ipv6 "$ipv6"; then
        colorized_echo red "Invalid IPv6 address: ${ipv6}"
        return 1
    fi

    if ! [[ "$http_port" =~ ^[0-9]+$ ]] || [ "$http_port" -lt 1 ] || [ "$http_port" -gt 65535 ]; then
        colorized_echo red "Invalid HTTP challenge port: ${http_port}"
        return 1
    fi

    ensure_acme_dependencies

    if ! acme_bin=$(get_acme_sh_binary); then
        install_acme || return 1
        acme_bin=$(get_acme_sh_binary) || {
            colorized_echo red "acme.sh binary not found after installation."
            return 1
        }
    fi

    colorized_echo yellow "IP certificates are short-lived and stricter than domain certs. Prefer option 1 (domain) when possible."
    if ! preflight_http01_challenge "$http_port" "" "$ipv4"; then
        print_ssl_troubleshoot "$ipv4" "$http_port"
        return 1
    fi

    mkdir -p "$cert_dir"
    reload_cmd=$(build_hpxpanel_ssl_reload_command)
    prepare_acme_account "$acme_bin"
    domain_args=(-d "$ipv4")
    if [ -n "$ipv6" ]; then
        domain_args+=(-d "$ipv6")
    fi

    if [ -d "${HOME}/.acme.sh/${ipv4}" ] || [ -d "/root/.acme.sh/${ipv4}" ]; then
        force_flag=(--force)
    fi

    colorized_echo blue "Issuing Let's Encrypt IP certificate for ${ipv4}..."
    if ! "$acme_bin" --issue \
        "${domain_args[@]}" \
        --standalone \
        --server letsencrypt \
        --certificate-profile shortlived \
        --days 6 \
        --httpport "$http_port" \
        "${force_flag[@]}"; then
        colorized_echo red "Failed to issue IP certificate."
        print_ssl_troubleshoot "$ipv4" "$http_port"
        rm -rf "${HOME}/.acme.sh/${ipv4}" "/root/.acme.sh/${ipv4}" "$cert_dir" 2>/dev/null || true
        [ -n "$ipv6" ] && rm -rf "${HOME}/.acme.sh/${ipv6}" "/root/.acme.sh/${ipv6}" 2>/dev/null || true
        return 1
    fi

    if ! install_acme_cert_pair "$acme_bin" "$ipv4" "$cert_dir" "$reload_cmd"; then
        colorized_echo red "Failed to install IP certificate files."
        print_ssl_troubleshoot "$ipv4" "$http_port"
        rm -rf "$cert_dir" 2>/dev/null || true
        return 1
    fi

    ensure_acme_auto_renew "$acme_bin"
    chmod 600 "${cert_dir}/privkey.pem" 2>/dev/null || true
    chmod 644 "${cert_dir}/fullchain.pem" 2>/dev/null || true

    colorized_echo green "IP certificate installed successfully."
    colorized_echo green "Certificate: ${cert_dir}/fullchain.pem"
    colorized_echo green "Private key: ${cert_dir}/privkey.pem"
    return 0
}

configure_custom_ssl_certificate() {
    local cert_source="$1"
    local key_source="$2"
    local ca_type="${3:-public}"
    local cert_dir="$DATA_DIR/certs/custom"
    local target_cert="${cert_dir}/fullchain.pem"
    local target_key="${cert_dir}/privkey.pem"

    if [ ! -f "$cert_source" ] || [ ! -r "$cert_source" ] || [ ! -s "$cert_source" ]; then
        colorized_echo red "Certificate file is missing or unreadable: $cert_source"
        return 1
    fi
    if [ ! -f "$key_source" ] || [ ! -r "$key_source" ] || [ ! -s "$key_source" ]; then
        colorized_echo red "Key file is missing or unreadable: $key_source"
        return 1
    fi

    mkdir -p "$cert_dir"
    cp "$cert_source" "$target_cert"
    cp "$key_source" "$target_key"
    chmod 644 "$target_cert" 2>/dev/null || true
    chmod 600 "$target_key" 2>/dev/null || true

    enable_hpxpanel_ssl_env "$target_cert" "$target_key" "$ca_type"
    colorized_echo green "Custom SSL certificate configured successfully."
    return 0
}

enable_hpxpanel_ssl_env() {
    local cert_file="$1"
    local key_file="$2"
    local ca_type="${3:-public}"

    set_or_uncomment_env_var "UVICORN_SSL_CERTFILE" "$cert_file" true "$ENV_FILE"
    set_or_uncomment_env_var "UVICORN_SSL_KEYFILE" "$key_file" true "$ENV_FILE"
    set_or_uncomment_env_var "UVICORN_SSL_CA_TYPE" "$ca_type" true "$ENV_FILE"
}

disable_hpxpanel_ssl_env() {
    comment_out_env_var "UVICORN_SSL_CERTFILE" "$ENV_FILE"
    comment_out_env_var "UVICORN_SSL_KEYFILE" "$ENV_FILE"
    comment_out_env_var "UVICORN_SSL_CA_TYPE" "$ENV_FILE"
}

setup_hpxpanel_ssl_during_install() {
    local ssl_mode="$1"
    local ssl_domain="$2"
    local ssl_http_port="$3"
    local ssl_choice=""
    local detected_ipv4=""
    local input_ipv4=""
    local input_ipv6=""
    local custom_cert=""
    local custom_key=""
    local custom_ca_choice=""
    local custom_ca_type="public"

    if [ "$ssl_mode" = "disabled" ]; then
        disable_hpxpanel_ssl_env
        colorized_echo yellow "Skipping SSL (--no-ssl). Dashboard binds to localhost only."
        return 0
    fi

    if ! [[ "$ssl_http_port" =~ ^[0-9]+$ ]] || [ "$ssl_http_port" -lt 1 ] || [ "$ssl_http_port" -gt 65535 ]; then
        colorized_echo red "Invalid SSL HTTP challenge port: ${ssl_http_port}"
        return 1
    fi

    if [ "$ssl_mode" = "domain" ] && [ -n "$ssl_domain" ]; then
        ssl_choice="1"
    else
        colorized_echo cyan "HPXPANEL // SSL channel setup:"
        colorized_echo green "  1) Let's Encrypt Domain certificate"
        colorized_echo green "  2) Let's Encrypt IP certificate (short-lived)"
        colorized_echo green "  3) Custom certificate + key paths"
        colorized_echo yellow "  4) No SSL"
        colorized_echo yellow "Port 80 (or configured --ssl-http-port) must be reachable for Let's Encrypt."
        read -p "Select SSL option [1-4] (default 1) >  " ssl_choice
        ssl_choice="${ssl_choice// /}"
        [ -z "$ssl_choice" ] && ssl_choice="1"
    fi

    case "$ssl_choice" in
    1)
        while [ -z "$ssl_domain" ]; do
            read -p "Enter domain for SSL certificate (example: panel.example.com): " ssl_domain
            ssl_domain="${ssl_domain// /}"

            if [ -z "$ssl_domain" ]; then
                colorized_echo red "Domain cannot be empty."
                continue
            fi

            if ! is_domain "$ssl_domain"; then
                colorized_echo red "Invalid domain format: ${ssl_domain}"
                ssl_domain=""
            fi
        done

        if setup_ssl_certificate "$ssl_domain" "$ssl_http_port"; then
            enable_hpxpanel_ssl_env "${DATA_DIR}/certs/${ssl_domain}/fullchain.pem" "${DATA_DIR}/certs/${ssl_domain}/privkey.pem" "public"
            colorized_echo green "SSL enabled for https://${ssl_domain}:8000/dashboard/"
            # Restart panel if already running so new cert is picked up.
            if is_hpxpanel_installed && is_hpxpanel_up 2>/dev/null; then
                detect_compose
                $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" restart >/dev/null 2>&1 || true
            fi
            return 0
        fi
        colorized_echo yellow "You can retry later with:  hpxpanel ssl"
        ;;
    2)
        colorized_echo yellow "Tip: domain certificates (option 1) are more reliable than IP certificates."
        detected_ipv4=$(get_public_ipv4 || true)
        if [ -n "$detected_ipv4" ]; then
            read -p "Enter IPv4 for SSL certificate (default: ${detected_ipv4}): " input_ipv4
            input_ipv4="${input_ipv4// /}"
            [ -z "$input_ipv4" ] && input_ipv4="$detected_ipv4"
        else
            read -p "Enter IPv4 for SSL certificate: " input_ipv4
            input_ipv4="${input_ipv4// /}"
        fi

        if ! is_ipv4 "$input_ipv4"; then
            colorized_echo red "Invalid IPv4 address: ${input_ipv4}"
            disable_hpxpanel_ssl_env
            colorized_echo yellow "Continuing without SSL."
            return 0
        fi

        read -p "Enter IPv6 for SSL certificate (optional, press Enter to skip): " input_ipv6
        input_ipv6="${input_ipv6// /}"
        if [ -n "$input_ipv6" ] && ! is_ipv6 "$input_ipv6"; then
            colorized_echo red "Invalid IPv6 address: ${input_ipv6}"
            disable_hpxpanel_ssl_env
            colorized_echo yellow "Continuing without SSL."
            return 0
        fi

        if setup_ip_ssl_certificate "$input_ipv4" "$input_ipv6" "$ssl_http_port"; then
            enable_hpxpanel_ssl_env "${DATA_DIR}/certs/ip/fullchain.pem" "${DATA_DIR}/certs/ip/privkey.pem" "public"
            colorized_echo green "SSL enabled for https://${input_ipv4}:8000/dashboard/"
            return 0
        fi
        ;;
    3)
        while true; do
            read -p "Enter full path to certificate file (crt/pem/fullchain): " custom_cert
            custom_cert=$(echo "$custom_cert" | tr -d '"' | tr -d "'" | xargs)
            if [ -f "$custom_cert" ] && [ -r "$custom_cert" ] && [ -s "$custom_cert" ]; then
                break
            fi
            colorized_echo red "Certificate file not found/readable: $custom_cert"
        done

        while true; do
            read -p "Enter full path to private key file (key/pem): " custom_key
            custom_key=$(echo "$custom_key" | tr -d '"' | tr -d "'" | xargs)
            if [ -f "$custom_key" ] && [ -r "$custom_key" ] && [ -s "$custom_key" ]; then
                break
            fi
            colorized_echo red "Private key file not found/readable: $custom_key"
        done

        read -p "Is this certificate from a public CA? [Y/n]: " custom_ca_choice
        if [[ -n "$custom_ca_choice" && ! "$custom_ca_choice" =~ ^[Yy]$ ]]; then
            custom_ca_type="private"
        fi

        if configure_custom_ssl_certificate "$custom_cert" "$custom_key" "$custom_ca_type"; then
            colorized_echo green "SSL enabled from custom certificate files."
            return 0
        fi
        ;;
    4)
        disable_hpxpanel_ssl_env
        colorized_echo yellow "Continuing without SSL."
        return 0
        ;;
    *)
        disable_hpxpanel_ssl_env
        colorized_echo yellow "Invalid SSL option. Continuing without SSL."
        return 0
        ;;
    esac

    disable_hpxpanel_ssl_env
    colorized_echo yellow "SSL setup failed. Continuing without SSL."
    colorized_echo yellow "Fix DNS/firewall/port 80, then run:  hpxpanel ssl"
    colorized_echo yellow "Or edit ${ENV_FILE} manually."
    return 0
}

ssl_command() {
    check_running_as_root
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi
    detect_compose
    local ssl_http_port="80"
    while [ $# -gt 0 ]; do
        case "$1" in
        --ssl-http-port)
            ssl_http_port="$2"
            shift 2
            ;;
        --domain)
            if setup_ssl_certificate "$2" "$ssl_http_port"; then
                enable_hpxpanel_ssl_env "${DATA_DIR}/certs/${2}/fullchain.pem" "${DATA_DIR}/certs/${2}/privkey.pem" "public"
                if is_hpxpanel_up 2>/dev/null; then
                    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" restart >/dev/null 2>&1 || true
                fi
                colorized_echo green "SSL enabled for https://${2}:8000/dashboard/"
                return 0
            fi
            exit 1
            ;;
        -h|--help)
            echo "Usage: hpxpanel ssl [--domain example.com] [--ssl-http-port 80]"
            return 0
            ;;
        *)
            colorized_echo red "Unknown option: $1"
            echo "Usage: hpxpanel ssl [--domain example.com] [--ssl-http-port 80]"
            exit 1
            ;;
        esac
    done
    setup_hpxpanel_ssl_during_install "auto" "" "$ssl_http_port"
    if is_hpxpanel_up 2>/dev/null; then
        $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" restart >/dev/null 2>&1 || true
    fi
}

compose_service_exists() {
    local service_name="$1"
    [ -z "$service_name" ] && return 1
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" config --services 2>/dev/null | grep -Fxq "$service_name"
}

list_hpxpanel_app_services() {
    local detected_services=""
    detected_services=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" config 2>/dev/null | awk '
        BEGIN { in_services = 0; service = ""; is_app = 0 }
        function flush_service() {
            if (service != "" && is_app) {
                print service
            }
        }
        /^services:[[:space:]]*$/ {
            in_services = 1
            next
        }
        in_services && /^[^[:space:]]/ {
            flush_service()
            in_services = 0
            service = ""
            is_app = 0
            next
        }
        !in_services {
            next
        }
        /^  [A-Za-z0-9_.-]+:[[:space:]]*$/ {
            flush_service()
            service = $0
            sub(/^  /, "", service)
            sub(/:[[:space:]]*$/, "", service)
            is_app = 0
            next
        }
        /^[[:space:]]+image:[[:space:]]*(ghcr\.io\/pooyahpx\/hpxpanel)([:@].*)?$/ {
            is_app = 1
            next
        }
        /^[[:space:]]+ROLE:[[:space:]]*(backend|node|scheduler)([[:space:]]|$)/ {
            is_app = 1
            next
        }
        /^[[:space:]]+-[[:space:]]*ROLE=(backend|node|scheduler)([[:space:]]|$)/ {
            is_app = 1
            next
        }
        END {
            flush_service()
        }
    ' 2>/dev/null || true)

    if [ -n "$detected_services" ]; then
        echo "$detected_services"
        return 0
    fi

    for candidate in panel hpxpanel node-worker scheduler; do
        if compose_service_exists "$candidate"; then
            echo "$candidate"
        fi
    done
}

detect_hpxpanel_backend_service() {
    local service_name=""

    for candidate in panel hpxpanel; do
        if compose_service_exists "$candidate"; then
            echo "$candidate"
            return 0
        fi
    done

    service_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" config 2>/dev/null | awk '
        BEGIN { in_services = 0; service = ""; is_backend = 0 }
        function flush_service() {
            if (service != "" && is_backend) {
                print service
                exit
            }
        }
        /^services:[[:space:]]*$/ {
            in_services = 1
            next
        }
        in_services && /^[^[:space:]]/ {
            flush_service()
            in_services = 0
            next
        }
        !in_services {
            next
        }
        /^  [A-Za-z0-9_.-]+:[[:space:]]*$/ {
            flush_service()
            service = $0
            sub(/^  /, "", service)
            sub(/:[[:space:]]*$/, "", service)
            is_backend = 0
            next
        }
        /^[[:space:]]+ROLE:[[:space:]]*backend([[:space:]]|$)/ {
            is_backend = 1
            next
        }
        /^[[:space:]]+-[[:space:]]*ROLE=backend([[:space:]]|$)/ {
            is_backend = 1
            next
        }
        END {
            if (service != "" && is_backend) {
                print service
            }
        }
    ' | head -n 1)

    if [ -n "$service_name" ]; then
        echo "$service_name"
        return 0
    fi

    service_name=$(list_hpxpanel_app_services | head -n 1)
    if [ -n "$service_name" ]; then
        echo "$service_name"
        return 0
    fi

    return 1
}

stop_hpxpanel_app_services() {
    local services
    services=$(list_hpxpanel_app_services | xargs)
    [ -z "$services" ] && services="hpxpanel"
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" stop $services 2>/dev/null || true
}

start_hpxpanel_app_services() {
    local services
    services=$(list_hpxpanel_app_services | xargs)
    [ -z "$services" ] && services="hpxpanel"
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" start $services 2>/dev/null || true
}

find_container() {
    local db_type=$1
    local container_name=""
    detect_compose

    case $db_type in
    mariadb)
        container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
        [ -z "$container_name" ] && container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps --format json mariadb 2>/dev/null | jq -r '.Name' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name=$(docker ps --filter "name=${APP_NAME}" --filter "name=mariadb" --format '{{.ID}}' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name="mariadb"
        ;;
    mysql)
        container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mysql 2>/dev/null || true)
        [ -z "$container_name" ] && container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
        [ -z "$container_name" ] && container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps --format json mysql mariadb 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name=$(docker ps --filter "name=${APP_NAME}" --filter "name=mysql" --format '{{.ID}}' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name=$(docker ps --filter "name=${APP_NAME}" --filter "name=mariadb" --format '{{.ID}}' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name="mysql"
        ;;
    postgresql|timescaledb)
        container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q timescaledb 2>/dev/null || true)
        [ -z "$container_name" ] && container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q postgresql 2>/dev/null || true)
        [ -z "$container_name" ] && container_name=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps --format json timescaledb postgresql 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name' 2>/dev/null | head -n 1 || true)
        [ -z "$container_name" ] && container_name="${APP_NAME}-timescaledb-1"
        ;;
    esac
    echo "$container_name"
}

check_container() {
    local container_name=$1
    local db_type=$2
    local actual_container=""

    if docker inspect "$container_name" >/dev/null 2>&1; then
        actual_container="$container_name"
    else
        case $db_type in
        mariadb)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-mariadb-1"
            ;;
        mysql)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mysql 2>/dev/null || true)
            [ -z "$actual_container" ] && actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-mysql-1"
            ;;
        postgresql|timescaledb)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q postgresql 2>/dev/null || true)
            [ -z "$actual_container" ] && actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q timescaledb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-postgresql-1"
            ;;
        esac
    fi

    [ -z "$actual_container" ] && { echo ""; return 1; }
    container_name="$actual_container"
    docker ps --filter "id=${container_name}" --format '{{.ID}}' 2>/dev/null | grep -q . || \
    docker ps --filter "name=${container_name}" --format '{{.Names}}' 2>/dev/null | grep -q . || \
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qE "^${container_name}$|/${container_name}$" || \
    docker ps --format '{{.ID}}' 2>/dev/null | grep -q "^${container_name}" || { echo ""; return 1; }
    echo "$container_name"
    return 0
}

verify_and_start_container() {
    local container_name=$1
    local db_type=$2
    local actual_container=""

    if docker inspect "$container_name" >/dev/null 2>&1; then
        actual_container="$container_name"
    else
        case $db_type in
        mariadb)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-mariadb-1"
            ;;
        mysql)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mysql 2>/dev/null || true)
            [ -z "$actual_container" ] && actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q mariadb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-mysql-1"
            ;;
        postgresql|timescaledb)
            actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q postgresql 2>/dev/null || true)
            [ -z "$actual_container" ] && actual_container=$($COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" ps -q timescaledb 2>/dev/null || true)
            [ -z "$actual_container" ] && [ -f "$COMPOSE_FILE" ] && actual_container="${APP_NAME}-postgresql-1"
            ;;
        esac
    fi

    [ -z "$actual_container" ] && { echo ""; return 1; }
    container_name="$actual_container"
    local container_running=false
    docker ps --filter "id=${container_name}" --format '{{.ID}}' 2>/dev/null | grep -q . && container_running=true || \
    docker ps --filter "name=${container_name}" --format '{{.Names}}' 2>/dev/null | grep -q . && container_running=true || \
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qE "^${container_name}$|/${container_name}$" && container_running=true || \
    docker ps --format '{{.ID}}' 2>/dev/null | grep -q "^${container_name}" && container_running=true

    if [ "$container_running" = false ]; then
        colorized_echo yellow "Database container '$container_name' is not running. Attempting to start it..."
        docker start "$container_name" >/dev/null 2>&1 || \
        $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" start "${db_type%%|*}" 2>/dev/null || true
        sleep 2
        docker ps --filter "id=${container_name}" --format '{{.ID}}' 2>/dev/null | grep -q . && container_running=true || \
        docker ps --filter "name=${container_name}" --format '{{.Names}}' 2>/dev/null | grep -q . && container_running=true
    fi

    [ "$container_running" = true ] && { echo "$container_name"; return 0; } || { echo ""; return 1; }
}

install_hpxpanel_script() {
    FETCH_REPO="pooyahpx/HPXPANEL"
    colorized_echo blue "Installing HPXPANEL CLI"
    install_shared_libs_from_repo "$FETCH_REPO" common.sh system.sh docker.sh github.sh env.sh hpxpanel-backup.sh hpxpanel-restore.sh
    github_install_script_from_repo "$FETCH_REPO" "scripts/hpxpanel.sh" "hpxpanel"
    colorized_echo green "HPXPANEL CLI installed successfully"
}

is_hpxpanel_installed() {
    if [ -d $APP_DIR ]; then
        return 0
    else
        return 1
    fi
}


ensure_hpx_engine_image() {
    local tag="${1:-latest}"
    local wanted="ghcr.io/pooyahpx/hpxpanel:${tag}"
    colorized_echo blue "Preparing HPXPANEL engine image (${tag})..."
    if docker image inspect "$wanted" >/dev/null 2>&1; then
        colorized_echo green "Engine image ready (local)"
        return 0
    fi
    if docker pull "$wanted"; then
        colorized_echo green "Engine image pulled from GHCR"
        return 0
    fi
    colorized_echo red "Could not pull ${wanted}"
    colorized_echo yellow "Build the image first: GitHub Actions → \"Build and push panel image (GHCR)\" → Run workflow"
    colorized_echo yellow "Repo: https://github.com/pooyahpx/HPXPANEL/actions"
    return 1
}
set_hpxpanel_image() {
    local target_image="$1"
    local service_name=""
    local image_name=""
    local updated_any=false

    while IFS= read -r service_name; do
        [ -z "$service_name" ] && continue
        image_name=$(yq eval -r ".services.\"${service_name}\".image // \"\"" "$COMPOSE_FILE" 2>/dev/null)
        if [[ "$image_name" =~ ^ghcr.io/pooyahpx/hpxpanel([:@].*)?$ ]]; then
            yq -i ".services.\"${service_name}\".image = \"${target_image}\"" "$COMPOSE_FILE"
            updated_any=true
        fi
    done < <(yq eval -r '.services | keys | .[]' "$COMPOSE_FILE" 2>/dev/null || true)

    if [ "$updated_any" = false ]; then
        for service_name in panel hpxpanel node-worker scheduler; do
            if yq eval -e ".services.\"${service_name}\"" "$COMPOSE_FILE" >/dev/null 2>&1; then
                yq -i ".services.\"${service_name}\".image = \"${target_image}\"" "$COMPOSE_FILE"
                updated_any=true
            fi
        done
    fi

    if [ "$updated_any" = false ]; then
        yq -i ".services.hpxpanel.image = \"${target_image}\"" "$COMPOSE_FILE"
    fi
}

install_hpxpanel() {
    local panel_version=$1
    local major_version=$2
    local database_type=$3
    local existing_db_password=""
    local existing_db_user=""
    local existing_db_name=""

    FILES_URL_PREFIX="https://raw.githubusercontent.com/pooyahpx/HPXPANEL"
    COMPOSE_FILES_URL_PREFIX="https://raw.githubusercontent.com/pooyahpx/HPXPANEL/main/scripts/docker-compose"

    mkdir -p "$DATA_DIR"
    mkdir -p "$APP_DIR"

    # Preserve DB secrets before we overwrite .env — required when reusing an
    # already-initialized Postgres/MySQL data directory (POSTGRES_PASSWORD is
    # only applied on first boot).
    if [ -f "$APP_DIR/.env" ]; then
        existing_db_password=$(grep -E '^DB_PASSWORD=' "$APP_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)
        existing_db_user=$(grep -E '^DB_USER=' "$APP_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)
        existing_db_name=$(grep -E '^DB_NAME=' "$APP_DIR/.env" 2>/dev/null | head -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//" || true)
        cp -a "$APP_DIR/.env" "$APP_DIR/.env.bak.$(date +%s)" 2>/dev/null || true
    fi

    colorized_echo blue "Fetching .env file"
    # Pre-create .env as 0600 (and tighten any pre-existing copy) so the DB,
    # pgAdmin and MySQL-root secrets written below are never world-readable.
    harden_secret_file "$APP_DIR/.env"
    curl -fsL "$FILES_URL_PREFIX/main/.env.example" -o "$APP_DIR/.env"

    colorized_echo green "File saved in $APP_DIR/.env"

    if [[ "$database_type" =~ ^(mysql|mariadb|postgresql|timescaledb)$ ]]; then

        case "$database_type" in
        mysql) db_name="MySQL" ;;
        mariadb) db_name="MariaDB" ;;
        timescaledb) db_name="TimeScaleDB" ;;
        *) db_name="PostgreSQL" ;;
        esac

        echo "----------------------------"
        colorized_echo red "Database engine: $db_name"
        echo "----------------------------"
        colorized_echo blue "Fetching HPXPANEL stack compose · $db_name"
        curl -fsL "$COMPOSE_FILES_URL_PREFIX/hpxpanel-$database_type.yml" -o "$COMPOSE_FILE"

        # Comment out the SQLite line
        sed -i 's~^SQLALCHEMY_DATABASE_URL = "sqlite~#&~' "$APP_DIR/.env"

        DB_NAME="${existing_db_name:-hpxpanel}"
        DB_USER="${existing_db_user:-hpxpanel}"
        if [ "${KEEP_EXISTING_DB_DATA:-0}" = "1" ] && [ -n "$existing_db_password" ]; then
            DB_PASSWORD="$existing_db_password"
            colorized_echo green "Reusing database password from previous .env (existing DB volume kept)."
        elif [ "${KEEP_EXISTING_DB_DATA:-0}" = "1" ]; then
            colorized_echo yellow "Existing DB volume kept but no old DB_PASSWORD found."
            read -p "Enter the existing database password: " DB_PASSWORD
            DB_PASSWORD="${DB_PASSWORD// /}"
            if [ -z "$DB_PASSWORD" ]; then
                colorized_echo red "Password required when keeping an existing database volume."
                exit 1
            fi
        else
            DB_NAME="hpxpanel"
            DB_USER="hpxpanel"
            prompt_for_db_password
        fi

        echo "" >>"$ENV_FILE"
        echo "# Database configuration" >>"$ENV_FILE"
        echo "DB_NAME=\"${DB_NAME}\"" >>"$ENV_FILE"
        echo "DB_USER=\"${DB_USER}\"" >>"$ENV_FILE"
        echo "DB_PASSWORD=\"${DB_PASSWORD}\"" >>"$ENV_FILE"

        if [[ "$database_type" == "postgresql" || "$database_type" == "timescaledb" ]]; then
            DB_PORT="6432"
            prompt_for_pgadmin_password
            echo "" >>"$ENV_FILE"
            echo "# PGAdmin configuration" >>"$ENV_FILE"
            echo "PGADMIN_EMAIL=\"pg@github.io\"" >>"$ENV_FILE"
            echo "PGADMIN_PASSWORD=\"${PGADMIN_PASSWORD}\"" >>"$ENV_FILE"
        else
            colorized_echo green "phpMyAdmin address: 0.0.0.0:8010"
            DB_PORT="3306"
            MYSQL_ROOT_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20 || true)
            echo "MYSQL_ROOT_PASSWORD=\"$MYSQL_ROOT_PASSWORD\"" >>"$ENV_FILE"
        fi

        if [[ "$database_type" =~ ^(postgresql|timescaledb)$ ]]; then
            if [ "$major_version" -lt 1 ]; then
                colorized_echo red "Error: --database $database_type is only supported in v1.0.0 and later."
                colorized_echo yellow "Use --pre-release or --version v1.x.y, or choose mysql/mariadb/sqlite for v0.x."
                exit 1
            fi
            db_driver_scheme="postgresql+asyncpg"
        else
            db_driver_scheme="mysql+asyncmy"
        fi

        SQLALCHEMY_DATABASE_URL="${db_driver_scheme}://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${DB_PORT}/${DB_NAME}"

        echo "" >>"$ENV_FILE"
        echo "# SQLAlchemy Database URL" >>"$ENV_FILE"
        echo "SQLALCHEMY_DATABASE_URL=\"$SQLALCHEMY_DATABASE_URL\"" >>"$ENV_FILE"

    else
        echo "----------------------------"
        colorized_echo red "Database engine: SQLite"
        echo "----------------------------"
        colorized_echo blue "Fetching HPXPANEL stack compose · SQLite"
        curl -fsL "$COMPOSE_FILES_URL_PREFIX/hpxpanel-sqlite.yml" -o "$COMPOSE_FILE"

        sed -i 's/^# \(SQLALCHEMY_DATABASE_URL = .*\)$/\1/' "$APP_DIR/.env"

        if [ "$major_version" -eq 1 ]; then
            db_driver_scheme="sqlite+aiosqlite"
        elif grep -Eq '^[#[:space:]]*SQLALCHEMY_DATABASE_URL[[:space:]]*=[[:space:]]*"sqlite\+aiosqlite' "$APP_DIR/.env"; then
            # Keep v1 check strict; use template hint for newer versions (e.g., v2+).
            db_driver_scheme="sqlite+aiosqlite"
        else
            db_driver_scheme="sqlite"
        fi

        sed -i "s~\(SQLALCHEMY_DATABASE_URL = \).*~\1\"${db_driver_scheme}:////${DATA_DIR}/db.sqlite3\"~" "$APP_DIR/.env"

    fi

    # Install requested version
    local target_image="ghcr.io/pooyahpx/hpxpanel:${panel_version}"
    if [ "$panel_version" == "latest" ]; then
        target_image="ghcr.io/pooyahpx/hpxpanel:latest"
    fi
    case "$panel_version" in
    latest|dev|pre-release) ensure_hpx_engine_image latest || exit 1 ;;
    *) ensure_hpx_engine_image "${panel_version#v}" || ensure_hpx_engine_image latest || exit 1 ;;
    esac
    set_hpxpanel_image "$target_image"
    colorized_echo green "File saved in $APP_DIR/docker-compose.yml"

    colorized_echo green "HPXPANEL installed successfully"
}

up_hpxpanel() {
    compose_up
}

status_command() {

    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        echo -n "Status: "
        colorized_echo red "Not Installed"
        exit 1
    fi

    detect_compose

    if ! is_hpxpanel_up; then
        echo -n "Status: "
        colorized_echo blue "Down"
        exit 1
    fi

    echo -n "Status: "
    colorized_echo green "Up"

    json=$($COMPOSE -f $COMPOSE_FILE ps -a --format=json)
    services=$(echo "$json" | jq -r 'if type == "array" then .[] else . end | .Service')
    states=$(echo "$json" | jq -r 'if type == "array" then .[] else . end | .State')
    # Print out the service names and statuses
    for i in $(seq 0 $(expr $(echo $services | wc -w) - 1)); do
        service=$(echo $services | cut -d' ' -f $(expr $i + 1))
        state=$(echo $states | cut -d' ' -f $(expr $i + 1))
        echo -n "- $service: "
        if [ "$state" == "running" ]; then
            colorized_echo green $state
        else
            colorized_echo red $state
        fi
    done
}

prompt_for_db_password() {
    DB_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20 || true)
    colorized_echo green "Generated a secure database password (saved in .env)."
    colorized_echo green "This password will be recorded in the .env file for future use."

}

prompt_for_pgadmin_password() {
    PGADMIN_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20 || true)
    colorized_echo green "Generated a secure pgAdmin password (saved in .env)."
    colorized_echo green "pgAdmin address: 0.0.0.0:8010"
    colorized_echo green "pgAdmin default email: pg@github.io"
    colorized_echo green "pgAdmin Password: $PGADMIN_PASSWORD"
    colorized_echo green "This password will be recorded in the .env file for future use."

}

check_existing_database_volumes() {
    local db_type=$1
    local found_paths=()
    local found_named_volumes=()
    KEEP_EXISTING_DB_DATA=0

    if [[ "$db_type" == "sqlite" ]]; then
        return 0
    fi

    case "$db_type" in
    mariadb|mysql)
        found_paths=("/var/lib/mysql/hpxpanel" "/var/lib/mysql/pasarguard")
        ;;
    postgresql|timescaledb)
        found_paths=("/var/lib/postgresql/hpxpanel" "/var/lib/postgresql/pasarguard")
        found_named_volumes=("pgadmin")
        ;;
    esac

    local existing_paths=()
    for path in "${found_paths[@]}"; do
        if [ -d "$path" ] && [ -n "$(ls -A "$path" 2>/dev/null)" ]; then
            existing_paths+=("$path")
        fi
    done

    local existing_named_volumes=()
    if [ ${#found_named_volumes[@]} -gt 0 ] && command -v docker >/dev/null 2>&1; then
        for vol_name in "${found_named_volumes[@]}"; do
            local prefixed_vol="${APP_NAME}_${vol_name}"
            if docker volume ls --format '{{.Name}}' 2>/dev/null | grep -qE "^${prefixed_vol}$|^${vol_name}$"; then
                existing_named_volumes+=("$vol_name")
            fi
        done
    fi

    if [ ${#existing_paths[@]} -eq 0 ] && [ ${#existing_named_volumes[@]} -eq 0 ]; then
        return 0
    fi

    colorized_echo yellow "WARNING: Found existing database data that will conflict if the password changes:"

    for path in "${existing_paths[@]}"; do
        local dir_size
        dir_size=$(du -sh "$path" 2>/dev/null | cut -f1 || echo "unknown size")
        colorized_echo yellow "  - Directory: $path (Size: $dir_size)"
    done

    for vol_name in "${existing_named_volumes[@]}"; do
        local vol_size="unknown size"
        local prefixed_vol="${APP_NAME}_${vol_name}"
        local actual_vol
        actual_vol=$(docker volume ls --format '{{.Name}}' 2>/dev/null | grep -E "^${prefixed_vol}$|^${vol_name}$" | head -n1)
        if [ -n "$actual_vol" ]; then
            local mountpoint
            mountpoint=$(docker volume inspect "$actual_vol" --format '{{.Mountpoint}}' 2>/dev/null)
            if [ -n "$mountpoint" ] && [ -d "$mountpoint" ]; then
                vol_size=$(du -sh "$mountpoint" 2>/dev/null | cut -f1 || echo "unknown size")
            fi
            colorized_echo yellow "  - Docker volume: $actual_vol (Size: $vol_size)"
        else
            colorized_echo yellow "  - Docker volume: $vol_name"
        fi
    done

    echo
    colorized_echo red "Postgres/MySQL only reads DB_PASSWORD on FIRST init."
    colorized_echo yellow "If you keep this data, the installer must reuse the old password."
    echo
    colorized_echo cyan "Delete existing DB data and start fresh? (default: no = keep + reuse password)"
    colorized_echo yellow "WARNING: Delete permanently wipes users/settings in the database."
    read -p "Delete volumes? [y/N]: " delete_volumes

    if [[ "$delete_volumes" =~ ^[Yy]$ ]]; then
        colorized_echo yellow "Deleting volumes..."
        KEEP_EXISTING_DB_DATA=0

        for path in "${existing_paths[@]}"; do
            if rm -rf "$path" 2>/dev/null; then
                colorized_echo green "Deleted directory: $path"
            else
                colorized_echo red "Failed to delete directory: $path (may be in use or permission denied)"
            fi
        done

        for vol_name in "${existing_named_volumes[@]}"; do
            local prefixed_vol="${APP_NAME}_${vol_name}"
            local actual_vol
            actual_vol=$(docker volume ls --format '{{.Name}}' 2>/dev/null | grep -E "^${prefixed_vol}$|^${vol_name}$" | head -n1)
            if [ -n "$actual_vol" ]; then
                if docker volume rm "$actual_vol" >/dev/null 2>&1; then
                    colorized_echo green "Deleted Docker volume: $actual_vol"
                else
                    colorized_echo red "Failed to delete Docker volume: $actual_vol (may be in use)"
                fi
            fi
        done

        colorized_echo green "Volume cleanup completed."
    else
        KEEP_EXISTING_DB_DATA=1
        colorized_echo yellow "Keeping existing DB data — will reuse the previous DB_PASSWORD."
    fi
    echo
}

install_command() {
    check_running_as_root

    # Default values
    panel_version="latest"
    major_version=1
    panel_version_set="false"
    database_type="sqlite"
    ssl_mode="auto"
    ssl_domain=""
    ssl_http_port="80"
    KEEP_EXISTING_DB_DATA=0

    # Parse options
    while [[ $# -gt 0 ]]; do
        key="$1"
        case $key in
        --database)
            database_type="$2"
            if [[ ! $database_type =~ ^(mysql|mariadb|postgresql|timescaledb)$ ]]; then
                colorized_echo red "Unsupported database type: $database_type"
                exit 1
            fi
            shift 2
            ;;
        --dev)
            if [[ "$panel_version_set" == "true" ]]; then
                colorized_echo red "Error: Cannot use --pre-release , --dev and --version options simultaneously."
                exit 1
            fi
            panel_version="dev"
            panel_version_set="true"
            shift
            ;;
        --pre-release)
            if [[ "$panel_version_set" == "true" ]]; then
                colorized_echo red "Error: Cannot use --pre-release , --dev and --version options simultaneously."
                exit 1
            fi
            panel_version="pre-release"
            panel_version_set="true"
            shift
            ;;
        --version)
            if [[ "$panel_version_set" == "true" ]]; then
                colorized_echo red "Error: Cannot use --pre-release , --dev and --version options simultaneously."
                exit 1
            fi
            panel_version="$2"
            panel_version_set="true"
            shift 2
            ;;
        --ssl)
            if [[ "$ssl_mode" == "disabled" ]]; then
                colorized_echo red "Error: Cannot use --ssl and --no-ssl together."
                exit 1
            fi
            ssl_mode="enabled"
            shift
            ;;
        --no-ssl)
            if [[ "$ssl_mode" == "enabled" || -n "$ssl_domain" ]]; then
                colorized_echo red "Error: Cannot use --no-ssl with --ssl or --ssl-domain."
                exit 1
            fi
            ssl_mode="disabled"
            shift
            ;;
        --ssl-domain)
            if [ -z "${2:-}" ]; then
                colorized_echo red "Error: --ssl-domain requires a value."
                exit 1
            fi
            if [[ "$ssl_mode" == "disabled" ]]; then
                colorized_echo red "Error: Cannot use --ssl-domain with --no-ssl."
                exit 1
            fi
            ssl_domain="${2// /}"
            if ! is_domain "$ssl_domain"; then
                colorized_echo red "Invalid domain format for --ssl-domain: $ssl_domain"
                exit 1
            fi
            ssl_mode="domain"
            shift 2
            ;;
        --ssl-http-port | --ssl-port)
            if [ -z "${2:-}" ]; then
                colorized_echo red "Error: $1 requires a value."
                exit 1
            fi
            ssl_http_port="$2"
            if ! [[ "$ssl_http_port" =~ ^[0-9]+$ ]] || [ "$ssl_http_port" -lt 1 ] || [ "$ssl_http_port" -gt 65535 ]; then
                colorized_echo red "Invalid SSL HTTP challenge port: $ssl_http_port"
                exit 1
            fi
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
        esac
    done

    # Check if hpxpanel is already installed
    if is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is already installed at $APP_DIR"
        read -p "Do you want to override the previous installation? (y/n) "
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            colorized_echo red "Aborted installation"
            exit 1
        fi
    fi
    detect_os
    if ! command -v jq >/dev/null 2>&1; then
        install_package jq
    fi
    if ! command -v curl >/dev/null 2>&1; then
        install_package curl
    fi
    if ! command -v docker >/dev/null 2>&1; then
        install_docker
    fi
    ensure_docker_compose
    if ! command -v yq >/dev/null 2>&1; then
        install_yq
    fi
    detect_compose
    install_hpxpanel_script
    # Function to check if a version exists in the GitHub releases
    check_version_exists() {
        local version=$1
        repo_url="https://api.github.com/repos/pooyahpx/HPXPANEL/releases"

        if [[ "$version" == "latest" || "$version" == "pre-release" || "$version" == "dev" ]]; then
            local latest_tag
            latest_tag=$(curl -s --max-time 5 ${repo_url}/latest | jq -r '.tag_name // empty' 2>/dev/null || echo "null")
            if [ -z "$latest_tag" ] || [ "$latest_tag" == "null" ]; then
                major_version=1
                [ "$version" == "pre-release" ] && panel_version="latest"
                return 0
            fi
            major_version=$(echo "$latest_tag" | sed 's/^v//' | sed 's/[^0-9]*\([0-9]*\)\..*/\1/')
            [ -z "$major_version" ] && major_version=1
            return 0
        fi

        local http_code
        http_code=$(curl -s -o /dev/null --max-time 5 -w "%{http_code}" "${repo_url}/tags/${version}" 2>/dev/null || echo "000")
        if [[ "$http_code" == "200" || "$http_code" == "000" ]]; then
            major_version=$(echo "$version" | sed 's/^v//' | sed 's/[^0-9]*\([0-9]*\)\..*/\1/')
            [ -z "$major_version" ] && major_version=1
            return 0
        fi
        return 1
    }

    semver_regex='^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$'
    # Check if the version is valid and exists
    if [[ "$panel_version" == "latest" || "$panel_version" == "dev" || "$panel_version" == "pre-release" || "$panel_version" =~ $semver_regex ]]; then
        if check_version_exists "$panel_version"; then
            if [[ "$database_type" =~ ^(postgresql|timescaledb)$ ]] && [ "$major_version" -lt 1 ]; then
                colorized_echo red "Error: --database $database_type requires v1.0.0 or newer."
                colorized_echo yellow "Try: --pre-release or --version v1.x.y"
                exit 1
            fi
            check_existing_database_volumes "$database_type"
            install_hpxpanel "$panel_version" "$major_version" "$database_type"
            setup_hpxpanel_ssl_during_install "$ssl_mode" "$ssl_domain" "$ssl_http_port"
            echo "Installing $panel_version version"
        else
            echo "Version $panel_version does not exist. Please enter a valid version (e.g. v0.5.2)"
            exit 1
        fi
    else
        echo "Invalid version format. Please enter a valid version (e.g. v0.5.2)"
        exit 1
    fi
    install_completion

    # --- Port conflict detection ---
    # Read the configured UVICORN_PORT from .env (default: 8000)
    local configured_port
    configured_port=$(grep -E '^\s*UVICORN_PORT\s*=' "$ENV_FILE" 2>/dev/null \
        | head -1 | sed 's/^[^=]*=\s*//' | tr -d '[:space:]"' || true)
    configured_port="${configured_port:-8000}"

    if is_port_in_use "$configured_port"; then
        colorized_echo yellow "Port ${configured_port} is already in use by another service."
        colorized_echo yellow "HPXPANEL will fail to start unless a free port is used."
        echo

        while true; do
            read -p "Enter a different port for HPXPANEL (1-65535) or 'q' to abort: " new_port
            if [[ "$new_port" == "q" || "$new_port" == "Q" ]]; then
                colorized_echo red "Installation aborted by user."
                exit 1
            fi
            if ! [[ "$new_port" =~ ^[0-9]+$ ]] || [ "$new_port" -lt 1 ] || [ "$new_port" -gt 65535 ]; then
                colorized_echo red "Invalid port number. Please enter a value between 1 and 65535."
                continue
            fi
            if is_port_in_use "$new_port"; then
                colorized_echo red "Port ${new_port} is also in use. Please choose another port."
                continue
            fi
            break
        done

        set_or_uncomment_env_var "UVICORN_PORT" "$new_port" false "$ENV_FILE"
        colorized_echo green "UVICORN_PORT updated to ${new_port} in ${ENV_FILE}"

        # Update ALLOWED_ORIGINS to reflect the new port
        if grep -qE '^\s*ALLOWED_ORIGINS\s*=' "$ENV_FILE"; then
            sed -i "s|localhost:${configured_port}|localhost:${new_port}|g" "$ENV_FILE"
        fi
    fi

    up_hpxpanel

    echo
    colorized_echo blue "=============================="
    colorized_echo yellow "HPXPANEL doesn't have any core by default."
    colorized_echo yellow "You need at least one node for proxy connection."
    echo
    colorized_echo cyan "Want to install node on same server?"
    colorized_echo red "(Not recommended for commercial use)"
    echo
    read -p "Do you want to install HPXPANEL node? (y/n) " install_node_choice
    if [[ $install_node_choice =~ ^[Yy]$ ]]; then
        install_node_command
    else
        colorized_echo yellow "Skipping node installation."
    fi

    follow_hpxpanel_logs
}

down_hpxpanel() {
    compose_down
}

show_hpxpanel_logs() {
    compose_logs
}

follow_hpxpanel_logs() {
    compose_logs_follow
}

hpxpanel_cli() {
    local backend_service=""
    backend_service=$(detect_hpxpanel_backend_service)
    if [ -z "$backend_service" ]; then
        colorized_echo red "Could not detect HPXPANEL backend service in docker-compose."
        return 1
    fi
    # Engine binary name inside the image; CLI_PROG_NAME is what the user sees.
    $COMPOSE -f $COMPOSE_FILE -p "$APP_NAME" exec -e CLI_PROG_NAME="hpxpanel cli" "$backend_service" pasarguard-cli "$@"
}

hpxpanel_tui() {
    local backend_service=""
    backend_service=$(detect_hpxpanel_backend_service)
    if [ -z "$backend_service" ]; then
        colorized_echo red "Could not detect HPXPANEL backend service in docker-compose."
        return 1
    fi
    $COMPOSE -f $COMPOSE_FILE -p "$APP_NAME" exec -e TUI_PROG_NAME="hpxpanel tui" "$backend_service" pasarguard-tui "$@"
}


is_hpxpanel_up() {
    if [ -z "$($COMPOSE -f $COMPOSE_FILE ps -q -a)" ]; then
        return 1
    else
        return 0
    fi
}

uninstall_command() {
    check_running_as_root

    local assume_yes=0
    local purge_all=0
    while [ $# -gt 0 ]; do
        case "$1" in
        -y|--yes) assume_yes=1; shift ;;
        --purge|--all|purge) purge_all=1; shift ;;
        -h|--help)
            echo "Usage: hpxpanel uninstall [-y] [--purge]"
            echo "  -y, --yes     no confirmation prompts"
            echo "  --purge       also wipe DB volumes + data (needed for clean reinstall)"
            return 0
            ;;
        *) colorized_echo red "Unknown option: $1"; exit 1 ;;
        esac
    done

    if ! is_hpxpanel_installed && [ "$purge_all" -eq 0 ]; then
        colorized_echo red "HPXPANEL is not installed!"
        colorized_echo yellow "To wipe leftover DB volumes anyway:  hpxpanel purge -y"
        exit 1
    fi

    if [ "$assume_yes" -eq 0 ]; then
        read -p "Do you really want to uninstall HPXPANEL? (y/n) "
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            colorized_echo red "Aborted"
            exit 1
        fi
    fi

    if [ -f "$COMPOSE_FILE" ]; then
        detect_compose || true
        if is_hpxpanel_up 2>/dev/null; then
            down_hpxpanel
        else
            $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" down --remove-orphans >/dev/null 2>&1 || true
        fi
    else
        docker rm -f hpxpanel 2>/dev/null || true
        docker ps -aq --filter "name=hpxpanel" 2>/dev/null | while read -r id; do [ -n "$id" ] && docker rm -f "$id" 2>/dev/null || true; done
    fi

    uninstall_completion
    uninstall_hpxpanel_script
    uninstall_hpxpanel
    uninstall_hpxpanel_docker_images

    if [ "$purge_all" -eq 1 ]; then
        uninstall_hpxpanel_data_files
        purge_hpxpanel_database_volumes
        colorized_echo green "HPXPANEL purged completely (app + data + DB volumes)."
        colorized_echo green "Reinstall with:"
        colorized_echo cyan "  sudo bash -c \"\$(curl -fsSL https://github.com/pooyahpx/HPXPANEL/raw/main/scripts/hpxpanel.sh)\" @ install --database timescaledb"
        return 0
    fi

    if [ "$assume_yes" -eq 1 ]; then
        colorized_echo green "HPXPANEL uninstalled (data/DB volumes kept)."
        colorized_echo yellow "For a clean reinstall wipe DB too:  hpxpanel purge -y"
        return 0
    fi

    read -p "Remove data files too ($DATA_DIR)? (y/n) "
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        uninstall_hpxpanel_data_files
    fi
    read -p "Also wipe database volumes (Postgres/MySQL)? Required if you got InvalidPasswordError. (y/n) "
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        purge_hpxpanel_database_volumes
    fi
    colorized_echo green "HPXPANEL uninstalled successfully"
}

purge_command() {
    # Full clean removal for reinstall — no leftover DB password conflict.
    uninstall_command --purge "$@"
}

purge_hpxpanel_database_volumes() {
    local paths=(
        "/var/lib/postgresql/hpxpanel"
        "/var/lib/postgresql/pasarguard"
        "/var/lib/mysql/hpxpanel"
        "/var/lib/mysql/pasarguard"
    )
    local path=""
    local vol=""

    colorized_echo yellow "Wiping database volumes/directories..."

    # Stop anything that might hold the mounts.
    if [ -f "$COMPOSE_FILE" ]; then
        detect_compose 2>/dev/null || true
        $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" down -v --remove-orphans >/dev/null 2>&1 || true
    fi
    docker ps -aq --filter "name=hpxpanel" 2>/dev/null | while read -r id; do [ -n "$id" ] && docker rm -f "$id" 2>/dev/null || true; done
    docker ps -aq --filter "name=timescaledb" 2>/dev/null | while read -r id; do [ -n "$id" ] && docker rm -f "$id" 2>/dev/null || true; done
    docker ps -aq --filter "name=pgbouncer" 2>/dev/null | while read -r id; do [ -n "$id" ] && docker rm -f "$id" 2>/dev/null || true; done
    docker ps -aq --filter "name=pgadmin" 2>/dev/null | while read -r id; do [ -n "$id" ] && docker rm -f "$id" 2>/dev/null || true; done

    for path in "${paths[@]}"; do
        if [ -e "$path" ]; then
            if rm -rf "$path" 2>/dev/null; then
                colorized_echo green "Deleted: $path"
            else
                colorized_echo red "Failed to delete: $path"
            fi
        fi
    done

    if command -v docker >/dev/null 2>&1; then
        for vol in $(docker volume ls --format '{{.Name}}' 2>/dev/null | grep -E '^(hpxpanel_|pasarguard_)?(pgadmin)$' || true); do
            if docker volume rm "$vol" >/dev/null 2>&1; then
                colorized_echo green "Deleted Docker volume: $vol"
            fi
        done
    fi
}

uninstall_hpxpanel_script() {
    if [ -f "/usr/local/bin/hpxpanel" ]; then
        colorized_echo yellow "Removing HPXPANEL CLI"
        rm "/usr/local/bin/hpxpanel"
    fi
}

uninstall_hpxpanel() {
    if [ -d "$APP_DIR" ]; then
        colorized_echo yellow "Removing directory: $APP_DIR"
        rm -rf "$APP_DIR"
    fi
}

uninstall_hpxpanel_docker_images() {
    local images
    images=$(docker images --format '{{.Repository}} {{.ID}}' | awk '$1 ~ /^ghcr\.io\/pooyahpx\/hpxpanel(:|$)/ {print $2}' | sort -u)

    if [ -z "$images" ]; then
        colorized_echo yellow "ghcr.io/pooyahpx/hpxpanel images not found"
        return 0
    fi

    colorized_echo yellow "Checking ghcr.io/pooyahpx/hpxpanel images for removal..."

    for image in $images; do
        if docker ps -a --filter "ancestor=$image" -q | grep -q .; then
		    local container
            container=$(docker ps -a --filter "ancestor=$image" --format '{{.Names}}' | tr '\n' ' ')
            colorized_echo yellow "Skipping image $image (still used by: $container)"
            continue
        fi

        if docker rmi "$image" >/dev/null 2>&1; then
            colorized_echo yellow "Image $image removed"
        else
            colorized_echo yellow "Failed to remove image $image"
        fi
    done
}

uninstall_hpxpanel_data_files() {
    if [ -d "$DATA_DIR" ]; then
        colorized_echo yellow "Removing directory: $DATA_DIR"
        rm -rf "$DATA_DIR"
    fi
}

restart_command() {
    help() {
        colorized_echo red "Usage: hpxpanel restart [options]"
        echo
        echo "OPTIONS:"
        echo "  -h, --help        display this help message"
        echo "  -n, --no-logs     do not follow logs after starting"
    }

    local no_logs=false
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
        -n | --no-logs)
            no_logs=true
            ;;
        -h | --help)
            help
            exit 0
            ;;
        *)
            echo "Error: Invalid option: $1" >&2
            help
            exit 0
            ;;
        esac
        shift
    done

    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    down_hpxpanel
    up_hpxpanel
    if [ "$no_logs" = false ]; then
        follow_hpxpanel_logs
    fi
    colorized_echo green "HPXPANEL successfully restarted!"
}
logs_command() {
    help() {
        colorized_echo red "Usage: hpxpanel logs [options]"
        echo ""
        echo "OPTIONS:"
        echo "  -h, --help        display this help message"
        echo "  -n, --no-follow   do not show follow logs"
    }

    local no_follow=false
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
        -n | --no-follow)
            no_follow=true
            ;;
        -h | --help)
            help
            exit 0
            ;;
        *)
            echo "Error: Invalid option: $1" >&2
            help
            exit 0
            ;;
        esac
        shift
    done

    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    if ! is_hpxpanel_up; then
        colorized_echo red "HPXPANEL is not up."
        exit 1
    fi

    if [ "$no_follow" = true ]; then
        show_hpxpanel_logs
    else
        follow_hpxpanel_logs
    fi
}

down_command() {

    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    if ! is_hpxpanel_up; then
        colorized_echo red "HPXPANEL is already down"
        exit 1
    fi

    down_hpxpanel
}

cli_command() {
    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    if ! is_hpxpanel_up; then
        colorized_echo red "HPXPANEL is not up."
        exit 1
    fi

    hpxpanel_cli "$@"
}

tui_command() {
    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    if ! is_hpxpanel_up; then
        colorized_echo red "HPXPANEL is not up."
        exit 1
    fi

    hpxpanel_tui "$@"
}

up_command() {
    help() {
        colorized_echo red "Usage: hpxpanel up [options]"
        echo ""
        echo "OPTIONS:"
        echo "  -h, --help        display this help message"
        echo "  -n, --no-logs     do not follow logs after starting"
    }

    local no_logs=false
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
        -n | --no-logs)
            no_logs=true
            ;;
        -h | --help)
            help
            exit 0
            ;;
        *)
            echo "Error: Invalid option: $1" >&2
            help
            exit 0
            ;;
        esac
        shift
    done

    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    if is_hpxpanel_up; then
        colorized_echo red "HPXPANEL is already up"
        exit 1
    fi

    up_hpxpanel
    if [ "$no_logs" = false ]; then
        follow_hpxpanel_logs
    fi
}

update_command() {
    check_running_as_root
    # Check if hpxpanel is installed
    if ! is_hpxpanel_installed; then
        colorized_echo red "HPXPANEL is not installed!"
        exit 1
    fi

    detect_compose

    update_hpxpanel_script
    uninstall_completion
    install_completion
    colorized_echo blue "Pulling latest version"
    update_hpxpanel

    colorized_echo blue "Restarting HPXPANEL services"
    down_hpxpanel
    up_hpxpanel

    colorized_echo blue "HPXPANEL updated successfully"
}

update_hpxpanel_script() {
    FETCH_REPO="pooyahpx/HPXPANEL"
    colorized_echo blue "Updating HPXPANEL CLI"

    local backup_dir
    backup_dir=$(backup_scripts)

    if ! install_shared_libs_from_repo "$FETCH_REPO" common.sh system.sh docker.sh github.sh env.sh hpxpanel-backup.sh hpxpanel-restore.sh; then
        colorized_echo red "Failed to update shared libraries. Restoring from backup..."
        restore_scripts "$backup_dir"
        cleanup_backup "$backup_dir"
        exit 1
    fi

    if ! github_install_script_from_repo "$FETCH_REPO" "scripts/hpxpanel.sh" "hpxpanel"; then
        colorized_echo red "Failed to update HPXPANEL CLI. Restoring from backup..."
        restore_scripts "$backup_dir"
        cleanup_backup "$backup_dir"
        exit 1
    fi

    cleanup_backup "$backup_dir"
    colorized_echo green "HPXPANEL CLI updated successfully"
}

update_hpxpanel() {
    $COMPOSE -f $COMPOSE_FILE -p "$APP_NAME" pull
}

edit_command() {
    detect_os
    check_editor
    if [ -f "$COMPOSE_FILE" ]; then
        $EDITOR "$COMPOSE_FILE"
    else
        colorized_echo red "Compose file not found at $COMPOSE_FILE"
        exit 1
    fi
}

edit_env_command() {
    detect_os
    check_editor
    if [ -f "$ENV_FILE" ]; then
        $EDITOR "$ENV_FILE"
    else
        colorized_echo red "Environment file not found at $ENV_FILE"
        exit 1
    fi
}

install_node_command() {
    colorized_echo blue "=============================="
    colorized_echo magenta "   Install HPXPANEL Node   "
    colorized_echo blue "=============================="
    echo

    if [ "$(id -u)" = "0" ]; then
        colorized_echo blue "Running node installation as root..."
        bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install -y
    else
        colorized_echo blue "Running node installation with sudo..."
        sudo bash -c "$(curl -fsSL https://github.com/pooyahpx/HPXNODE/raw/main/scripts/install.sh)" @ install -y
    fi

    if [ $? -eq 0 ]; then
        colorized_echo green "Node installation completed successfully!"
    else
        colorized_echo red "Node installation failed."
        exit 1
    fi
}

generate_completion() {
    cat <<'EOF'
_hpxpanel_completions()
{
    local cur cmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    cmds="up down restart status logs cli tui install update uninstall purge install-script install-node ssl backup backup-service restore core-update edit edit-env help completion"
    COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )
    return 0
}
EOF
    echo "complete -F _hpxpanel_completions hpxpanel"
    echo "complete -F _hpxpanel_completions $APP_NAME"
}

install_completion() {
    local completion_dir="/etc/bash_completion.d"
    local completion_file="$completion_dir/$APP_NAME"
    mkdir -p "$completion_dir"
    generate_completion >"$completion_file"
    chmod 644 "$completion_file"
    colorized_echo green "Bash completion installed to $completion_file"
}

uninstall_completion() {
    local completion_dir="/etc/bash_completion.d"
    local completion_file="$completion_dir/$APP_NAME"
    if [ -f "$completion_file" ]; then
        rm "$completion_file"
        colorized_echo yellow "Bash completion removed from $completion_file"
    fi
}

usage() {
    local script_name="${0##*/}"
    colorized_echo blue "=============================="
    colorized_echo magenta "           HPXPANEL Help"
    colorized_echo blue "=============================="
    colorized_echo cyan "Usage:"
    echo "  ${script_name} [command]"
    echo

    colorized_echo cyan "Commands:"
    colorized_echo yellow "  up              $(tput sgr0)– Start services"
    colorized_echo yellow "  down            $(tput sgr0)– Stop services"
    colorized_echo yellow "  restart         $(tput sgr0)– Restart services"
    colorized_echo yellow "  status          $(tput sgr0)– Show status"
    colorized_echo yellow "  logs            $(tput sgr0)– Show logs"
    colorized_echo yellow "  cli             $(tput sgr0)– HPXPANEL CLI"
    colorized_echo yellow "  tui             $(tput sgr0)– HPXPANEL TUI"
    colorized_echo yellow "  install         $(tput sgr0)– Install HPXPANEL"
    colorized_echo yellow "  update          $(tput sgr0)– Update to latest version"
    colorized_echo yellow "  uninstall       $(tput sgr0)– Uninstall HPXPANEL"
    colorized_echo yellow "  purge           $(tput sgr0)– Full wipe (app+data+DB) for clean reinstall"
    colorized_echo yellow "  install-script  $(tput sgr0)– Install HPXPANEL script"
    colorized_echo yellow "  install-node    $(tput sgr0)– Install HPXPANEL node"
    colorized_echo yellow "  ssl             $(tput sgr0)– Issue / reconfigure Let's Encrypt SSL"
    colorized_echo yellow "  backup          $(tput sgr0)– Manual backup launch"
    colorized_echo yellow "  backup-service  $(tput sgr0)– hpxpanel Backup service to backup to TG, and a new job in crontab"
    colorized_echo yellow "  restore         $(tput sgr0)– Restore database from backup file"
    colorized_echo yellow "  edit            $(tput sgr0)– Edit docker-compose.yml (via nano or vi editor)"
    colorized_echo yellow "  edit-env        $(tput sgr0)– Edit environment file (via nano or vi editor)"
    colorized_echo yellow "  help            $(tput sgr0)– Show this help message"

    echo
    colorized_echo cyan "Directories:"
    colorized_echo magenta "  App directory: $APP_DIR"
    colorized_echo magenta "  Data directory: $DATA_DIR"
    colorized_echo blue "================================"
    echo
}

hpxpanel_main() {
    case "$1" in
    up)
        shift
        up_command "$@"
        ;;
    down)
        shift
        down_command "$@"
        ;;
    restart)
        shift
        restart_command "$@"
        ;;
    status)
        shift
        status_command "$@"
        ;;
    logs)
        shift
        logs_command "$@"
        ;;
    cli)
        shift
        cli_command "$@"
        ;;
    tui)
        shift
        tui_command "$@"
        ;;
    backup)
        shift
        backup_command "$@"
        ;;
    backup-service)
        shift
        backup_service "$@"
        ;;
    restore)
        shift
        restore_command "$@"
        ;;
    install)
        shift
        install_command "$@"
        ;;
    update)
        shift
        update_command "$@"
        ;;
    uninstall)
        shift
        uninstall_command "$@"
        ;;
    purge)
        shift
        purge_command "$@"
        ;;
    install-script)
        shift
        install_hpxpanel_script "$@"
        ;;
    install-node)
        shift
        install_node_command "$@"
        ;;
    ssl|cert)
        shift
        ssl_command "$@"
        ;;
    edit)
        shift
        edit_command "$@"
        ;;
    edit-env)
        shift
        edit_env_command "$@"
        ;;
    completion)
        check_running_as_root
        install_completion
        colorized_echo cyan ""
        colorized_echo yellow "To activate completion in this session, run:"
        colorized_echo cyan "  source /etc/bash_completion.d/$APP_NAME"
        colorized_echo yellow "Or simply restart your terminal."
        ;;
    help | *)
        usage
        ;;
    esac
}

if [ "${PASARGUARD_SOURCE_ONLY:-false}" != "true" ]; then
    hpxpanel_main "$@"
fi
