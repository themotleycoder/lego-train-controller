"""
LEGO Control Server Package

This package provides functionality for controlling LEGO Powered Up devices via Bluetooth:
- Switch control for train track switches
- Basic train control (stop, forward, backward)
- Bluetooth scanning and communication
"""

from utils.constants import TRAIN_COMMAND, COMMAND_CHANNEL, LEGO_MANUFACTURER_IDS
from .bluetooth_scanner import BetterBleScanner
from .main import LegoController

__all__ = [
    'TRAIN_COMMAND',
    'COMMAND_CHANNEL',
    'LEGO_MANUFACTURER_IDS',
    'BetterBleScanner',
    'LegoController'
]
