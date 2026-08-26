ARG PYTHON_VERSION=3.14

FROM ghcr.io/astral-sh/uv:python$PYTHON_VERSION-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /build
# Lockfile references a path dependency under vendor/ — mount it for the first sync.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=vendor,target=vendor \
    uv sync --frozen --no-install-project --no-dev
ADD . /build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:$PYTHON_VERSION-slim-bookworm

COPY --from=builder /build /code
WORKDIR /code

ENV PATH="/code/.venv/bin:$PATH"

# curl: healthchecks · docker CLI: spawn FOREIGN tunnel containers via host socket
# iproute2/iptables/ping: manage TAP iface + health when network_mode=host
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    iproute2 \
    iptables \
    iputils-ping \
    && DOCKER_ARCH="$TARGETARCH" \
    && if [ "$DOCKER_ARCH" = "amd64" ] || [ -z "$DOCKER_ARCH" ]; then DOCKER_ARCH=x86_64; fi \
    && if [ "$DOCKER_ARCH" = "arm64" ]; then DOCKER_ARCH=aarch64; fi \
    && curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-27.5.1.tgz" \
      | tar -xz -C /tmp \
    && mv /tmp/docker/docker /usr/local/bin/docker \
    && rm -rf /tmp/docker \
    && rm -rf /var/lib/apt/lists/*

COPY cli_wrapper.sh /usr/bin/hpxpanel-cli
RUN chmod +x /usr/bin/hpxpanel-cli

COPY tui_wrapper.sh /usr/bin/hpxpanel-tui
RUN chmod +x /usr/bin/hpxpanel-tui

# Copy healthcheck script
COPY healthcheck.sh /code/healthcheck.sh
RUN chmod +x /code/healthcheck.sh

RUN chmod +x /code/start.sh

ENTRYPOINT ["/code/start.sh"]
