from pybricks.hubs import CityHub
from pybricks.pupdevices import DCMotor, ColorDistanceSensor
from pybricks.parameters import Port, Color
from pybricks.tools import StopWatch, wait

# Constants
COMMAND_CHANNEL = 21
STATUS_CHANNEL = 12

MOTOR_SPEED = 50  # Power in %
CHECK_INTERVAL = 50  # Time between color checks in ms
BROADCAST_INTERVAL = 2000  # Time between status broadcasts in ms
TRAIN_NAME = "TRAIN HUB 1"

# What mode is the train running in?
SELF_DRIVING = False
SELF_DRIVE_POWER = 50

processed_commands = set()
broadcast_timer = StopWatch()

# Train commands
TRAIN_COMMAND = {"STOP": 0, "FORWARD_UNTIL_PATTERN": 1, "BACKWARD_UNTIL_PATTERN": 2}

# Clear terminal output
print("\x1b[H\x1b[2J", end="")

# Initialize hub and motor
hub = CityHub(broadcast_channel=STATUS_CHANNEL, observe_channels=[COMMAND_CHANNEL])
motor = DCMotor(Port.A)
sensor = ColorDistanceSensor(Port.B)
print("Hub, sensor and motor initialized!")

# Get hub identifiers once at startup
HUB_NAME = hub.system.name()
print(f"Hub name: {HUB_NAME}")
print(f"Hub ID: {COMMAND_CHANNEL}")

Color.BLUE = Color(h=216, s=79, v=5)
Color.GREEN = Color(h=90, s=60, v=3)
Color.YELLOW = Color(h=49, s=87, v=9)
Color.RED = Color(h=350, s=88, v=5)
Color.GRAY = Color(h=0, s=30, v=3)
our_colors = (
    Color.RED,
    Color.YELLOW,
    Color.GREEN,
    Color.BLUE,
    Color.GRAY,
    Color.WHITE,
    Color.NONE,
)
sensor.detectable_colors(our_colors)

# Color codes (3 bits)
TRAIN_COLOR_CODES = {
    Color.NONE: 0,
    Color.RED: 1,
    Color.YELLOW: 2,
    Color.GREEN: 3,
    Color.BLUE: 4,
    Color.GRAY: 5,
    Color.WHITE: 6,
}

TRAIN_COLOR_FROM_CODE = {code: color for color, code in TRAIN_COLOR_CODES.items()}

VALID_PATTERN_COLORS = {Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE}


def is_valid_color(color):
    """Check if a color is valid for pattern matching"""
    return color in VALID_PATTERN_COLORS


def handle_command(cmd):
    """Process commands for both manual and self-driving modes

    Args:
        cmd: Either a tuple (in self-driving mode) or an integer (in manual mode)
    """
    try:
        # print(f"Received command: {cmd}")

        if not SELF_DRIVING:
            # Manual mode - expect single integer for power
            if not isinstance(cmd, (int, float)):
                print("Invalid command type for manual mode")
                return False

            power = int(cmd)
            if -100 <= power <= 100:
                motor.dc(power)
                print(f"Motor power set to {power}%")
                return True
            else:
                print(f"Invalid power value: {power}")
                return False
        else:
            # Self-driving mode - expect tuple/list with command structure
            if not isinstance(cmd, (list, tuple)):
                print("Invalid command type for self-driving mode")
                return False

            if len(cmd) < 3:
                print("Command too short")
                return False

            command_number = cmd[0]
            device_name = cmd[1]
            command_type = cmd[2]
            # print(f"Command type: {command_type}")

            if command_type == TRAIN_COMMAND["STOP"]:
                motor.brake()
                processed_commands.add(command_number)
                return True

            elif command_type in [
                TRAIN_COMMAND["FORWARD_UNTIL_PATTERN"],
                TRAIN_COMMAND["BACKWARD_UNTIL_PATTERN"],
            ]:
                if len(cmd) >= 4:  # Has pattern length
                    pattern_length = cmd[3]
                    if len(cmd) >= 4 + pattern_length:  # Has full pattern
                        pattern = list(cmd[4 : 4 + pattern_length])
                        direction = (
                            1
                            if command_type == TRAIN_COMMAND["FORWARD_UNTIL_PATTERN"]
                            else -1
                        )
                        processed_commands.add(command_number)
                        move_until_pattern(direction, pattern)
                        return True

                print("Pattern incomplete")
                return False

            print("Unknown command type")
            return False

    except Exception as e:
        print(f"Error in handle_command: {e}")
        return False


print("Train control ready! Listening for commands...")


def consolidate_colors(color_history, min_repeats=2):
    """
    Convert a list of colors into a stable pattern by removing outliers.
    A color must be seen min_repeats times to be considered real.
    Returns list of colors with outliers removed.
    """
    if not color_history:
        return []

    # Group consecutive same colors
    groups = []
    current_color = color_history[0]
    current_count = 1

    for color in color_history[1:]:
        if color == current_color:
            current_count += 1
        else:
            groups.append((current_color, current_count))
            current_color = color
            current_count = 1
    groups.append((current_color, current_count))

    # Keep only colors that appear enough times
    stable_colors = []
    for color, count in groups:
        if count >= min_repeats:
            if not stable_colors or stable_colors[-1] != color:
                stable_colors.append(color)

    return stable_colors


def move_until_pattern(direction, pattern_codes):
    """
    Move train in specified direction until color pattern is found
    direction: 1 for forward, -1 for backward
    pattern_codes: list of color codes to look for in sequence
    """
    movement = "FORWARD" if direction > 0 else "BACKWARD"
    pattern = [TRAIN_COLOR_FROM_CODE[code] for code in pattern_codes]
    print(f"{TRAIN_NAME}: Moving {movement} until pattern {pattern} detected...")

    motor.dc(direction * MOTOR_SPEED)
    seen_colors = []
    # broadcast_status(movement, pattern_codes)

    while True:
        # Check for new commands (especially STOP)
        cmd = hub.ble.observe(COMMAND_CHANNEL)
        if cmd:
            if handle_command(cmd):  # Returns True if we should stop
                return False

        if sensor.distance() < 15:
            current_color = sensor.color()
            if is_valid_color(current_color):
                seen_colors.append(current_color)
                if len(seen_colors) > len(pattern) * 4:
                    seen_colors.pop(0)

                stable_pattern = consolidate_colors(seen_colors)
                print(f"Stable pattern: {stable_pattern}")

                if len(stable_pattern) >= len(pattern):
                    if tuple(stable_pattern[-len(pattern) :]) == tuple(pattern):
                        print(f"Found pattern {pattern}!")
                        motor.brake()
                        # broadcast_status("STOPPED", pattern_codes)
                        send_status()
                        return True

        if broadcast_timer.time() >= BROADCAST_INTERVAL:
            # broadcast_status(movement, pattern_codes)
            send_status()

        wait(CHECK_INTERVAL)


# Status reporting
def send_status():
    """Send status update to server including hub name and ID"""
    try:
        # Status value (1 = connected/running)
        status_value = 1

        current_color = sensor.color()

        # Create a tuple with (hub_id, hub_name, status_value, 0)
        # The receiving end will get this as a tuple of (str, str, int, int)
        status_data = (COMMAND_CHANNEL, HUB_NAME, status_value, 0)
        hub.ble.broadcast(status_data)
        # print(f"Broadcasting status: {status_data}")

    except Exception as e:
        print(f"Error sending status: {e}")


COMMAND_LIST = [
    (1, "train1", TRAIN_COMMAND["FORWARD_UNTIL_PATTERN"], 1, 1),  # Forward until 2 reds
    (2, "train1", TRAIN_COMMAND["STOP"]),  # Stop
    (
        3,
        "train1",
        TRAIN_COMMAND["FORWARD_UNTIL_PATTERN"],
        1,
        2,
    ),  # Forward until 2 yellows
    (4, "train1", TRAIN_COMMAND["STOP"]),  # Stop
    (
        5,
        "train1",
        TRAIN_COMMAND["BACKWARD_UNTIL_PATTERN"],
        1,
        4,
    ),  # Backward until 2 blues
    (6, "train1", TRAIN_COMMAND["STOP"]),
    (7, "train1", TRAIN_COMMAND["FORWARD_UNTIL_PATTERN"], 1, 1),  # Forward until 2 reds
    (8, "train1", TRAIN_COMMAND["STOP"]),  # Final stop
]

command_index = 0
last_command_time = StopWatch()

# Main loop - listen for commands and send status
while True:
    try:
        cmd = hub.ble.observe(COMMAND_CHANNEL)
        if cmd is not None:
            print(f"Received value: {cmd}")

            if cmd == 101:
                # Self-drive ON command
                print("Starting self drive")
                SELF_DRIVING = True
                # Start the motor at the self-drive power
                motor.dc(SELF_DRIVE_POWER)
            elif cmd == 102:
                # Self-drive OFF command
                print("Stopping self drive")
                SELF_DRIVING = False
                # Stop the motor when exiting self-drive mode
                motor.brake()
            else:
                # Regular power command (-100 to 100)
                # train_motor.dc(cmd)
                print(f"Set motor power to {cmd}")
                handle_command(cmd)

        # Color scanning logic - active in self-driving mode
        if SELF_DRIVING and sensor.distance() < 12:
            current_color = sensor.color()
            distance = sensor.distance()
            hsv = sensor.hsv()

            print(f"Self-driving - detected color: {current_color}")
            print(f"Distance: {distance}")
            print(f"HSV: {hsv}")

            if is_valid_color(current_color):
                print(f"Valid color detected: {current_color}")
                # Here you can add specific behaviors for different colors
                # For example:
                if current_color == Color.RED:
                    motor.brake()
                    wait(1000)
                    motor.dc(SELF_DRIVE_POWER)

        # Send status update
        send_status()

    except Exception as e:
        print(f"Error in main loop: {e}")
        wait(1000)
        continue

    wait(50)  # Short delay to prevent busy-waiting
