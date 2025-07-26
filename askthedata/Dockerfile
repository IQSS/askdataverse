FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    liblapack-dev \
    gfortran \
    libpng-dev \
    libjpeg-dev \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py /app/
# Do NOT bake key.json if it contains secrets
# COPY key.json /app/

EXPOSE 8085

CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8085", "app.py"]
