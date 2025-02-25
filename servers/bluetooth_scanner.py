#!/usr/bin/env python3
import asyncio
import time
from bleak import BleakScanner
import subprocess

class BetterBleScanner:
    def __init__(self):
        self.scanner = None
        self._scanning = False
        self._lock = asyncio.Lock()  # Add lock for thread safety
    
    async def start_scan(self, callback):
        """Start a new scan with forced cleanup"""
        async with self._lock:  # Use lock to prevent concurrent scans
            try:
                if self._scanning:
                    print("Scanner already running, stopping first...")
                    await self.stop_scan()
                    await asyncio.sleep(1)  # Give time for cleanup
                
                print("Resetting Bluetooth...")
                await self.reset_bluetooth()
                await asyncio.sleep(1)  # Wait for reset

                print("Creating new scanner...")
                self.scanner = BleakScanner(callback)
                print("Starting scan...")
                await self.scanner.start()
                self._scanning = True
                print("Scanning started successfully")
                
            except Exception as e:
                print(f"Error starting scan: {e}")
                self._scanning = False
                self.scanner = None
                raise
    
    async def stop_scan(self):
        """Stop scanning with forced cleanup"""
        async with self._lock:
            if self.scanner and self._scanning:
                try:
                    print("Stopping scanner...")
                    await self.scanner.stop()
                    self._scanning = False
                    self.scanner = None
                    print("Scanner stopped successfully")
                except Exception as e:
                    print(f"Warning - error stopping scanner: {e}")
                finally:
                    self._scanning = False
                    self.scanner = None

    async def reset_bluetooth(self):
        """Reset Bluetooth to a known state"""
        try:
            print("\nResetting Bluetooth...")
            
            # Simple reset using bluetoothctl
            commands = [
                ["sudo", "bluetoothctl", "power", "off"],
                ["sudo", "bluetoothctl", "power", "on"]
            ]
            
            for cmd in commands:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    await asyncio.sleep(0.5)  # Longer delay between commands
                except subprocess.CalledProcessError as e:
                    print(f"Warning - command {cmd} failed: {e}")
                    continue
                    
            print("Bluetooth reset complete")
        except Exception as e:
            print(f"Error during Bluetooth reset: {e}")
            raise

    @property
    def is_scanning(self):
        """Check if currently scanning"""
        return self._scanning and self.scanner is not None
