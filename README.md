# lego-train-controller

A Python-based controller for LEGO Technic Hubs using Bluetooth Low Energy (BLE) communication. This project allows you to control LEGO switches and trains through both a REST API and command-line interface. It supports advanced features like self-driving trains with color pattern recognition and reliable switch control.

## Prerequisites

- Python 3.x
- `bleak` library for Bluetooth Low Energy communication
- `msgpack` for data serialization
- Linux system with Bluetooth support (tested on Raspberry Pi)
- Root/sudo privileges for Bluetooth operations
- FastAPI and uvicorn for the web service
- Python virtual environment (recommended)
- LEGO Technic Hubs (City Hub for trains, Technic Hub for switches)
- LEGO Color Distance Sensor (for self-driving train functionality)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/lego-train-controller.git
   cd lego-train-controller
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Web Service

### Direct Command Line

You can run the web service directly using uvicorn:

```bash
sudo PYTHONPATH=/path/to/lego-train-controller uvicorn webservice.train_service:app --host 0.0.0.0 --port 8000
```

### As a System Service

To run as a system service (recommended for production):

1. Copy the example service file, customize it for your environment, and install it:
   ```bash
   # Copy the example file
   cp lego-controller.service_example lego-controller.service
   
   # Edit the file to update paths and settings
   nano lego-controller.service
   
   # Copy to systemd
   sudo cp lego-controller.service /etc/systemd/system/
   ```

2. Reload systemd daemon:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable the service to start on boot:
   ```bash
   sudo systemctl enable lego-controller
   ```

4. Control the service:
   ```bash
   sudo systemctl start lego-controller    # Start the service
   sudo systemctl stop lego-controller     # Stop the service
   sudo systemctl restart lego-controller  # Restart the service
   sudo systemctl status lego-controller   # Check service status
   ```

## Web Service API Endpoints

The web service runs on port 8000 and provides the following REST API endpoints:

### Train Control
- `POST /train`
  ```json
  {
    "hub_id": 0,
    "power": 40  // -100 to 100
  }
  ```

### Self-Driving Train Control
- `POST /selfdrive`
  ```json
  {
    "hub_id": 0,
    "self_drive": 1  // 1 for self-drive mode, 0 for manual mode
  }
  ```

### Switch Control
- `POST /switch`
  ```json
  {
    "hub_id": 0,
    "switch": "A",  // A, B, C, or D
    "position": "STRAIGHT"  // STRAIGHT or DIVERGING
  }
  ```

### Status Endpoints
- `GET /connected/trains` - List connected train hubs with detailed status information including:
  - Current speed and direction
  - Self-drive mode status
  - Connection quality (RSSI)
  - Last update timestamp
  
- `GET /connected/switches` - List connected switch hubs with detailed information including:
  - Current position of each switch (STRAIGHT or DIVERGING)
  - Connected motor ports
  - Command reliability statistics
  - Connection quality (RSSI)
  - Last update timestamp

### System Control
- `POST /reset` - Reset Bluetooth connections

## Features

### Train Control
- Manual control with variable speed (-100 to 100)
- Self-driving mode with color pattern recognition
- Automatic stopping at detected color patterns
- Support for multiple train hubs
- Real-time status monitoring and reporting

### Switch Control
- Support for both Motor and DCMotor switch types
- Control of up to 4 switches per hub (ports A-D)
- Automatic detection of connected motors
- Command verification with retry mechanism
- Reliability statistics for each switch

### System Features
- Real-time status monitoring of switch and train positions
- Automatic Bluetooth connection management with recovery
- Command queuing for improved performance
- Robust error handling and recovery
- Support for multiple LEGO Technic Hubs
- REST API for remote control
- Systemd service integration for production deployment
- Logging to system files (/var/log/lego-controller.log)

## Technical Details

The project consists of several components:

### Project Structure
```
lego-train-controller/
├── __init__.py
├── .gitignore
├── lego-controller.service_example  # Systemd service template (customize before use)
├── lego-controller.service          # Your customized service file (not in git)
├── README.md
├── requirements.txt
├── controllers/                    # Controller logic
│   ├── __init__.py
│   ├── switch_controller.py        # Switch control logic
│   └── train_controller.py         # Train control logic
├── hubs/                           # Code that runs on LEGO hubs
│   ├── switch_receiver_dcmotor.py  # DCMotor-based switch control
│   ├── switch_receiver_motor.py    # Motor-based switch control
│   └── train_receiver.py           # Train control with color sensing
├── servers/                        # Backend server components
│   ├── __init__.py
│   ├── bluetooth_scanner.py        # Enhanced BLE scanning
│   ├── lego_service.py             # Core service functionality
│   └── main.py                     # Main controller entry point
├── utils/                          # Shared utilities
│   ├── __init__.py
│   └── constants.py                # Shared constants
└── webservice/                     # API layer
    └── train_service.py            # FastAPI implementation
```

### Server Components
- `BetterBleScanner`: Custom BLE scanner with forced cleanup and auto-recovery
- `SwitchController`: Manages switch positions and commands with verification
- `TrainController`: Handles train movement, speed control, and self-driving
- `FastAPI Web Service`: Provides REST API endpoints for remote control

### Hub Components
- `train_receiver.py`: Runs on the LEGO City Hub to control trains with color sensing
- `switch_receiver_motor.py`: Runs on LEGO Technic Hub to control switches using Motor
- `switch_receiver_dcmotor.py`: Runs on LEGO Technic Hub to control switches using DCMotor

### Communication
- Bluetooth Low Energy (BLE) for wireless communication
- Custom protocol for reliable command transmission
- Status monitoring with automatic reconnection
- Command queuing and batching for improved performance

### Recent Structure Changes

The project has recently undergone a structural reorganization to improve code organization and maintainability:

1. **Controller Logic Separation**:
   - Controller logic has been moved from `servers/` to a dedicated `controllers/` directory
   - This separates the business logic from the server infrastructure

2. **Shared Utilities**:
   - Constants and shared utilities have been moved to a dedicated `utils/` directory
   - This improves reusability and makes dependencies clearer

3. **Import Structure**:
   - Changed from relative imports to absolute imports for better reliability
   - This prevents issues with imports when running from different contexts

These changes make the codebase more modular and easier to maintain, while preserving all functionality.

### Recommended Structure Improvements
For future development, consider these additional structural improvements:

1. **Configuration Management**:
   - Add a dedicated `config/` directory for configuration files
   - Move hardcoded constants to configuration files

2. **Testing**:
   - Add a `tests/` directory with unit and integration tests
   - Include test fixtures for simulating hub connections

3. **Documentation**:
   - Create a `docs/` directory with detailed documentation
   - Add inline code documentation using docstrings

4. **Examples**:
   - Add an `examples/` directory with sample scripts
   - Include example configurations for different setups

5. **Client-Server Separation**:
   - Consider separating client code into a dedicated package
   - This would allow for easier distribution of client libraries

## Troubleshooting

If you encounter issues:

1. Check the service logs:
   ```bash
   sudo journalctl -u lego-controller -f
   ```

2. View application logs:
   ```bash
   sudo tail -f /var/log/lego-controller.log
   sudo tail -f /var/log/lego-controller.error.log
   ```

3. Reset Bluetooth connections:
   ```bash
   curl -X POST http://localhost:8000/reset
   ```

4. Verify Bluetooth status:
   ```bash
   sudo hciconfig
   ```

## Self-Driving Train Features

The self-driving train functionality uses a LEGO Color Distance Sensor to detect colors and patterns on the track. Key features include:

- Color pattern recognition (RED, YELLOW, GREEN, BLUE, GRAY, WHITE)
- Automatic stopping at programmed color patterns
- Forward and backward movement until pattern detection
- Noise filtering for reliable color detection
- Real-time status reporting during autonomous operation

To use self-driving mode:
1. Set up a track with color markers (using LEGO bricks or colored paper)
2. Enable self-driving mode via the API
3. The train will automatically respond to color patterns based on programmed behavior

## Error Handling and Reliability

The system includes comprehensive error handling for:
- Bluetooth connection issues with automatic recovery
- Command transmission failures with intelligent retry mechanisms
- Invalid API requests with detailed error responses
- Status parsing errors with fallback mechanisms
- Service recovery and auto-restart
- Command verification with position feedback
- Reliability statistics for monitoring system performance

Each operation includes multiple fallback mechanisms to ensure reliable communication with the LEGO hubs, with special attention to the challenges of Bluetooth communication in potentially noisy environments.
