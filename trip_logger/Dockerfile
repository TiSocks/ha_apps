# Use a pure, lightweight Python image
FROM python:3.12-slim

# Don't buffer output
ENV PYTHONUNBUFFERED=1

ARG APP_VERSION=1.1.6
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/TiSocks/CarDataLogger"

RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

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
