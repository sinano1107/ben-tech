import asyncio
import bluetooth
import aioble
import time
from machine import Pin
import struct

# モーターのピン定義
MOTOR_PINS = {
    "IN1": 16,
    "IN2": 17,
    "IN3": 18,
    "IN4": 19
}

# Bluetooth設定の定数
BLE_CONFIG = {
    "SERVICE_UUID": bluetooth.UUID("00a8a81d-4125-410e-a5c3-62615319bcbd"),
    "CONTROL_CHAR_UUID": bluetooth.UUID("46898fe4-4b87-47c5-833f-6b9df8ca3b13"),
    "DEVICE_NAME": "BT-lid-controller",
    "ADVERTISE_INTERVAL": 100
}

# コマンド定義
COMMANDS = {
    "ROTATE": b"\x01",
    "COMPLETE": b"\x00"  # シンプルに1バイトの0を送信
}

class MotorController:
    """ステッピングモーター制御クラス"""
    
    SEQUENCE = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1]
    ]
    
    STEPS_PER_ROTATION = 512
    DEFAULT_DELAY = 0.001
    
    def __init__(self):
        self.pins = [
            Pin(MOTOR_PINS["IN1"], Pin.OUT),
            Pin(MOTOR_PINS["IN2"], Pin.OUT),
            Pin(MOTOR_PINS["IN3"], Pin.OUT),
            Pin(MOTOR_PINS["IN4"], Pin.OUT)
        ]
    
    def rotate(self, turns, clockwise=True, delay=DEFAULT_DELAY):
        steps = int(self.STEPS_PER_ROTATION * turns)
        sequence = self.SEQUENCE if clockwise else self.SEQUENCE[::-1]
        
        for _ in range(steps):
            for step in sequence:
                for pin, value in zip(self.pins, step):
                    pin.value(value)
                time.sleep(delay)
    
    def cleanup(self):
        for pin in self.pins:
            pin.value(0)

class BLEMotorServer:
    """Bluetoothモーター制御サーバー"""
    
    def __init__(self):
        self.led = Pin("LED", Pin.OUT)
        self.motor = MotorController()
        self.service = None
        self.char = None
        
    async def setup(self):
        self.service = aioble.Service(BLE_CONFIG["SERVICE_UUID"])
        self.char = aioble.Characteristic(
            self.service,
            BLE_CONFIG["CONTROL_CHAR_UUID"],
            read=True,
            write=True,
            write_no_response=True,
            capture=True,
            notify=True
        )
        aioble.register_services(self.service)
        self.led.off()
    
    async def start_advertising(self):
        connection = await aioble.advertise(
            BLE_CONFIG["ADVERTISE_INTERVAL"],
            name=BLE_CONFIG["DEVICE_NAME"],
            services=[BLE_CONFIG["SERVICE_UUID"]],
        )
        print("Connected to central")
        return connection
    
    async def handle_motor_command(self):
        print("Rotating clockwise...")
        self.motor.rotate(turns=1, clockwise=True)
        time.sleep(1)
        
        print("Rotating counter-clockwise...")
        self.motor.rotate(turns=1, clockwise=False)
    
    async def run(self):
        await self.setup()
        connection = await self.start_advertising()
        
        while connection.is_connected():
            try:
                written = await self.char.written() 
                if written is None:
                    continue
                    
                data = written[1]
                
                if data == COMMANDS["ROTATE"]:
                    try:
                        await self.handle_motor_command()
                        print("Sending completion notification (0)...")
                        await self.char.notify(connection, COMMANDS["COMPLETE"])
                        print("Notification sent")
                    finally:
                        self.motor.cleanup()
                else:
                    print(f"Unknown Command Received: {data}")
                    
            except Exception as e:
                print(f"Error in operation: {e}")
        
        print("Disconnected from Central")

async def main():
    server = BLEMotorServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
