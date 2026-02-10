FROM public.ecr.aws/docker/library/python:3.11

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

# Set the working directory
WORKDIR /app

# Create the venv
RUN python -m venv /app/.venv

# Make the venv “default” for every later RUN and at runtime
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

# Copy the application
COPY . .
RUN make install_requirements

# Expose all service ports
EXPOSE $SERVICE_PORTS

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD ["sh", "-c", "make run"]
