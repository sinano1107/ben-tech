# BT-lid-controller
# TODO 開けている途中に閉じろと言われた時にすぐ閉じるようにする
# 現状では開き切ってから閉じる

import asyncio
import bluetooth
import aioble
import time
from machine import Pin


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

    # Bluetooth設定の定数
    BLE_CONFIG = {
        "SERVICE_UUID": bluetooth.UUID("ac6dd643-a32e-42fb-836d-8130790d9ab4"),
        "CONTROL_CHAR_UUID": bluetooth.UUID("74779bc7-1e28-4cb1-8dd7-3a3f2a9259ab"),
        "RESPONSE_CHAR_UUID": bluetooth.UUID("82bdb1a9-4ffd-4a97-8b5f-af7e84655133"),
        "DEVICE_NAME": "BT-lid-controller",
        "ADVERTISE_INTERVAL": 100,
    }

    # コマンド定義
    COMMANDS = {
        "LID_CLOSE": b"\x02",  # LIDを閉じる
        "LID_OPEN": b"\x01",  # LIDを開く
        "COMPLETE": b"\x01",  # 完了通知（closeのみ）
    }

    def __init__(self):
        self.led = Pin("LED", Pin.OUT)
        self.motor = MotorController()
        self.service = None
        self.control_char = None
        self.response_char = None

    async def setup(self):
        # 初期化中を知らせるためにLEDを点灯
        self.led.on()

        # serviceの生成
        self.service = aioble.Service(__class__.BLE_CONFIG["SERVICE_UUID"])

        # characteristicの生成
        self.control_char = aioble.Characteristic(
            self.service,
            __class__.BLE_CONFIG["CONTROL_CHAR_UUID"],
            read=True,
            write=True,
            write_no_response=True,
            capture=True,
        )
        self.response_char = aioble.Characteristic(
            self.service,
            __class__.BLE_CONFIG["RESPONSE_CHAR_UUID"],
            read=True,
            notify=True,
        )

        # サービスを登録
        aioble.register_services(self.service)

        # 初期化終了を知らせるためにLEDを消灯
        self.led.off()

    async def start_advertising(self):
        connection = await aioble.advertise(
            __class__.BLE_CONFIG["ADVERTISE_INTERVAL"],
            name=__class__.BLE_CONFIG["DEVICE_NAME"],
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
        if command == __class__.COMMANDS["LID_CLOSE"]:
            print("Closing lid...")
            # LIDを閉じる（時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=True)
            # close完了時のみ通知
            print("Sending close completion notification...")
            await self.response_char.notify(connection, __class__.COMMANDS["COMPLETE"])
            print("Close notification sent")

        elif command == __class__.COMMANDS["LID_OPEN"]:
            print("Opening lid...")
            # LIDを開く（反時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=False)
            print("Open operation completed")

        else:
            print(f"Unknown command: {command}")

    async def run(self):
        await self.setup()

        while True:
            connection = await self.start_advertising()
            print("接続されました")

            while connection.is_connected():
                try:
                    _, data = await self.control_char.written(timeout_ms=1000)

                    try:
                        # LID制御を実行
                        await self.handle_lid_command(data, connection)
                    finally:
                        self.motor.cleanup()
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    print(f"Error in operation: {e}")

            print("Disconnected from Central")

async def main():
    controller = BLELidController()
    await controller.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
