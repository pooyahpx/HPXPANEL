#!/usr/bin/env bash

check_running_as_root() {
    if [ "$(id -u)" != "0" ]; then
        die "This command must be run as root."
    fi
}

detect_os() {
    if [ -f /etc/lsb-release ] && command -v lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
    elif [ -f /etc/os-release ]; then
        OS=$(awk -F= '/^NAME/{print $2}' /etc/os-release | tr -d '"')
    elif [ -f /etc/redhat-release ]; then
        OS=$(awk '{print $1}' /etc/redhat-release)
    elif [ -f /etc/arch-release ]; then
        OS="Arch Linux"
    else
        die "Unsupported operating system"
    fi
}

is_redhat_family_os() {
    [[ "${OS:-}" == "CentOS"* ]] ||
        [[ "${OS:-}" == "AlmaLinux"* ]] ||
        [[ "${OS:-}" == "Rocky"* ]] ||
        [[ "${OS:-}" == "Red Hat"* ]] ||
        [[ "${OS:-}" == "Oracle Linux"* ]] ||
        [[ "${OS:-}" == "Amazon Linux"* ]]
}

select_redhat_package_manager() {
    if command -v dnf >/dev/null 2>&1; then
        PKG_MANAGER="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MANAGER="yum"
    else
        die "Neither yum nor dnf was found. Please install packages manually."
    fi
}

enable_epel_if_available() {
    if $PKG_MANAGER install -y -q epel-release >/dev/null 2>&1; then
        return
    fi

    colorized_echo yellow "Could not enable EPEL automatically; continuing with configured repositories."
}

warn_package_metadata_refresh_failed() {
    colorized_echo yellow "Could not refresh package metadata; continuing with configured repositories."
}

is_debian_family_os() {
    [[ "${OS:-}" == "Ubuntu"* ]] || [[ "${OS:-}" == "Debian"* ]]
}

debian_apt_options() {
    echo "-o" "DPkg::Lock::Timeout=120"
}

debian_repair_apt() {
    local apt_opts
    apt_opts="$(debian_apt_options)"
    # shellcheck disable=SC2086
    DEBIAN_FRONTEND=noninteractive apt-get $apt_opts update -y >/dev/null 2>&1 || true
    # shellcheck disable=SC2086
    DEBIAN_FRONTEND=noninteractive dpkg --configure -a >/dev/null 2>&1 || true
    # shellcheck disable=SC2086
    DEBIAN_FRONTEND=noninteractive apt-get $apt_opts -y --fix-broken install >/dev/null 2>&1 || true
}

show_package_install_log() {
    local log="$1"
    [ -n "$log" ] && [ -f "$log" ] || return 0
    colorized_echo yellow "Package manager output:"
    tail -n 25 "$log"
    rm -f "$log"
}

run_debian_package_install() {
    local package="$1"
    local log="$2"
    local apt_opts
    apt_opts="$(debian_apt_options)"
    # shellcheck disable=SC2086
    DEBIAN_FRONTEND=noninteractive apt-get $apt_opts -y install "$package" >"$log" 2>&1
}

detect_and_update_package_manager() {
    if [ -z "${OS:-}" ]; then
        detect_os
    fi

    colorized_echo blue "Updating package manager"

    if is_debian_family_os; then
        PKG_MANAGER="apt-get"
        local apt_opts
        apt_opts="$(debian_apt_options)"
        # shellcheck disable=SC2086
        DEBIAN_FRONTEND=noninteractive $PKG_MANAGER $apt_opts update -y >/dev/null 2>&1 || warn_package_metadata_refresh_failed
    elif is_redhat_family_os; then
        select_redhat_package_manager
        $PKG_MANAGER -y -q makecache >/dev/null 2>&1 || warn_package_metadata_refresh_failed
        enable_epel_if_available
    elif [[ "$OS" == "Fedora"* ]]; then
        PKG_MANAGER="dnf"
        $PKG_MANAGER -q -y makecache >/dev/null 2>&1 || warn_package_metadata_refresh_failed
    elif [[ "$OS" == "Arch Linux" ]] || [[ "$OS" == "Arch"* ]]; then
        PKG_MANAGER="pacman"
        $PKG_MANAGER -Sy --noconfirm --quiet >/dev/null 2>&1 || warn_package_metadata_refresh_failed
    elif [[ "$OS" == "openSUSE"* ]]; then
        PKG_MANAGER="zypper"
        $PKG_MANAGER refresh --quiet >/dev/null 2>&1 || warn_package_metadata_refresh_failed
    else
        die "Unsupported operating system"
    fi
}

# Attempt to install a package, returning non-zero on failure instead of
# aborting. Use this when the caller wants to handle a failed install itself
# (e.g. fall back to an alternative package name); most callers want
# install_package, which aborts on failure.
try_install_package() {
    local package="$1"
    local install_log=""

    if [ -z "${OS:-}" ]; then
        detect_os
    fi

    if [ -z "${PKG_MANAGER:-}" ]; then
        detect_and_update_package_manager
    fi

    colorized_echo blue "Installing $package"
    install_log="$(mktemp /tmp/hpxpanel-pkg.XXXXXX 2>/dev/null || mktemp)"

    local status=1
    if is_debian_family_os; then
        if run_debian_package_install "$package" "$install_log"; then
            rm -f "$install_log"
            return 0
        fi
        colorized_echo yellow "Retrying $package after apt repair..."
        debian_repair_apt
        if run_debian_package_install "$package" "$install_log"; then
            rm -f "$install_log"
            return 0
        fi
        show_package_install_log "$install_log"
        return 1
    elif is_redhat_family_os; then
        $PKG_MANAGER install -y -q "$package" >"$install_log" 2>&1
        status=$?
    elif [[ "$OS" == "Fedora"* ]]; then
        $PKG_MANAGER install -y -q "$package" >"$install_log" 2>&1
        status=$?
    elif [[ "$OS" == "Arch Linux" ]] || [[ "$OS" == "Arch"* ]]; then
        $PKG_MANAGER -S --noconfirm --quiet "$package" >"$install_log" 2>&1
        status=$?
    elif [[ "$OS" == "openSUSE"* ]]; then
        $PKG_MANAGER --quiet install -y "$package" >"$install_log" 2>&1
        status=$?
    else
        rm -f "$install_log"
        die "Unsupported operating system"
    fi

    if [ "$status" -eq 0 ]; then
        rm -f "$install_log"
        return 0
    fi

    show_package_install_log "$install_log"
    return 1
}

install_package() {
    local package="$1"
    try_install_package "$package" || {
        if is_debian_family_os; then
            die "Failed to install $package with apt-get. Try: apt-get update && apt-get install -y $package"
        fi
        die "Failed to install $package with ${PKG_MANAGER:-the package manager}. Check your package repositories and try again."
    }
}

install_dns_utils_package() {
    if [ -z "${OS:-}" ]; then
        detect_os
    fi

    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        install_package dnsutils
    elif is_redhat_family_os || [[ "$OS" == "Fedora"* ]]; then
        install_package bind-utils
    elif [[ "$OS" == "Arch Linux" ]] || [[ "$OS" == "Arch"* ]]; then
        install_package bind-tools
    elif [[ "$OS" == "openSUSE"* ]]; then
        install_package bind-utils
    else
        colorized_echo yellow "Could not install DNS tools automatically on this OS."
        return 1
    fi
}

check_editor() {
    if [ -z "${EDITOR:-}" ]; then
        if command -v nano >/dev/null 2>&1; then
            EDITOR="nano"
        elif command -v vi >/dev/null 2>&1; then
            EDITOR="vi"
        else
            detect_os
            install_package nano
            EDITOR="nano"
        fi
    fi
}

identify_the_operating_system_and_architecture() {
    if [[ "$(uname)" != "Linux" ]]; then
        die "error: This operating system is not supported."
    fi

    case "$(uname -m)" in
    i386 | i686)
        ARCH='32'
        ;;
    amd64 | x86_64)
        ARCH='64'
        ;;
    armv5tel)
        ARCH='arm32-v5'
        ;;
    armv6l)
        ARCH='arm32-v6'
        grep Features /proc/cpuinfo | grep -qw 'vfp' || ARCH='arm32-v5'
        ;;
    armv7 | armv7l)
        ARCH='arm32-v7a'
        grep Features /proc/cpuinfo | grep -qw 'vfp' || ARCH='arm32-v5'
        ;;
    armv8 | aarch64)
        ARCH='arm64-v8a'
        ;;
    mips)
        ARCH='mips32'
        ;;
    mipsle)
        ARCH='mips32le'
        ;;
    mips64)
        ARCH='mips64'
        lscpu | grep -q "Little Endian" && ARCH='mips64le'
        ;;
    mips64le)
        ARCH='mips64le'
        ;;
    ppc64)
        ARCH='ppc64'
        ;;
    ppc64le)
        ARCH='ppc64le'
        ;;
    riscv64)
        ARCH='riscv64'
        ;;
    s390x)
        ARCH='s390x'
        ;;
    *)
        die "error: The architecture is not supported."
        ;;
    esac
}

install_yq() {
    local base_url="https://github.com/mikefarah/yq/releases/latest/download"
    local yq_binary=""
    local yq_url=""
    local binary_tmp=""

    if command -v yq >/dev/null 2>&1; then
        colorized_echo green "yq is already installed."
        return
    fi

    identify_the_operating_system_and_architecture

    case "$ARCH" in
    64 | x86_64)
        yq_binary="yq_linux_amd64"
        ;;
    arm32-v7a | arm32-v6 | arm32-v5 | armv7l)
        yq_binary="yq_linux_arm"
        ;;
    arm64-v8a | aarch64)
        yq_binary="yq_linux_arm64"
        ;;
    32 | i386 | i686)
        yq_binary="yq_linux_386"
        ;;
    *)
        die "Unsupported architecture: $ARCH"
        ;;
    esac

    yq_url="${base_url}/${yq_binary}"
    colorized_echo blue "Downloading yq from ${yq_url}..."

    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        colorized_echo yellow "Neither curl nor wget is installed. Attempting to install curl."
        install_package curl || die "Failed to install curl. Please install curl or wget manually."
    fi

    binary_tmp=$(create_temp_file "yq" ".bin")

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$yq_url" -o "$binary_tmp" || die "Failed to download yq using curl. Please check your internet connection."
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$binary_tmp" "$yq_url" || die "Failed to download yq using wget. Please check your internet connection."
    fi

    install -m 755 "$binary_tmp" /usr/local/bin/yq
    colorized_echo green "yq installed successfully!"

    if ! echo "$PATH" | grep -q "/usr/local/bin"; then
        export PATH="/usr/local/bin:$PATH"
    fi

    rm -f "$binary_tmp"
}
