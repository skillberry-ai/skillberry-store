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
RUN --mount=type=ssh make install-requirements

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

# Label the image with metadata
LABEL version="$BUILD_VERSION" \
      date="$BUILD_DATE"

# Persist into the image runtime environment
ENV BUILD_VERSION=$BUILD_VERSION \
    BUILD_DATE=$BUILD_DATE \
    SERVICE_NAME=$SERVICE_NAME \
    SERVICE_PORTS=$SERVICE_PORTS \
    SERVICE_ENTRY_MODULE=$SERVICE_ENTRY_MODULE

# Python, NodeJS and venv are already set in the base image
# WORKDIR is already set in the base image to /app

# Copy entire /app directory from builder stage
# This includes the application code and the .venv with all installed dependencies
COPY --from=builder /app /app

# Expose all service ports
EXPOSE $SERVICE_PORTS

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD ["sh", "-c", "make run"]
