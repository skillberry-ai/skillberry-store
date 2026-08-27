#!/bin/bash
# Stage extra host content into the container build context.
#
# Usage: stage-extra-copy.sh "<src>:<dst>[,<src>:<dst>...]"
# Example: stage-extra-copy.sh "./certs:/etc/ssl/extra,../my.yaml:/app/conf.yaml"
#
# A container build can only read from its build context, so host content that
# lives outside the project root cannot be COPY'd directly. This script copies
# each source into the staging folder below, laid out as a mirror of its
# absolute target path. The Dockerfile then unpacks that mirror with a single
# recursive copy into "/", which lands every entry at its target.
#
# Per pair: a directory source contributes its tree *contents* to <dst>; a file
# source is copied to <dst> (or into it, if <dst> ends with "/").
# <dst> must be an absolute path inside the container.
#
# The staging folder is rewritten from scratch on every call, so it always
# reflects the current spec (an empty spec removes it altogether).

set -e

# Normalize the staged content for the container runtime:
#
#  - umask 022 keeps the mirror's intermediate folders traversable (755)
#    whatever the caller's umask is. The unpack applies an archived folder's
#    mode to any folder it has to create along a target path, so under a
#    private umask the app could not reach its own content. (Folders that
#    already exist in the image keep their own metadata - the Dockerfile
#    unpacks with tar --no-overwrite-dir for exactly that reason.)
#
#  - "chmod g=u" per staged item (below) gives the group the owner's access.
#    The build COPY forces ownership of everything in the context to root and
#    gid 0, and both the image's USER and the arbitrary UID that OpenShift
#    assigns run with gid 0 - so this is what makes the content readable at
#    runtime, and writable exactly when it was writable to its owner on the
#    host. It is the same policy the Dockerfile applies to $APP_HOME, extended
#    to targets outside it.
umask 022

# Keep in sync with the staging folder unpacked by the Dockerfile.
STAGE_DIR=".extra-copy"

SPEC="$1"

rm -rf "$STAGE_DIR"
[ -n "$SPEC" ] || exit 0

IFS=',' read -ra PAIRS <<< "$SPEC"
for pair in "${PAIRS[@]}"; do
    src="${pair%%:*}"
    dst="${pair#*:}"
    if [ "$src" = "$pair" ] || [ -z "$src" ] || [ -z "$dst" ]; then
        echo "EXTRA_COPY_FILES: expected <source>:<target>, got '$pair'" >&2
        exit 1
    fi
    case "$dst" in
        /*) ;;
        *)  echo "EXTRA_COPY_FILES: target '$dst' must be an absolute container path" >&2
            exit 1 ;;
    esac

    staged="$STAGE_DIR/${dst#/}"
    if [ -d "$src" ]; then
        mkdir -p "$staged"
        cp -aL "$src/." "$staged/"
        chmod -R g=u "$staged"
    elif [ -f "$src" ]; then
        case "$dst" in
            */) mkdir -p "$staged" && cp -aL "$src" "$staged/" \
                    && chmod g=u "$staged/$(basename "$src")" ;;
            *)  mkdir -p "$(dirname "$staged")" && cp -aL "$src" "$staged" \
                    && chmod g=u "$staged" ;;
        esac
    else
        echo "EXTRA_COPY_FILES: source '$src' does not exist" >&2
        exit 1
    fi
    echo "Staged for copy into the image: $src -> $dst"
done
