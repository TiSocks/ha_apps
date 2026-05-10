# Use a pure, lightweight Python image (bypassing HA's s6-overlay)
FROM python:3.12-alpine

# Don't buffer output
ENV PYTHONUNBUFFERED=1

# Install timezone data so Alpine understands the TZ variable
RUN apk add --no-cache tzdata

## Install the required Python packages
## (Raw Python images don't require the break-system-packages flag)
#RUN pip install --no-cache-dir hyundai_kia_connect_api schedule

# Copy the requirements file into the container
COPY requirements.txt /

# Install the required Python packages from the file
RUN pip install --no-cache-dir -r /requirements.txt

# Copy only the Python script into the container
COPY kia_logger.py /

# Run the script natively as the container's main process
CMD ["python3", "/kia_logger.py"]
