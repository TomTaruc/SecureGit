# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    nginx \
    libpq-dev \
    gcc \
    postgresql-client \
    openssh-server \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app

# Setup directories
RUN mkdir -p /srv/git /mnt/backup /var/run/sshd
RUN chown -R www-data:www-data /app /srv/git /mnt/backup

# Expose ports for Flask (Gunicorn) and SSH
EXPOSE 5000
EXPOSE 2222

# Environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV GIT_REPOS_BASE=/srv/git
ENV REDIS_URL=redis://redis:6379/0

# Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
