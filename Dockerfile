# Base image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app


# Install system dependencies for MySQL client
RUN apt-get update && apt-get install -y default-libmysqlclient-dev gcc

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
 && rm -rf /var/lib/apt/lists/*


# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt


# Copy the project files
COPY . .

# Expose Django's default port
EXPOSE 8000

# Prevent .pyc creation and enable unbuffered output
ENV PYTHONUNBUFFERED=1

# Run Django migrations and start the server
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
