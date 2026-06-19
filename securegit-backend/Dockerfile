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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set git global config
RUN git config --global init.defaultBranch main && \
    git config --global --add safe.directory '*'

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app

# Setup directories and git user
RUN mkdir -p /srv/git /mnt/backup /var/run/sshd
RUN useradd -m -d /home/git -s /bin/bash git
RUN chown -R www-data:www-data /app /mnt/backup
RUN chown -R git:git /srv/git /home/git

# Configure SSH daemon
RUN ssh-keygen -A && \
    echo "Port 2222" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication no" >> /etc/ssh/sshd_config && \
    echo "AllowUsers git" >> /etc/ssh/sshd_config && \
    echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "AuthorizedKeysFile /home/git/.ssh/authorized_keys" >> /etc/ssh/sshd_config

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Expose ports for Flask (Gunicorn) and SSH
EXPOSE 5000
EXPOSE 2222

# Environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV GIT_REPOS_BASE=/srv/git
ENV REDIS_URL=redis://redis:6379/0

# Start via entrypoint (handles migrations + gunicorn)
CMD ["/app/entrypoint.sh"]

