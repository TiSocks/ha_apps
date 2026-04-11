# Use a pure, lightweight Python image (bypassing HA's s6-overlay)
FROM python:3.11-alpine

# Don't buffer output
ENV PYTHONUNBUFFERED=1

# Set the container's timezone to Perth
ENV TZ="Australia/Perth"

# Install timezone data so Alpine understands the TZ variable
RUN apk add --no-cache tzdata

# Install the required Python packages
# (Raw Python images don't require the break-system-packages flag)
RUN pip install --no-cache-dir hyundai_kia_connect_api schedule

# Copy only the Python script into the container
COPY kia_logger.py /

# Run the script natively as the container's main process
CMD ["python3", "/kia_logger.py"]