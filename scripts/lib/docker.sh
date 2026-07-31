#!/usr/bin/env bash

install_docker() {
    colorized_echo blue "Installing Docker"
    if ! bash -o pipefail -c 'curl -fsSL https://get.docker.com | sh'; then
        die "Failed to install Docker"
    fi
    ensure_docker_service_running
    colorized_echo green "Docker installed successfully"
}

ensure_docker_service_running() {
    if ! command -v systemctl >/dev/null 2>&1; then
        return
    fi

    if [ ! -d /run/systemd/system ]; then
        return
    fi

    if ! systemctl list-unit-files docker.service >/dev/null 2>&1; then
        return
    fi

    if systemctl is-active --quiet docker; then
        return
    fi

    colorized_echo blue "Starting Docker service"
    if ! systemctl enable --now docker >/dev/null 2>&1; then
        systemctl start docker >/dev/null 2>&1 || die "Failed to start Docker service"
    fi
}

detect_compose() {
    if docker compose version >/dev/null 2>&1; then
        COMPOSE='docker compose'
    else
        die "docker compose v2 not found. Install the Docker Compose v2 plugin (e.g. 'apt-get install docker-compose-plugin' or 'docker-compose-v2'), then re-run."
    fi
}

# Ensure the Docker Compose v2 plugin is available. A bare 'command -v docker'
# check is not enough: a machine can have the docker engine (e.g. the distro
# docker.io package) without the compose v2 plugin. Installs the plugin via the
# package manager when missing -- the package is named docker-compose-plugin in
# Docker's official repo and docker-compose-v2 in Debian/Ubuntu's -- and aborts
# with actionable guidance if it still cannot be provided.
ensure_docker_compose() {
    if docker compose version >/dev/null 2>&1; then
        return 0
    fi
    colorized_echo blue "Docker Compose v2 plugin not found; installing it"
    try_install_package docker-compose-plugin || try_install_package docker-compose-v2 || true
    if ! docker compose version >/dev/null 2>&1; then
        die "docker compose v2 is required but could not be installed automatically. Install the Docker Compose v2 plugin (e.g. 'apt-get install docker-compose-plugin' or 'docker-compose-v2'), then re-run."
    fi
    colorized_echo green "Docker Compose v2 plugin installed"
}

compose_up() {
    ensure_docker_service_running
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" up -d --remove-orphans
}

compose_down() {
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" down
}

compose_logs() {
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" logs
}

compose_logs_follow() {
    $COMPOSE -f "$COMPOSE_FILE" -p "$APP_NAME" logs -f
}
