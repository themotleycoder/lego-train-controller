import asyncio
import subprocess
import time
import struct
from servers.bluetooth_scanner import BetterBleScanner
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TrainController:
    def __init__(self):
        self.command_number = 0x01
        self.scanner = BetterBleScanner()
        self.running = True
        self.train_statuses = {}
        self.last_update_times = {}
        self.train_channels = {}
        self._active_trains = set()  # Track active trains
        self._train_self_drive = {}  # Track self-drive state for each train
        # Add command queue for better performance
        self.command_queue = asyncio.Queue()
        self.command_task = None

    def register_train(self, hub_id: int, command_channel: int):
        """Register a train and its command channel"""
        self.train_channels[hub_id] = command_channel
        logger.info(f"Registered train {hub_id} on command channel {command_channel}")

    def get_train_channel(self, hub_id: int) -> int:
        """Get the command channel for a specific train"""
        if hub_id not in self.train_channels:
            raise ValueError(
                f"Train {hub_id} not registered. Please register train with command channel first."
            )
        return self.train_channels[hub_id]

    def reset_bluetooth(self):
        """Reset Bluetooth to a known state"""
        self.scanner.reset_bluetooth()

    def mark_train_active(self, hub_id):
        """Mark a train as active for more frequent updates"""
        self._active_trains.add(hub_id)

    def mark_train_inactive(self, hub_id):
        """Mark a train as inactive"""
        self._active_trains.discard(hub_id)

    async def _mark_inactive_later(self, hub_id):
        """Mark train as inactive after delay"""
        await asyncio.sleep(5)
        self.mark_train_inactive(hub_id)

    async def start_status_monitoring(self):
        """Start monitoring for status updates from trains"""

        async def status_callback(device, advertisement_data):
            try:
                if device.name and "Train" in device.name:
                    if 919 in advertisement_data.manufacturer_data:
                        data = advertisement_data.manufacturer_data[919]

                        try:
                            # Get listening channel from data
                            listening_channel = int(data[2])
                            hub_id = listening_channel

                            # Auto-register using listening channel
                            if hub_id not in self.train_channels:
                                logger.info(
                                    f"Auto-registering train {hub_id} using channel {listening_channel}"
                                )
                                self.register_train(hub_id, listening_channel)

                            current_time = time.time()
                            last_update = self.last_update_times.get(hub_id, 0)

                            # More frequent updates for active trains
                            update_threshold = (
                                0.1 if hub_id in self._active_trains else 0.5
                            )
                            if current_time - last_update >= update_threshold:
                                status_value = data[-2]
                                current_power = struct.unpack("b", bytes([data[-1]]))[0]

                                self.train_statuses[hub_id] = {
                                    "status": (
                                        "running" if status_value > 0 else "stopped"
                                    ),
                                    "speed": current_power,
                                    "direction": (
                                        "forward" if current_power >= 0 else "backward"
                                    ),
                                    "connected": True,
                                    "timestamp": current_time,
                                    "name": device.name,
                                    "selfDrive": self._train_self_drive.get(
                                        hub_id, False
                                    ),
                                    "rssi": advertisement_data.rssi,
                                    "channel": listening_channel,
                                }
                                self.last_update_times[hub_id] = current_time
                                logger.debug(
                                    f"Updated status for train {hub_id}: {self.train_statuses[hub_id]}"
                                )

                        except Exception as e:
                            logger.error(
                                f"Error processing hub data: {e}", exc_info=True
                            )
                            import traceback

                            traceback.print_exc()

            except Exception as e:
                logger.error(f"Error in status callback: {e}", exc_info=True)
                import traceback

                traceback.print_exc()

        logger.info("Starting train status monitoring...")
        self.command_task = asyncio.create_task(self._process_commands())

        while self.running:
            try:
                logger.debug("Setting up scanner...")
                await self.scanner.start_scan(status_callback)
                logger.debug("Scanner started, waiting for events...")

                while self.running:
                    await asyncio.sleep(
                        0.05
                    )  # Reduced sleep time for better responsiveness

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
                logger.info("Waiting before retry...")
                await asyncio.sleep(1)  # Reduced retry delay
            finally:
                await self.scanner.stop_scan()

    async def _process_commands(self):
        """Background task to process commands from queue with batching"""
        while self.running:
            try:
                # Get all pending commands (up to 5)
                commands = []
                try:
                    while len(commands) < 5:
                        command = self.command_queue.get_nowait()
                        commands.append(command)
                except asyncio.QueueEmpty:
                    if not commands:
                        # If no commands, wait for the next one
                        commands.append(await self.command_queue.get())

                # Process all collected commands
                for command in commands:
                    await self._execute_command(command)
                    self.command_queue.task_done()

                # Small delay between batches
                await asyncio.sleep(0.02)

            except Exception as e:
                logger.error(f"Error processing command batch: {e}", exc_info=True)

    async def _execute_command(self, command):
        """Execute a single command"""
        hub_id, value_bytes = command  # Now only expecting 2 values
        try:
            command_channel = self.get_train_channel(hub_id)

            payload = (
                bytes([0x08, 0xFF, 0x97, 0x03, command_channel, 0x00, 0x61])
                + value_bytes
            )

            # Create a single combined HCI command string
            hci_commands = [
                # Stop advertising
                ["sudo", "hcitool", "cmd", "0x08", "0x000A", "00"],
                # Set advertising parameters - reduced interval for faster response
                [
                    "sudo",
                    "hcitool",
                    "cmd",
                    "0x08",
                    "0x0006",
                    "32",
                    "00",  # 50ms interval (faster than 100ms but still reliable)
                    "32",
                    "00",  # Same interval
                    "03",  # non-connectable
                    "00",
                    "00",
                    "00",
                    "00",
                    "00",
                    "00",
                    "00",
                    "00",
                    "07",
                    "00",
                ],
                # Set advertising data
                ["sudo", "hcitool", "cmd", "0x08", "0x0008"]
                + [format(len(payload), "x")]
                + [format(b, "02x") for b in payload],
                # Start advertising
                ["sudo", "hcitool", "cmd", "0x08", "0x000A", "01"],
            ]

            # Execute commands with minimal delays
            for cmd in hci_commands:
                subprocess.run(cmd, capture_output=True)
                await asyncio.sleep(0.02)  # Minimal delay between commands

            # Channel-specific handling
            if command_channel == 22:
                # Extra time for channel 22 which needs it
                await asyncio.sleep(0.1)
                # Send a second pulse for reliability
                subprocess.run(hci_commands[-2], capture_output=True)  # Resend data
                subprocess.run(
                    hci_commands[-1], capture_output=True
                )  # Restart advertising
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            raise

    async def handle_command(self, hub_id: int, power: int):
        """Queue a power command for processing"""
        try:
            if hub_id not in self.train_statuses:
                available_trains = list(self.train_statuses.keys())
                raise ValueError(
                    f"Train {hub_id} not found. Available trains: {available_trains}"
                )

            logger.info(f"Setting train {hub_id} power to: {power}%")
            self.mark_train_active(hub_id)
            # Encode power commands as values from -100 to 100
            clamped_power = max(min(power, 100), -100)
            value_bytes = struct.pack("b", clamped_power)
            await self.command_queue.put((hub_id, value_bytes))

            asyncio.create_task(self._mark_inactive_later(hub_id))

        except Exception as e:
            logger.error(f"Error queueing train command: {e}", exc_info=True)
            import traceback

            traceback.print_exc()
            raise

    async def handle_drive_command(self, hub_id: int, self_drive: int = 0):
        """Queue a self-drive command for processing"""
        try:
            if hub_id not in self.train_statuses:
                available_trains = list(self.train_statuses.keys())
                raise ValueError(
                    f"Train {hub_id} not found. Available trains: {available_trains}"
                )

            logger.info(f"Setting train {hub_id} self drive to: {self_drive}")
            self.mark_train_active(hub_id)
            # Update self-drive state in our tracking dictionary
            self._train_self_drive[hub_id] = bool(self_drive)
            # Encode self-drive commands as values above 100 (e.g., 101 for on, 102 for off)
            value = 101 if self_drive else 102
            value_bytes = struct.pack("b", value)
            await self.command_queue.put((hub_id, value_bytes))

            asyncio.create_task(self._mark_inactive_later(hub_id))

        except Exception as e:
            logger.error(f"Error queueing train command: {e}", exc_info=True)
            import traceback

            traceback.print_exc()
            raise

    def get_connected_trains(self):
        """Return information about all connected trains"""
        try:
            current_time = time.time()
            connected_trains = {}

            for hub_id, status in self.train_statuses.items():
                try:
                    timestamp = float(status.get("timestamp", 0))
                    last_update = current_time - timestamp

                    if last_update < 5:
                        connected_trains[hub_id] = {
                            "status": status.get("status", "unknown"),
                            "speed": status.get("speed", 0),
                            "direction": status.get("direction", "unknown"),
                            "name": status.get("name", f"Train {hub_id}"),
                            "selfDrive": self._train_self_drive.get(hub_id, False),
                            "last_update_seconds_ago": round(last_update, 2),
                            "rssi": status.get("rssi", 0),
                            "channel": status.get("channel"),  # Include channel info
                            "active": hub_id
                            in self._active_trains,  # Include active status
                        }
                except Exception as e:
                    logger.error(f"Error processing train {hub_id}: {e}", exc_info=True)
                    continue

            return connected_trains
        except Exception as e:
            logger.error(f"Error in get_connected_trains: {e}", exc_info=True)
            return {}

    async def stop_status_monitoring(self):
        """Stop monitoring for status updates"""
        logger.info("Stopping train status monitoring...")
        self.running = False
        await self.scanner.stop_scan()
        logger.info("Train monitor stopped")
