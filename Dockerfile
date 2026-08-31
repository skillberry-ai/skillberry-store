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
#
# Defaults to empty: the image ships the core service only. Plugins are
# auto-loaded through entry points at startup (plugins/loader.py), so every
# installed plugin's top-level module is imported and its metadata object is
# retained for the life of the process -- even when the admin toggles the
# plugin "off". Bundling all 16 by default made every deployment pay for all
# of them.
#
# Build the all-plugins variant with `make docker-build-full`, or pick a subset
# with `--build-arg PLUGIN_EXTRAS=plugin-creator,plugin-dedupe`. See
# docs/plugins-installation.md.
ARG PLUGIN_EXTRAS=

# Promote the BUILD_VERSION arg into an env var so `make` (invoked below) sees
# the host-computed version. Combined with DEPLOY_ONLY=TRUE, this makes the
# makefile's `BUILD_VERSION ?=` respect the passed-in value instead of trying
# to re-derive it from git inside the container (.git is not shipped into the
# build context; see .dockerignore).
# APP_HOME mirrors the runtime stage: the base image only sets WORKDIR, so
# without this the $APP_HOME references below would expand to empty.
ENV BUILD_VERSION=$BUILD_VERSION \
    DEPLOY_ONLY=TRUE \
    APP_HOME=/app

# Python, NodeJS and venv are already set in the base image
# WORKDIR is already set in the base image to /app

# Copy the application
COPY . .

# Unpack the extra host content staged into the build context by
# scripts/stage-extra-copy.sh (make docker-build EXTRA_COPY_FILES=<src>:<dst>,...).
# The staged tree mirrors the absolute target paths, so one recursive unpack
# into "/" lands every entry at its target.
#
# tar --no-overwrite-dir, and not "cp -a", because the mirror necessarily
# carries a folder for every component of every target path, and cp applies
# the mirror folder's mode to the pre-existing folder it lands on -- resetting
# /tmp from 1777 to 755, for one. tar leaves existing folders' metadata alone
# and still applies the archived mode to the content itself and to folders it
# creates.
#
# This must precede every build step that reads the copied tree: the staged
# files are real build inputs. `make ui-build` below bakes the ACL mode from
# access_control_config.yaml into the UI bundle, so unpacking only in the
# runtime stage shipped a bundle built against the repo's config while the
# image ran with the operator's — a UI stuck in the wrong auth mode.
#
# This is the only unpack. Afterwards the staging tree is moved out of
# $APP_HOME (so it does not ride along with the $APP_HOME copy in the runtime
# stage) and its $APP_HOME mirror is pruned, leaving exactly the targets that
# $APP_HOME cannot carry across the stage boundary. That split matters: paths
# under $APP_HOME travel in whatever state the build left them, instead of
# being reverted to the staged original by a second application. mkdir -p
# keeps the recipe unconditional when EXTRA_COPY_FILES is unset.
RUN mkdir -p "$APP_HOME/.extra-copy" \
    && tar -cf - -C "$APP_HOME/.extra-copy" . | tar -xf - --no-overwrite-dir -C / \
    && mv "$APP_HOME/.extra-copy" /extra-copy \
    && rm -rf "/extra-copy$APP_HOME"

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

# Pre-seed the ~80 MB ONNX encoder weights so the runtime image can start
# without reaching HuggingFace at all.
#
# fastembed ignores HF_HOME / TRANSFORMERS_CACHE / XDG_CACHE_HOME and caches into
# its own temp directory, so an unseeded image paid an ~11.5 s download on the
# *readiness* critical path (/health/ready gates on encoder_warmup) and paid it
# again on every pod restart where that temp dir is an ephemeral emptyDir — and
# never started at all in an air-gapped deployment. encoder_cache_dir() resolves
# to $APP_HOME/.cache/fastembed here, which rides along with the
# `COPY --from=builder $APP_HOME $APP_HOME` below and picks up the same
# `chgrp 0` / `chmod g=u` treatment, so the arbitrary UID OpenShift assigns can
# read it.
#
# Best-effort: an image built without egress to HuggingFace is still usable, it
# just falls back to downloading at first embed like before. The warning names
# the consequence so a silent miss is not mistaken for a seeded cache.
RUN python -c "\
from skillberry_store.vdbs.vector_db_interface import encoder_cache_dir, text_to_vector; \
text_to_vector('cache warm'); \
print('Encoder weights pre-seeded into', encoder_cache_dir())" \
    || echo "WARNING: could not pre-seed the encoder model; the image will download it at first embed (no air-gapped start)."

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
# Default is empty (core-only), matching the builder stage. Use
# `make docker-build-full` to build the all-plugins variant.
ARG PLUGIN_EXTRAS=

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

# Place the staged extra host content whose targets sit outside $APP_HOME
# (e.g. /etc/ssl/extra). The builder applied the whole staged tree and pruned
# its $APP_HOME mirror, so this is exactly the complement of what the copy
# above carries — no path is written twice, and nothing reverts a $APP_HOME
# target to its staged original. Resolves to an empty tree, and the unpack
# below to a no-op, when EXTRA_COPY_FILES is unset.
#
# Note these entries cross as staged, not as the build left them: a build step
# that rewrote a target outside $APP_HOME would lose that edit. Placing them
# by path would require the target list at parse time, which a Dockerfile
# cannot have; nothing in this build writes outside $APP_HOME.
#
# The tree lands in a scratch folder instead of on "/" directly, because COPY
# applies the mirror folders' modes to the pre-existing folders they land on
# just as "cp -a" would -- resetting /tmp from 1777 to 755, which locks the
# service out of its own log and pid files. The RUN below unpacks it with
# tar --no-overwrite-dir, which leaves existing folders' metadata alone, and
# drops the scratch folder. Unpacking there also puts the content in place
# ahead of the ownership fixups, so targets under $APP_DATA_DIR (or any other
# path fixed up below) get the same treatment.
COPY --from=builder /extra-copy /extra-copy

# OpenShift compliance:
#  - safe.directory '*' lets git operate under any UID (the image is immutable,
#    so the CVE-2022-24765 threat model does not apply).
#  - gid 0 + `chmod g=u` on runtime-writable paths lets the arbitrary UID that
#    OpenShift assigns (always in gid 0) read/write everything the app needs.
#    Harmless on plain Docker/k8s: group perms equal user perms.
RUN tar -cf - -C /extra-copy . | tar -xf - --no-overwrite-dir -C / \
    && rm -rf /extra-copy \
    && git config --system --add safe.directory '*' \
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
