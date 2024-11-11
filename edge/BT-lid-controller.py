# BT-lid-controller

import asyncio
import bluetooth
import aioble
import time
from machine import Pin

# Bluetooth設定の定数
BLE_CONFIG = {
    "SERVICE_UUID": bluetooth.UUID("00a8a81d-4125-410e-a5c3-62615319bcbd"),
    "CONTROL_CHAR_UUID": bluetooth.UUID("46898fe4-4b87-47c5-833f-6b9df8ca3b13"),
    "DEVICE_NAME": "BT-lid-controller",
    "ADVERTISE_INTERVAL": 100
}

# コマンド定義
COMMANDS = {
    "LID_CLOSE": b"\x02",  # LIDを閉じる
    "LID_OPEN": b"\x01",   # LIDを開く
    "COMPLETE": b"\x01"    # 完了通知（closeのみ）
}

class MotorController:
    """ステッピングモーター制御クラス"""

    # モーターのピン定義
    MOTOR_PINS = {
        "IN1": 16,
        "IN2": 17,
        "IN3": 18,
        "IN4": 19,
    }

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
    DEFAULT_TURNS = 4  # デフォルトの回転数

    def __init__(self):
        self.pins = [
            Pin(__class__.MOTOR_PINS["IN1"], Pin.OUT),
            Pin(__class__.MOTOR_PINS["IN2"], Pin.OUT),
            Pin(__class__.MOTOR_PINS["IN3"], Pin.OUT),
            Pin(__class__.MOTOR_PINS["IN4"], Pin.OUT),
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

class BLELidController:
    """Bluetooth LID制御サーバー"""
    
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

    async def handle_lid_command(self, command, connection):
        """
        LIDの開閉制御
        Args:
            command: 受信したコマンド
            connection: BLE接続オブジェクト
        """
        if command == COMMANDS["LID_CLOSE"]:
            print("Closing lid...")
            # LIDを閉じる（時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=True)
            # close完了時のみ通知
            print("Sending close completion notification...")
            await self.char.notify(connection, COMMANDS["COMPLETE"])
            print("Close notification sent")
            
        elif command == COMMANDS["LID_OPEN"]:
            print("Opening lid...")
            # LIDを開く（反時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=False)
            print("Open operation completed")
            
        else:
            print(f"Unknown command: {command}")
    
    async def run(self):
        await self.setup()
        connection = await self.start_advertising()
        
        while connection.is_connected():
            try:
                written = await self.char.written()
                if written is None:
                    continue
                    
                data = written[1]
                
                try:
                    # LID制御を実行
                    await self.handle_lid_command(data, connection)
                finally:
                    self.motor.cleanup()
                    
            except Exception as e:
                print(f"Error in operation: {e}")
        
        print("Disconnected from Central")

async def main():
    controller = BLELidController()
    await controller.run()

if __name__ == "__main__":
    asyncio.run(main())
