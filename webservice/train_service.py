#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import time
from servers.main import LegoController

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize controller
controller = LegoController()

@app.on_event("startup")
async def startup_event():
    """Initialize the controller when the FastAPI app starts"""
    print("Starting up FastAPI server...")
    await controller.initialize()
    
    # Start monitoring in background task
    controller.running = True
    asyncio.create_task(controller.train_controller.start_status_monitoring())
    asyncio.create_task(controller.switch_controller.start_status_monitoring())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when server shuts down"""
    print("Shutting down server...")
    controller.running = False
    await controller.train_controller.stop_status_monitoring()
    await asyncio.sleep(1)  # Give time for cleanup

async def run_single_monitor():
    """Run a single monitoring instance"""
    while True:
        try:
            print("Starting monitoring...")
            # Start only the train monitoring (since it uses the same BLE scanner)
            await controller.train_controller.start_status_monitoring()
            await controller.switch_controller.start_status_monitoring()
        except Exception as e:
            print(f"Monitor error: {e}")
            # Wait before retrying
            await asyncio.sleep(5)

class TrainCommand(BaseModel):
    hub_id: int = 0
    command: str
    power: Optional[int] = 40

class SwitchCommand(BaseModel):
    hub_id: int = 0
    switch: str  # "A" or "B"
    position: str  # "STRAIGHT" or "DIVERGING"

class TrainPowerCommand(BaseModel):
    hub_id: int
    power: int = Field(..., ge=-100, le=100)  # Ensures power is between -100 and 100

class TrainDriveCommand(BaseModel):
    hub_id: int
    self_drive: int   # self drive is 1, manual drive is 0    

@app.post("/selfdrive")
async def control_train(command: TrainDriveCommand):
    try:
        await controller.train_controller.handle_drive_command(command.hub_id, command.self_drive)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train")
async def control_train(command: TrainPowerCommand):
    try:
        await controller.train_controller.handle_command(command.hub_id, command.power)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/switch")
async def control_switch(command: SwitchCommand):
    try:
        # Convert switch letter to number (1-4 for A-D)
        switch_num = ord(command.switch) - ord('A') + 1
        # Create command value: XYYY where X is switch number and YYY includes position
        position = 1 if command.position == "DIVERGING" else 0
        
        # Send the command to the switch controller
        await controller.switch_controller.send_command_with_retry(
            command.hub_id,
            f"SWITCH_{command.switch}",  # Keep the SWITCH_ prefix for compatibility
            position
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/connected/trains")
async def get_connected_trains():
    try:
        # Add error handling for controller access
        if not controller or not controller.train_controller:
            raise HTTPException(
                status_code=503,
                detail="Train controller not initialized"
            )
            
        connected_trains = controller.train_controller.get_connected_trains()
        
        return {
            "connected_trains": len(connected_trains),
            "trains": connected_trains
        }
    except Exception as e:
        print(f"Error in get_connected_trains endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
@app.get("/connected/switches", 
    description="Get information about all connected switch hubs",
    response_description="""Returns a dictionary with:
    - connected_switches: Number of connected switch hubs
    - switches: Dictionary of switch hub data, where each hub contains:
        - switch_positions: Current position of each switch (0=STRAIGHT, 1=DIVERGING)
        - last_update_seconds_ago: Time since last status update
        - name: Hub name
        - status: Raw status byte
        - connected: Connection status
        - active: Whether hub is currently active
        - port_connections: Binary representation of connected motor ports
    """
)
async def get_connected_switches():
    try:
        connected_switches = controller.switch_controller.get_connected_switches()
        
        return {
            "connected_switches": len(connected_switches),
            "switches": connected_switches
        }
    except Exception as e:
        print(f"Error checking switch connections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
async def reset_bluetooth():
    try:
        controller.switch_controller.scanner.reset_bluetooth()
        controller.train_controller.reset_bluetooth()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
