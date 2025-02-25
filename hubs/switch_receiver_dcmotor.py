from pybricks.hubs import TechnicHub
from pybricks.pupdevices import DCMotor
from pybricks.parameters import Port, Color
from pybricks.tools import wait

# Channels for communication
COMMAND_CHANNEL = 1
STATUS_CHANNEL = 11

# Initialize hub with broadcast capability
hub = TechnicHub(
    broadcast_channel=STATUS_CHANNEL, 
    observe_channels=[COMMAND_CHANNEL]
)

# Dictionary to store motors and their ports
motors = {}
active_ports = []

# One-time port detection at startup
print("Detecting connected devices...")
for port, port_name in zip([Port.A, Port.B, Port.C, Port.D], ['A', 'B', 'C', 'D']):
    try:
        motor = DCMotor(port)
        motors[port_name] = motor
        active_ports.append(port_name)
        print("Found motor on Port " + port_name)
    except Exception as e:
        print("No motor detected on Port " + port_name)

HUB_NAME = hub.system.name()
print("Hub name: " + HUB_NAME)
print("Hub ID: " + str(COMMAND_CHANNEL))
print("Active ports: " + str(active_ports))

# Track last command to avoid repeats
last_command = None

# Track switch positions (0=straight, 1=diverging)
switch_positions = {}
for port in active_ports:
    switch_positions[port] = 0

def broadcast_init_status():
    """Broadcast initialization status"""
    try:
        # Convert active ports to a binary number
        port_bits = 0
        for port in active_ports:
            port_bits += 1 << (ord('D') - ord(port))
        
        # Send initialization status
        init_data = (COMMAND_CHANNEL, HUB_NAME, 0, port_bits)
        hub.ble.broadcast(init_data)
        hub.light.on(Color.GREEN)
        print("Broadcasting initialization: " + str(init_data))
        
        # Short delay to ensure initialization broadcast is received
        wait(500)
        
        # Send ready status
        ready_data = (COMMAND_CHANNEL, HUB_NAME, 1, port_bits)
        hub.ble.broadcast(ready_data)
        print("Broadcasting ready status: " + str(ready_data))
        
        hub.light.on(Color.BLUE)
    except Exception as e:
        print("Error sending init status: " + str(e))
        hub.light.on(Color.RED)

def set_switch_position(motor, switch_name, position):
    """Set switch position using motor and update tracking"""
    motor.dc(70 if position else -70)
    wait(200)
    motor.brake()
    
    # Update position tracking
    switch_positions[switch_name] = position
    
    # Calculate status based on current positions
    status = 0
    for port, pos in switch_positions.items():
        if pos:
            status += 1 << (ord('D') - ord(port))
    
    send_status(status)
    print("Switch " + switch_name + " set to " + str(position))

def send_status(status_value):
    """
    Send status update with compact data format
    """
    try:
        # Calculate port connection status as binary
        port_connections = 0
        for port in ['A', 'B', 'C', 'D']:
            if port in active_ports:
                port_connections += 1 << (ord('D') - ord(port))
        
        # Format the data for BLE advertisement
        # First byte: Status channel (11)
        # Second byte: Status value
        # Third byte: Port connections
        status_data = (
            COMMAND_CHANNEL, # 1
            STATUS_CHANNEL,    # 11 (0x0B)
            status_value,      # Switch positions
            port_connections   # Port connections bitmap
        )
        
        hub.ble.broadcast(status_data)
        
        print(f"Broadcasting status: {status_data}")
        print(f"  - Switch positions (binary): {bin(status_value)[2:]:0>4}")
        print(f"  - Port connections (binary): {bin(port_connections)[2:]:0>4}")
        
    except Exception as e:
        print("Error sending status: " + str(e))
        hub.light.on(Color.RED)

def decode_command(data):
    """
    Decode the command data into switch and position
    Command format: XYYY where X is the switch number (1-4 for A-D)
                   and YYY is the position (0 or 1)
    """
    try:
        # Extract switch number (1-4 for A-D)
        switch_num = data // 1000
        # Convert switch number to port letter
        switch = chr(ord('A') + switch_num - 1)
        # Extract position (remainder after dividing by 1000)
        position = data % 2
        return switch, position
    except Exception as e:
        print("Error decoding command: " + str(e))
        return None, None

# Broadcast initial status
print("Hub started - Broadcasting initialization status...")
broadcast_init_status()
initial_status = 0  # Since all switches start in straight position (0)
print("Sending initial switch status...")
send_status(initial_status)
print("Motors initialized and ready for commands...")

while True:
    try:
        # Try to get any data on command channel
        data = hub.ble.observe(COMMAND_CHANNEL)
        
        # Only process if we got data AND it's different from last command
        if data is not None and data != last_command:
            print("Received raw data: " + str(data))
            
            # Decode the command
            if isinstance(data, int):
                switch, position = decode_command(data)
                if switch and switch in motors:
                    state = "DIVERGING" if position else "STRAIGHT"
                    print(f"Switch {switch} command: {state}")
                    
                    # Execute the command
                    set_switch_position(motors[switch], switch, position)
                    print("Command executed")
                    last_command = data
                else:
                    print(f"Ignoring command - Invalid switch or no motor on port {switch}")
                
        wait(100)
        
    except Exception as e:
        print("Error in main loop: " + str(e))
        wait(100)