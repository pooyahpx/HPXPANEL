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

detect_and_update_package_manager() {
    if [ -z "${OS:-}" ]; then
        detect_os
    fi

    colorized_echo blue "Updating package manager"

    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        PKG_MANAGER="apt-get"
        $PKG_MANAGER update -qq >/dev/null 2>&1 || warn_package_metadata_refresh_failed
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

    if [ -z "${OS:-}" ]; then
        detect_os
    fi

    if [ -z "${PKG_MANAGER:-}" ]; then
        detect_and_update_package_manager
    fi

    colorized_echo blue "Installing $package"
    if [[ "$OS" == "Ubuntu"* ]] || [[ "$OS" == "Debian"* ]]; then
        $PKG_MANAGER -y -qq install "$package" >/dev/null 2>&1
    elif is_redhat_family_os; then
        $PKG_MANAGER install -y -q "$package" >/dev/null 2>&1
    elif [[ "$OS" == "Fedora"* ]]; then
        $PKG_MANAGER install -y -q "$package" >/dev/null 2>&1
    elif [[ "$OS" == "Arch Linux" ]] || [[ "$OS" == "Arch"* ]]; then
        $PKG_MANAGER -S --noconfirm --quiet "$package" >/dev/null 2>&1
    elif [[ "$OS" == "openSUSE"* ]]; then
        $PKG_MANAGER --quiet install -y "$package" >/dev/null 2>&1
    else
        die "Unsupported operating system"
    fi
}

install_package() {
    try_install_package "$1" || die "Failed to install $1 with ${PKG_MANAGER:-the package manager}. Check your package repositories and try again."
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
