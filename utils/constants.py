#!/usr/bin/env python3

# Train command constants
TRAIN_COMMAND = {
    "STOP": 0,
    "FORWARD": 1,
    "BACKWARD": 2
}

# Bluetooth constants
LEGO_MANUFACTURER_IDS = [919, 0x397]  # LEGO manufacturer ID can be either 919 (0x0397) or 0x397
COMMAND_CHANNEL = 21  # Channel for train commands
