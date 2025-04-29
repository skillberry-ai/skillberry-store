FROM python:3.11

# Define build arguments
ARG BUILD_VERSION=latest
ARG BUILD_DATE

# Label the image with metadata
LABEL version="$BUILD_VERSION"
LABEL date="$BUILD_DATE"

# Set the working directory
WORKDIR /app

# Copy the application
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Expose a port (change if needed)
EXPOSE 8000

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD echo "Starting blueberry tools-service (version $BUILD_VERSION built on $BUILD_DATE)" && echo "" && python main.py
