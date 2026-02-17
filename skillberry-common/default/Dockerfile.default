ARG BASE_IMAGE_FULL_NAME=skillberry-base
ARG BASE_IMAGE_TAG=latest

FROM ${BASE_IMAGE_FULL_NAME}:${BASE_IMAGE_TAG}

# Define build arguments
ARG BUILD_VERSION=latest
ARG BUILD_DATE
ARG SERVICE_NAME
ARG SERVICE_PORTS
ARG SERVICE_ENTRY_MODULE

# Label the image with metadata
LABEL version="$BUILD_VERSION"
LABEL date="$BUILD_DATE"

# Persist into the image runtime environment
ENV BUILD_VERSION=$BUILD_VERSION \
    BUILD_DATE=$BUILD_DATE \
    SERVICE_NAME=$SERVICE_NAME \
    SERVICE_PORTS=$SERVICE_PORTS \
    SERVICE_ENTRY_MODULE=$SERVICE_ENTRY_MODULE

# Python, NodeJS and venv are already set in the base image
# WORKDIR is already set in the base image to /app

# Copy the application
COPY . .
RUN make install-requirements

# Expose all service ports
EXPOSE $SERVICE_PORTS

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD ["sh", "-c", "make run"]
