# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy files
COPY mspa_mqtt_bridge.py .
COPY run.sh .

# Install dependencies
RUN pip install --no-cache-dir requests paho-mqtt pytz

# Make run.sh executable
RUN chmod +x run.sh

# Set default command
CMD ["/app/run.sh"]
