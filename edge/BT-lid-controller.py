# BT-lid-controller
# TODO 開けている途中に閉じろと言われた時にすぐ閉じるようにする
# 現状では開き切ってから閉じる

import asyncio
import bluetooth
import time
from machine import Pin
from common import BenTechResponsiveDeviceServer


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


class BenTechLidController(BenTechResponsiveDeviceServer):
    """Bentech 蓋開閉機"""

    # コマンド定義
    COMMANDS = {
        "LID_CLOSE": b"\x02",  # LIDを閉じる
        "LID_OPEN": b"\x01",  # LIDを開く
        "COMPLETE": b"\x01",  # 完了通知（closeのみ）
    }

    def __init__(self):
        super().__init__(
            name="BT-lid-controller",
            service_id=bluetooth.UUID("ac6dd643-a32e-42fb-836d-8130790d9ab4"),
            control_char_id=bluetooth.UUID("74779bc7-1e28-4cb1-8dd7-3a3f2a9259ab"),
            response_char_id=bluetooth.UUID("82bdb1a9-4ffd-4a97-8b5f-af7e84655133"),
        )
        self.motor = MotorController()

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["LID_CLOSE"]:
            print("Closing lid...")
            # LIDを閉じる（時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=True)
            # close完了時のみ通知
            print("Sending close completion notification...")
            await self._notify_response(__class__.COMMANDS["COMPLETE"])
            print("Close notification sent")
        elif command == __class__.COMMANDS["LID_OPEN"]:
            print("Opening lid...")
            # LIDを開く（反時計回り）
            self.motor.rotate(turns=self.motor.DEFAULT_TURNS, clockwise=False)
            print("Open operation completed")
        else:
            print(f"Unknown command: {command}")


async def main():
    controller = BenTechLidController()
    await controller.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
