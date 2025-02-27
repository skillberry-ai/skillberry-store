FROM python:3.10

# Define build arguments
ARG BUILD_VERSION=latest
ARG BUILD_DATE

# Label the image with metadata
LABEL version="$BUILD_VERSION"
LABEL date="$BUILD_DATE"

# Set the working directory
WORKDIR /app

# Copy only requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY contrib .

# Expose a port (change if needed)
EXPOSE 8000

# Set the entrypoint command (adjust if running FastAPI, Flask, Django, etc.)
CMD echo "Starting blueberry tools-service (version $BUILD_VERSION built on $BUILD_DATE)" && echo "" && python main.py
