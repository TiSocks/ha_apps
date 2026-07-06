# Use a pure, lightweight Python image
FROM python:3.11-alpine

# Don't buffer output
ENV PYTHONUNBUFFERED=1

ARG APP_VERSION=1.1.4
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/TiSocks/HyundaiDataLogger"

# Install timezone data so Alpine understands the TZ variable
RUN apk add --no-cache tzdata gcc musl-dev postgresql-dev

# Set working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install the required Python packages from the file
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY app.py kia_logger.py /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Create a data directory for persistence
RUN mkdir -p /app/data

# Expose the web UI port
EXPOSE 5002

# Run the app natively
CMD ["python3", "app.py"]
