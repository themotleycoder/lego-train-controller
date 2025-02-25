#!/usr/bin/env python3
import asyncio
import subprocess

from controllers.switch_controller import SwitchController
from controllers.train_controller import TrainController
from servers.bluetooth_scanner import BetterBleScanner
from utils.constants import TRAIN_COMMAND

class LegoController:
    def __init__(self):
        self.switch_controller = SwitchController()
        self.train_controller = TrainController()
        self.running = True

    async def initialize(self):
        """Async initialization method"""
        await self.switch_controller.scanner.reset_bluetooth()

    def extract_number_and_command(self, s: str) -> tuple[int, str]:
        # Find all digits at the start of the string
        number = ''
        pos = 0
        for char in s:
            if char.isdigit():
                number += char
                pos += 1
            else:
                break
                
        # Get remaining string starting from where numbers ended
        command = s[pos:]
        
        return int(number) if number else 0, command

    async def run(self):
        """Main run loop with proper task management"""
        print("Starting Lego Controller...")
        self.switch_controller.scanner.reset_bluetooth()
        # self.train_controller.reset_bluetooth()
        
        try:
            # Create tasks for status monitoring
            switch_monitor_task = asyncio.create_task(self.switch_controller.start_status_monitoring())
            train_monitor_task = asyncio.create_task(self.train_controller.start_status_monitoring())
            
            print("\nCommands:")
            print("as: Switch A to STRAIGHT")
            print("ad: Switch A to DIVERGING")
            print("bs: Switch B to STRAIGHT")
            print("bd: Switch B to DIVERGING")
            print("\nTrain Commands:")
            print("ts: Stop train")
            print("tf[power]: Forward (optional power 0-100, e.g. tf50)")
            print("tb[power]: Backward (optional power 0-100, e.g. tb75)")
            print("r: Reset Bluetooth")
            print("q: Quit")
            
            while self.running:
                try:
                    # Use asyncio.create_task for input to prevent blocking
                    cmd = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
                    
                    hub, cmd = self.extract_number_and_command(cmd)

                    if cmd.lower() == 'q':
                        self.running = False
                    elif cmd.lower() == 'r':
                        await self.switch_controller.stop_status_monitoring()
                        await self.train_controller.stop_status_monitoring()
                        self.switch_controller.scanner.reset_bluetooth()
                        self.train_controller.reset_bluetooth()
                        switch_monitor_task.cancel()  # Cancel old monitoring tasks
                        train_monitor_task.cancel()
                        switch_monitor_task = asyncio.create_task(self.switch_controller.start_status_monitoring())
                        train_monitor_task = asyncio.create_task(self.train_controller.start_status_monitoring())
                    elif cmd.lower() == 'as':
                        await self.switch_controller.send_command_with_retry(hub, "SWITCH_A", 0)
                    elif cmd.lower() == 'ad':
                        await self.switch_controller.send_command_with_retry(hub, "SWITCH_A", 1)
                    elif cmd.lower() == 'bs':
                        await self.switch_controller.send_command_with_retry(hub, "SWITCH_B", 0)
                    elif cmd.lower() == 'bd':
                        await self.switch_controller.send_command_with_retry(hub, "SWITCH_B", 1)
                    elif cmd.lower().startswith('ts'):
                        await self.train_controller.send_command_with_retry(hub, TRAIN_COMMAND["STOP"])
                    elif cmd.lower().startswith('tf'):
                        # Extract power value if provided (e.g. tf50)
                        power = int(cmd[2:]) if len(cmd) > 2 and cmd[2:].isdigit() else 40
                        await self.train_controller.send_command_with_retry(hub, TRAIN_COMMAND["FORWARD"], power)
                    elif cmd.lower().startswith('tb'):
                        # Extract power value if provided (e.g. tb75)
                        power = int(cmd[2:]) if len(cmd) > 2 and cmd[2:].isdigit() else 40
                        await self.train_controller.send_command_with_retry(hub, TRAIN_COMMAND["BACKWARD"], power)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Error processing command: {e}")
                    
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Clean up
            self.running = False
            await self.switch_controller.stop_status_monitoring()
            await self.train_controller.stop_status_monitoring()
            if 'switch_monitor_task' in locals():
                switch_monitor_task.cancel()
            if 'train_monitor_task' in locals():
                train_monitor_task.cancel()
            subprocess.run(["sudo", "hcitool", "cmd", "0x08", "0x000A", "00"])

if __name__ == "__main__":
    asyncio.run(LegoController().run())
