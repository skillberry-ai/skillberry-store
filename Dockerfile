ARG BASE_IMAGE_FULL_NAME=skillberry-base
ARG BASE_IMAGE_TAG=latest

###########################################
# Build Stage - Contains SSH key temporarily
###########################################
FROM ${BASE_IMAGE_FULL_NAME}:${BASE_IMAGE_TAG} AS builder

# Define build arguments
ARG BUILD_VERSION=latest
ARG BUILD_DATE
ARG SERVICE_NAME
ARG SERVICE_PORTS
ARG SERVICE_ENTRY_MODULE
# Optional dependency group to install (see pyproject [project.optional-dependencies]).
# Defaults to "plugins-all" so the image ships every bundled plugin; pass an empty
# value (--build-arg PLUGIN_EXTRAS=) to build a slim, core-only image.
ARG PLUGIN_EXTRAS=plugins-all

# Promote the BUILD_VERSION arg into an env var so `make` (invoked below) sees
# the host-computed version. Combined with DEPLOY_ONLY=TRUE, this makes the
# makefile's `BUILD_VERSION ?=` respect the passed-in value instead of trying
# to re-derive it from git inside the container (.git is not shipped into the
# build context; see .dockerignore).
ENV BUILD_VERSION=$BUILD_VERSION \
    DEPLOY_ONLY=TRUE

# Python, NodeJS and venv are already set in the base image
# WORKDIR is already set in the base image to /app

# Copy the application
COPY . .

# Uncomment this to test your SSH cconnection to github.ibm.com
# RUN --mount=type=ssh \
#     echo "SSH_AUTH_SOCK=$SSH_AUTH_SOCK" && \
#     ls -l "$SSH_AUTH_SOCK" || true && \
#     ssh -V && git --version && \
#     ssh -o StrictHostKeyChecking=accept-new -T git@github.ibm.com || true

# Install dependencies (requires SSH key for git+ssh)
RUN --mount=type=ssh make install-requirements ODEPS=${PLUGIN_EXTRAS}

# Build the UI static bundle so the runtime image ships it prebuilt (the
# runtime stage sets DEPLOY_ONLY=TRUE, which drops ui-build from `make run`).
RUN make ui-build

###########################################
# Runtime Stage - Clean, no SSH key
###########################################
FROM ${BASE_IMAGE_FULL_NAME}:${BASE_IMAGE_TAG}

# Define build arguments for runtime stage
ARG BUILD_VERSION=latest
ARG BUILD_DATE
ARG SERVICE_NAME
ARG SERVICE_PORTS
ARG SERVICE_ENTRY_MODULE
# Must match the builder-stage value so the runtime stamp lookup
# (.stamps/install-requirements-$(ODEPS)) resolves to the file created at build.
ARG PLUGIN_EXTRAS=plugins-all

# Label the image with metadata
LABEL version="$BUILD_VERSION" \
      date="$BUILD_DATE"

# Persist into the image runtime environment.
# APP_HOME, and the *_CACHE_DIR vars point at group-writable paths so an
# arbitrary OpenShift UID (whose HOME defaults to /) can still write caches.
ENV BUILD_VERSION=$BUILD_VERSION \
    BUILD_DATE=$BUILD_DATE \
    SERVICE_NAME=$SERVICE_NAME \
    SERVICE_PORTS=$SERVICE_PORTS \
    SERVICE_ENTRY_MODULE=$SERVICE_ENTRY_MODULE \
    ODEPS=$PLUGIN_EXTRAS \
    DEPLOY_ONLY=TRUE \
    APP_HOME=/app \
    APP_DATA_DIR=/tmp/skillberry-store \
    HOME=/app \
    XDG_CACHE_HOME=/tmp/.cache \
    UV_CACHE_DIR=/tmp/.cache/uv \
    PIP_CACHE_DIR=/tmp/.cache/pip \
    USER=default \
    LOGNAME=default

# Cap glibc's per-thread malloc arenas (default 8 x ncpu, so 160 on a 20-core
# host). uvicorn runs every `def` endpoint on an anyio threadpool, so the
# process spreads its allocations across many arenas within seconds of startup;
# capping at 2 trims the per-arena free-list and fragmentation overhead.
#
# Worth ~12 MiB of RSS, measured over 3 alternating container runs (527.6 ->
# 515.9 MiB mean; Python-process RSS 447.6 -> 435.6 MiB, all three pairs
# improving with non-overlapping ranges). Note this is far less than the
# 50-150 MB sometimes claimed for this knob: the usual rationale is that each
# arena's 64 MB reservation is charged to RSS, but those reservations are
# PROT_NONE address space (VSZ) and only touched pages become resident.
# We are not allocator-bound, so the throughput cost is nil.
ENV MALLOC_ARENA_MAX=2

# Python, NodeJS and venv are already set in the base image
# WORKDIR is already set in the base image to /app

# Copy entire /app directory from builder stage
# This includes the application code and the .venv with all installed dependencies
COPY --from=builder $APP_HOME $APP_HOME

# OpenShift compliance:
#  - safe.directory '*' lets git operate under any UID (the image is immutable,
#    so the CVE-2022-24765 threat model does not apply).
#  - gid 0 + `chmod g=u` on runtime-writable paths lets the arbitrary UID that
#    OpenShift assigns (always in gid 0) read/write everything the app needs.
#    Harmless on plain Docker/k8s: group perms equal user perms.
RUN git config --system --add safe.directory '*' \
    && mkdir -p "$UV_CACHE_DIR" "$PIP_CACHE_DIR" "$APP_DATA_DIR" \
    && chgrp -R 0 "$APP_HOME" "$XDG_CACHE_HOME" "$APP_DATA_DIR" \
    && chmod -R g=u "$APP_HOME" "$XDG_CACHE_HOME" "$APP_DATA_DIR"

# Expose all service ports
EXPOSE $SERVICE_PORTS

# Run as a non-root numeric UID so plain-k8s PodSecurityStandards `restricted`
# accepts the pod. OpenShift will override this with a random UID from its
# project range; the gid-0 + g=u permissions above make either case work.
USER 1001

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD ["sh", "-c", "make run"]
