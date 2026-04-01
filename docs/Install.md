# Production Installation Guide

Complete guide to install and host Factory Analytics in a production environment using PM2.

## Table of Contents

- [Prerequisites](#prerequisites)
- [System Requirements](#system-requirements)
- [Installation Steps](#installation-steps)
- [PM2 Setup](#pm2-setup)
- [Configuration](#configuration)
- [SSL/HTTPS Setup](#sslhttps-setup)
- [Monitoring & Logs](#monitoring--logs)
- [Backup & Recovery](#backup--recovery)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.14+ | Runtime environment |
| Node.js | 18+ | PM2 process manager |
| PM2 | 5+ | Process management |
| SQLite3 | 3.35+ | Database |
| Git | 2.30+ | Version control |

### External Services

| Service | Required | Purpose |
|---------|----------|---------|
| Frigate NVR | Yes | Video/event layer |
| Ollama | Yes | Local vision model inference |

---

## System Requirements

### Minimum Hardware

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps

### Recommended Hardware (Production)

- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 100+ GB SSD (for logs and database growth)
- **Network**: 1 Gbps

### Operating System

- Ubuntu 22.04 LTS / 24.04 LTS (recommended)
- Debian 12+
- CentOS Stream 9
- macOS 12+ (development only)

---

## Installation Steps

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential curl wget git sqlite3

# Install Python 3.14
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.14 python3.14-venv python3.14-dev python3.14-distutils

# Verify Python version
python3.14 --version

# Install pip for Python 3.14
curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python3.14
```

### 2. Install Node.js and PM2

```bash
# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version
npm --version

# Install PM2 globally
sudo npm install -g pm2

# Setup PM2 startup script (starts on system boot)
pm2 startup systemd -u $USER --hp $HOME
```

### 3. Create Application User

```bash
# Create dedicated service user (recommended)
sudo useradd -r -s /bin/bash -m factory

# Or use your existing user for development
# Skip this step if using your own user
```

### 4. Clone and Setup Application

```bash
# Clone the repository
cd /opt  # or your preferred directory
sudo git clone <repository-url> factory-analytics
cd factory-analytics

# Set ownership (if using dedicated user)
sudo chown -R factory:factory /opt/factory-analytics

# Switch to application user
sudo su - factory
cd /opt/factory-analytics
```

### 5. Python Environment Setup

```bash
# Create virtual environment with Python 3.14
python3.14 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### 6. Directory Structure Setup

```bash
# Create required directories
mkdir -p data/db
mkdir -p logs
mkdir -p run
mkdir -p static

# Set permissions
chmod 755 data logs run static
chmod 644 requirements.txt .env.example
```

### 7. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Critical Production Settings:**

```bash
# Application
APP_HOST=0.0.0.0
APP_PORT=8090
PUBLIC_BASE_URL=https://your-domain.com
TIMEZONE=Asia/Kolkata
LOG_LEVEL=INFO

# Database
SQLITE_PATH=./data/db/factory_analytics.db
DATA_ROOT=./data
LOG_ROOT=./logs
RUN_ROOT=./run

# Frigate Integration
FRIGATE_URL=http://frigate-server:5000
FRIGATE_AUTH_MODE=basic  # or 'bearer' or 'none'
FRIGATE_USERNAME=your_username
FRIGATE_PASSWORD=your_password
FRIGATE_BEARER_TOKEN=
FRIGATE_VERIFY_TLS=true

# Ollama Integration
OLLAMA_URL=http://ollama-server:11434
OLLAMA_VISION_MODEL=qwen3.5:9b
OLLAMA_TIMEOUT_SEC=120
OLLAMA_KEEP_ALIVE=5m

# Scheduler
ANALYSIS_INTERVAL_SECONDS=300
SCHEDULER_ENABLED=true

# Security - CHANGE THIS!
MCP_TOKEN=your-secure-random-token-here
```

### 8. Generate Secure Token

```bash
# Generate a secure MCP token
python3.14 -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env file
# MCP_TOKEN=<generated-token>
```

---

## PM2 Setup

### Option A: PM2 Ecosystem File (Recommended)

Create `ecosystem.config.js` in the project root:

```javascript
module.exports = {
  apps: [
    {
      name: 'factory-api',
      script: '.venv/bin/uvicorn',
      args: 'factory_analytics.main:app --host 0.0.0.0 --port 8090 --log-level info',
      cwd: '/opt/factory-analytics',
      interpreter: 'none',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      error_file: './logs/api-error.log',
      out_file: './logs/api-out.log',
      log_file: './logs/api-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    },
    {
      name: 'factory-mcp',
      script: '.venv/bin/uvicorn',
      args: 'factory_analytics.mcp_server:app --host 0.0.0.0 --port 8099 --log-level info',
      cwd: '/opt/factory-analytics',
      interpreter: 'none',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1'
      },
      error_file: './logs/mcp-error.log',
      out_file: './logs/mcp-out.log',
      log_file: './logs/mcp-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
```

### Option B: Direct PM2 Commands

```bash
# Start API server
pm2 start .venv/bin/uvicorn \
  --name factory-api \
  --interpreter none \
  -- factory_analytics.main:app --host 0.0.0.0 --port 8090 --log-level info

# Start MCP server
pm2 start .venv/bin/uvicorn \
  --name factory-mcp \
  --interpreter none \
  -- factory_analytics.mcp_server:app --host 0.0.0.0 --port 8099 --log-level info
```

### PM2 Process Management

```bash
# Start all processes
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# List processes
pm2 list

# Monitor in real-time
pm2 monit

# View logs
pm2 logs

# View specific process logs
pm2 logs factory-api
pm2 logs factory-mcp

# Restart processes
pm2 restart all
pm2 restart factory-api

# Stop processes
pm2 stop all
pm2 stop factory-api

# Reload (graceful restart)
pm2 reload all

# Delete processes
pm2 delete all
pm2 delete factory-api
```

### PM2 Startup Configuration

```bash
# Generate startup script
pm2 startup systemd -u $USER --hp $HOME

# This outputs a command - run it!
# Example output:
# sudo env PATH=$PATH:/usr/bin /usr/lib/node_modules/pm2/bin/pm2 startup systemd -u factory --hp /home/factory

# Save current process list
pm2 save

# Verify startup is configured
systemctl status pm2-$USER
```

---

## Configuration

### Database Initialization

```bash
# The database is auto-created on first run
# Verify database was created
ls -la data/db/factory_analytics.db

# Check database integrity
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"

# View tables
sqlite3 data/db/factory_analytics.db ".tables"
```

### Log Rotation Setup

Create `/etc/logrotate.d/factory-analytics`:

```
/opt/factory-analytics/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 factory factory
    sharedscripts
    postrotate
        pm2 reload all > /dev/null 2>&1 || true
    endscript
}
```

### Systemd Service (Alternative to PM2)

Create `/etc/systemd/system/factory-api.service`:

```ini
[Unit]
Description=Factory Analytics API Server
After=network.target

[Service]
Type=simple
User=factory
Group=factory
WorkingDirectory=/opt/factory-analytics
Environment="PATH=/opt/factory-analytics/.venv/bin"
ExecStart=/opt/factory-analytics/.venv/bin/uvicorn factory_analytics.main:app --host 0.0.0.0 --port 8090 --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/factory-mcp.service`:

```ini
[Unit]
Description=Factory Analytics MCP Server
After=network.target

[Service]
Type=simple
User=factory
Group=factory
WorkingDirectory=/opt/factory-analytics
Environment="PATH=/opt/factory-analytics/.venv/bin"
ExecStart=/opt/factory-analytics/.venv/bin/uvicorn factory_analytics.mcp_server:app --host 0.0.0.0 --port 8099 --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable factory-api factory-mcp
sudo systemctl start factory-api factory-mcp
sudo systemctl status factory-api factory-mcp
```

---

## SSL/HTTPS Setup

### Using Nginx Reverse Proxy

1. **Install Nginx:**

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

2. **Create Nginx Configuration:**

Create `/etc/nginx/sites-available/factory-analytics`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=mcp_limit:10m rate=5r/s;

# Upstream servers
upstream factory_api {
    server 127.0.0.1:8090;
    keepalive 32;
}

upstream factory_mcp {
    server 127.0.0.1:8099;
    keepalive 16;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    return 301 https://$server_name$request_uri;
}

# HTTPS - Main Application
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json application/xml;

    # Static files
    location /static/ {
        alias /opt/factory-analytics/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location / {
        limit_req zone=api_limit burst=20 nodelay;
        
        proxy_pass http://factory_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # MCP endpoint
    location /mcp/ {
        limit_req zone=mcp_limit burst=10 nodelay;
        
        proxy_pass http://factory_mcp/mcp/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        proxy_pass_header Authorization;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://factory_api/health;
        access_log off;
    }
}
```

3. **Enable and test:**

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/factory-analytics /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

4. **Obtain SSL Certificate:**

```bash
# Obtain Let's Encrypt certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

---

## Monitoring & Logs

### PM2 Monitoring

```bash
# Real-time monitoring dashboard
pm2 monit

# Process info
pm2 show factory-api

# Resource usage
pm2 describe factory-api

# Process metrics
pm2 info factory-api
```

### Install PM2 Plus (Optional)

```bash
# Install pm2-logrotate
pm2 install pm2-logrotate

# Configure log rotation
pm2 set pm2-logrotate:max_size 50M
pm2 set pm2-logrotate:retain 30
pm2 set pm2-logrotate:compress true

# Connect to PM2 Plus (optional monitoring service)
pm2 link <secret_key> <public_key>
```

### Health Check Script

Create `/opt/factory-analytics/scripts/health-check.sh`:

```bash
#!/bin/bash

API_URL="http://127.0.0.1:8090/health"
MCP_URL="http://127.0.0.1:8099/health"
ALERT_WEBHOOK=""  # Slack/Discord webhook URL

check_service() {
    local url=$1
    local name=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $name is healthy"
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - $name is DOWN!"
        
        # Send alert
        if [ -n "$ALERT_WEBHOOK" ]; then
            curl -X POST -H 'Content-type: application/json' \
                --data "{\"text\":\"⚠️ $name is DOWN on $(hostname)\"}" \
                "$ALERT_WEBHOOK"
        fi
        
        # Attempt restart
        pm2 restart "$name"
        return 1
    fi
}

check_service "$API_URL" "factory-api"
check_service "$MCP_URL" "factory-mcp"
```

Add to crontab:

```bash
crontab -e

# Add health check every minute
* * * * * /opt/factory-analytics/scripts/health-check.sh >> /opt/factory-analytics/logs/health-check.log 2>&1
```

### Log Locations

| Log File | Purpose |
|----------|---------|
| `logs/api-out.log` | API stdout |
| `logs/api-error.log` | API errors |
| `logs/mcp-out.log` | MCP stdout |
| `logs/mcp-error.log` | MCP errors |
| `logs/api-combined.log` | All API logs |
| `logs/mcp-combined.log` | All MCP logs |

### View Logs

```bash
# PM2 logs
pm2 logs

# Follow specific logs
pm2 logs factory-api --lines 100

# System logs
tail -f logs/api-combined.log
tail -f logs/mcp-combined.log

# Search logs
grep -i error logs/api-error.log
grep -i "connection" logs/mcp-combined.log
```

---

## Backup & Recovery

### Database Backup Script

Create `/opt/factory-analytics/scripts/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/factory-analytics/backups"
DB_PATH="/opt/factory-analytics/data/db/factory_analytics.db"
DATE=$(date '+%Y-%m-%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/factory_analytics_${DATE}.db.gz"

mkdir -p "$BACKUP_DIR"

# Create backup
sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE%.gz}'"

# Compress
gzip "${BACKUP_FILE%.gz}"

# Keep only last 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup created: $BACKUP_FILE"
```

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/factory-analytics/scripts/backup.sh >> /opt/factory-analytics/logs/backup.log 2>&1
```

### Recovery Procedure

```bash
# Stop services
pm2 stop all

# Restore database
gunzip -c backups/factory_analytics_YYYY-MM-DD_HHMMSS.db.gz > data/db/factory_analytics.db

# Verify integrity
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"

# Start services
pm2 start all
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port
sudo lsof -i :8090
sudo lsof -i :8099

# Kill process
sudo kill -9 <PID>
```

#### 2. Permission Denied

```bash
# Fix permissions
sudo chown -R $USER:$USER /opt/factory-analytics
chmod -R 755 /opt/factory-analytics
chmod 644 .env
```

#### 3. Python Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf .venv
python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Database Locked

```bash
# Check for locked database
lsof data/db/factory_analytics.db

# Stop all services and check
pm2 stop all
sqlite3 data/db/factory_analytics.db "PRAGMA integrity_check;"
pm2 start all
```

#### 5. PM2 Process Crashes

```bash
# Check PM2 logs
pm2 logs --err

# Check process status
pm2 list
pm2 show factory-api

# Reset and restart
pm2 delete all
pm2 start ecosystem.config.js
pm2 save
```

#### 6. Memory Issues

```bash
# Check memory usage
pm2 monit

# Increase memory limit
pm2 start ecosystem.config.js --max-memory-restart 2G
```

### Diagnostic Commands

```bash
# System resources
free -h
df -h
top

# Python version
python3.14 --version

# Dependencies
pip list
pip check

# PM2 status
pm2 list
pm2 describe factory-api
pm2 describe factory-mcp

# Process info
ps aux | grep uvicorn
ps aux | grep python

# Network
netstat -tulpn | grep LISTEN
ss -tulpn

# Logs
journalctl -u pm2-$USER -f
dmesg | tail
```

### Debug Mode

```bash
# Stop PM2 processes
pm2 stop all

# Run in debug mode
./factory-analytics.sh debug

# Or manually with verbose logging
.venv/bin/uvicorn factory_analytics.main:app \
  --host 0.0.0.0 \
  --port 8090 \
  --log-level debug \
  --reload
```

---

## Security Checklist

- [ ] Changed default `MCP_TOKEN` to secure random value
- [ ] Configured firewall (ufw/iptables) to restrict ports
- [ ] SSL/HTTPS enabled via Nginx reverse proxy
- [ ] Environment file `.env` has restricted permissions (600)
- [ ] Database backup schedule configured
- [ ] Log rotation configured
- [ ] Health monitoring configured
- [ ] PM2 startup script enabled
- [ ] Unnecessary services disabled
- [ ] Strong passwords for Frigate authentication
- [ ] TLS verification enabled for Frigate connection
- [ ] Rate limiting configured in Nginx

---

## Quick Reference

### Start Services
```bash
pm2 start ecosystem.config.js
```

### Stop Services
```bash
pm2 stop all
```

### Restart Services
```bash
pm2 restart all
```

### View Status
```bash
pm2 list
pm2 monit
```

### View Logs
```bash
pm2 logs
```

### Update Application
```bash
pm2 stop all
git pull
source .venv/bin/activate
pip install -r requirements.txt
pm2 restart all
```

### Full Systemd Alternative
If you prefer systemd over PM2, use the systemd service files provided in the [Configuration](#configuration) section.

---

## Support

- Check logs: `logs/` directory
- Health endpoint: `http://localhost:8090/health`
- API docs: `http://localhost:8090/docs`
- PM2 monitoring: `pm2 monit`
- Database: `data/db/factory_analytics.db`

---

**Installation complete!** 

Access your application:
- GUI: `https://your-domain.com`
- API: `https://your-domain.com/docs`
- MCP: `https://your-domain.com/mcp`
