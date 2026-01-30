# Systemd Service Setup Guide

Complete guide for setting up the LEGO Train Controller as a systemd service that starts automatically on Raspberry Pi boot.

## Prerequisites

- Raspberry Pi with Raspberry Pi OS installed
- Project deployed to Raspberry Pi (see [RASPBERRY_PI_DEPLOY.md](RASPBERRY_PI_DEPLOY.md))
- Python virtual environment set up with dependencies installed
- `.env` file configured with your settings

## Quick Setup (TL;DR)

```bash
# 1. Create the service file
sudo nano /etc/systemd/system/lego-controller.service

# 2. Paste the configuration (see below)

# 3. Enable and start
sudo systemctl daemon-reload
sudo systemctl enable lego-controller
sudo systemctl start lego-controller

# 4. Check status
sudo systemctl status lego-controller
```

---

## Step-by-Step Setup

### Step 1: Verify Installation

Before creating the service, verify your installation is working:

```bash
# Navigate to project directory
cd ~/lego-train-controller

# Activate virtual environment
source .venv/bin/activate

# Test run the service
python3 -m uvicorn webservice.train_service:app --host 0.0.0.0 --port 8000
```

Press Ctrl+C to stop the test. If it works, proceed to the next step.

### Step 2: Create the Systemd Service File

Create the service configuration file:

```bash
sudo nano /etc/systemd/system/lego-controller.service
```

Paste the following configuration, **replacing the paths with your actual installation directory**:

```ini
[Unit]
Description=LEGO Train and Switch Controller Service
After=network.target bluetooth.target
Requires=bluetooth.service

[Service]
Type=simple
User=pi
Group=bluetooth
WorkingDirectory=/home/pi/lego-train-controller
Environment="PYTHONPATH=/home/pi/lego-train-controller"
ExecStart=/home/pi/lego-train-controller/.venv/bin/uvicorn webservice.train_service:app --host 0.0.0.0 --port 8000
StandardOutput=append:/var/log/lego-controller.log
StandardError=append:/var/log/lego-controller.error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Important Configuration Notes:**

- **User**: Should be `pi` (or your username)
- **Group**: Set to `bluetooth` for Bluetooth access
- **WorkingDirectory**: Full path to your project directory
- **PYTHONPATH**: Same as WorkingDirectory
- **ExecStart**: Full path to uvicorn in your virtual environment
- **Restart=always**: Service will auto-restart if it crashes
- **RestartSec=10**: Wait 10 seconds before restarting

Save the file (Ctrl+X, Y, Enter).

### Step 3: Create Log Files with Proper Permissions

```bash
# Create log files
sudo touch /var/log/lego-controller.log
sudo touch /var/log/lego-controller.error.log

# Set ownership to your user
sudo chown pi:pi /var/log/lego-controller.log
sudo chown pi:pi /var/log/lego-controller.error.log

# Set permissions
sudo chmod 644 /var/log/lego-controller.log
sudo chmod 644 /var/log/lego-controller.error.log
```

### Step 4: Enable and Start the Service

```bash
# Reload systemd to read the new service file
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable lego-controller

# Start the service now
sudo systemctl start lego-controller

# Check the status
sudo systemctl status lego-controller
```

**Expected Output:**
```
● lego-controller.service - LEGO Train and Switch Controller Service
     Loaded: loaded (/etc/systemd/system/lego-controller.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2026-01-30 10:00:00 GMT; 5s ago
   Main PID: 1234 (uvicorn)
      Tasks: 2 (limit: 1234)
     Memory: 50.0M
        CPU: 1.234s
     CGroup: /system.slice/lego-controller.service
             └─1234 /home/pi/lego-train-controller/.venv/bin/python3 /home/pi/lego-train-controller/.venv/bin/uvicorn...
```

If you see `Active: active (running)`, the service is working correctly!

### Step 5: Verify Service is Working

Test the service with curl:

```bash
# Health check (no authentication required)
curl http://localhost:8000/health | python3 -m json.tool

# Get connected trains (requires API key)
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/connected/trains
```

---

## Service Management Commands

### Basic Operations

```bash
# Start the service
sudo systemctl start lego-controller

# Stop the service
sudo systemctl stop lego-controller

# Restart the service
sudo systemctl restart lego-controller

# Check service status
sudo systemctl status lego-controller

# Enable service to start on boot
sudo systemctl enable lego-controller

# Disable service from starting on boot
sudo systemctl disable lego-controller
```

### Viewing Logs

```bash
# View service logs from systemd journal
sudo journalctl -u lego-controller -f

# View last 50 lines
sudo journalctl -u lego-controller -n 50

# View logs since last boot
sudo journalctl -u lego-controller -b

# View application logs directly
tail -f /var/log/lego-controller.log
tail -f /var/log/lego-controller.error.log
```

---

## Updating the Service

When you update your code or configuration:

### 1. Update Code

```bash
cd ~/lego-train-controller
git pull origin main  # Or your preferred method

# Update dependencies if needed
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Restart Service

```bash
# Just restart the service - no need to reload systemd
sudo systemctl restart lego-controller

# Check that it started successfully
sudo systemctl status lego-controller
```

### 3. If Service File Changed

If you modified the service file in `/etc/systemd/system/lego-controller.service`:

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Restart the service
sudo systemctl restart lego-controller
```

---

## Troubleshooting

### Service Won't Start

**Check the status:**
```bash
sudo systemctl status lego-controller
```

**Common issues:**

1. **Wrong paths in service file**
   - Verify `WorkingDirectory` exists: `ls /home/pi/lego-train-controller`
   - Verify virtual environment exists: `ls /home/pi/lego-train-controller/.venv/bin/uvicorn`

2. **Permission issues**
   - Ensure user `pi` can access the directory
   - Ensure user `pi` is in the `bluetooth` group: `groups pi`

3. **Missing dependencies**
   ```bash
   cd ~/lego-train-controller
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Port already in use**
   - Check if port 8000 is available: `sudo lsof -i :8000`
   - Kill conflicting process or change port in service file

### Service Keeps Restarting

**View detailed logs:**
```bash
sudo journalctl -u lego-controller -n 100
tail -n 100 /var/log/lego-controller.error.log
```

**Common causes:**
- Missing `.env` file
- Invalid configuration in `.env`
- Bluetooth adapter issues
- Python import errors

### Bluetooth Not Working

**Check Bluetooth service:**
```bash
sudo systemctl status bluetooth
sudo hciconfig hci0
```

**Verify user is in bluetooth group:**
```bash
# Check current groups
groups pi

# Add to bluetooth group if missing
sudo usermod -a -G bluetooth pi

# Restart service
sudo systemctl restart lego-controller
```

**Check passwordless sudo for Bluetooth:**
```bash
# Test Bluetooth command without password
sudo -n hcitool cmd 0x08 0x000A 00

# If it asks for password, set up passwordless sudo
echo 'pi ALL=(ALL) NOPASSWD: /usr/bin/hcitool, /usr/bin/bluetoothctl, /usr/sbin/hciconfig' | sudo tee /etc/sudoers.d/bluetooth
sudo chmod 0440 /etc/sudoers.d/bluetooth
```

### Logs Not Appearing

**Check log file permissions:**
```bash
ls -l /var/log/lego-controller*

# Fix if needed
sudo chown pi:pi /var/log/lego-controller.log
sudo chown pi:pi /var/log/lego-controller.error.log
```

### Service Not Starting on Boot

**Check if service is enabled:**
```bash
sudo systemctl is-enabled lego-controller
```

Should return `enabled`. If not:
```bash
sudo systemctl enable lego-controller
```

**Check boot logs:**
```bash
sudo journalctl -u lego-controller -b
```

---

## Advanced Configuration

### Running on Different Port

Edit the service file:
```bash
sudo nano /etc/systemd/system/lego-controller.service
```

Change the ExecStart line:
```ini
ExecStart=/home/pi/lego-train-controller/.venv/bin/uvicorn webservice.train_service:app --host 0.0.0.0 --port 8080
```

Then reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart lego-controller
```

### Custom Environment Variables

Add environment variables in the service file under `[Service]`:

```ini
[Service]
Environment="PYTHONPATH=/home/pi/lego-train-controller"
Environment="LOG_LEVEL=DEBUG"
Environment="CUSTOM_VAR=value"
```

Note: Variables in `.env` file will still be loaded by the application.

### Multiple Service Instances

To run multiple instances on different ports:

```bash
# Create a second service file
sudo cp /etc/systemd/system/lego-controller.service /etc/systemd/system/lego-controller-2.service

# Edit it with different port and log files
sudo nano /etc/systemd/system/lego-controller-2.service
```

Change:
- Port in ExecStart
- Log file paths
- Add `Environment="PORT=8001"` if your app supports it

---

## Monitoring and Maintenance

### Service Health Monitoring

Create a simple monitoring script:

```bash
nano ~/monitor-lego-service.sh
```

Add this content:
```bash
#!/bin/bash
if ! systemctl is-active --quiet lego-controller; then
    echo "Service is down! Sending alert..."
    # Add your notification method here (email, SMS, etc.)
fi
```

Make it executable and add to crontab:
```bash
chmod +x ~/monitor-lego-service.sh
crontab -e
```

Add this line to check every 5 minutes:
```
*/5 * * * * /home/pi/monitor-lego-service.sh
```

### Log Rotation

The logs can grow large over time. Set up log rotation:

```bash
sudo nano /etc/logrotate.d/lego-controller
```

Add this configuration:
```
/var/log/lego-controller*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 pi pi
}
```

This will:
- Rotate logs daily
- Keep 14 days of logs
- Compress old logs
- Create new log files with proper ownership

---

## Testing Auto-Start on Boot

To verify the service starts automatically on boot:

```bash
# Reboot the Raspberry Pi
sudo reboot

# After reboot, check service status
sudo systemctl status lego-controller

# Test the API
curl http://localhost:8000/health
```

---

## Security Considerations

### File Permissions

Ensure proper permissions on sensitive files:

```bash
# Restrict .env file
chmod 600 ~/lego-train-controller/.env

# Verify service file permissions
sudo ls -l /etc/systemd/system/lego-controller.service
# Should be: -rw-r--r-- root root
```

### Firewall Configuration

If using UFW firewall:

```bash
# Allow only from local network
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Or allow from specific IP
sudo ufw allow from 192.168.1.100 to any port 8000
```

### Regular Updates

Keep system and dependencies updated:

```bash
# System updates
sudo apt-get update && sudo apt-get upgrade -y

# Python dependencies
cd ~/lego-train-controller
source .venv/bin/activate
pip install -r requirements.txt --upgrade
```

---

## Quick Reference

### Installation Paths (Standard Setup)

- **Project Directory**: `/home/pi/lego-train-controller`
- **Virtual Environment**: `/home/pi/lego-train-controller/.venv`
- **Uvicorn Binary**: `/home/pi/lego-train-controller/.venv/bin/uvicorn`
- **Service File**: `/etc/systemd/system/lego-controller.service`
- **Application Logs**: `/var/log/lego-controller.log`
- **Error Logs**: `/var/log/lego-controller.error.log`
- **Environment Config**: `/home/pi/lego-train-controller/.env`

### Essential Commands Cheat Sheet

```bash
# Service control
sudo systemctl start lego-controller       # Start
sudo systemctl stop lego-controller        # Stop
sudo systemctl restart lego-controller     # Restart
sudo systemctl status lego-controller      # Status

# View logs
sudo journalctl -u lego-controller -f      # Follow journal
tail -f /var/log/lego-controller.log       # Follow app logs

# After code update
cd ~/lego-train-controller && git pull && sudo systemctl restart lego-controller

# After service file change
sudo systemctl daemon-reload && sudo systemctl restart lego-controller

# Test service
curl http://localhost:8000/health
```

---

## Related Documentation

- **[README.md](README.md)** - Project overview and features
- **[RASPBERRY_PI_DEPLOY.md](RASPBERRY_PI_DEPLOY.md)** - Complete deployment guide
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - General deployment information
- **[SECURITY.md](SECURITY.md)** - Security best practices

---

## Support

If you encounter issues:

1. Check service status: `sudo systemctl status lego-controller`
2. View logs: `sudo journalctl -u lego-controller -n 100`
3. Verify paths in service file match your installation
4. Ensure all prerequisites are installed
5. Test manual startup before troubleshooting service issues

For persistent issues, ensure:
- Virtual environment is activated when testing manually
- All dependencies are installed
- `.env` file is properly configured
- Bluetooth service is running
- User has proper permissions
