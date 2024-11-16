# BT-auto-flusher

import asyncio
import bluetooth
import time
from machine import Pin
from common import BenTechDeviceServer


class MotorController:
    """ステッピングモーター制御クラス"""

    # モーターのピン定義
    MOTOR_PINS = {"IN1": 16, "IN2": 17, "IN3": 18, "IN4": 19}

    SEQUENCE = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1],
    ]

    STEPS_PER_ROTATION = 512
    DEFAULT_DELAY = 0.001

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

        try:
            for _ in range(steps):
                for step in sequence:
                    for pin, value in zip(self.pins, step):
                        pin.value(value)
                    time.sleep(delay)
        finally:
            self.cleanup()

    def cleanup(self):
        for pin in self.pins:
            pin.value(0)


class AutoFlusher(BenTechDeviceServer):
    """自動水洗アタッチメントのサーバー"""

    COMMANDS = {"FLUSH": b"\x01"}

    def __init__(self):
        super().__init__(
            name="BT-auto-flusher",
            service_id=bluetooth.UUID("6408f4f4-5002-4787-8c6f-c44147b06802"),
            control_char_id=bluetooth.UUID("f36a79b8-f196-4975-8e53-15ed99efa275"),
        )
        self.motor = MotorController()

    async def _handle_motor_command(self):
        print("Rotating clockwise...")
        self.motor.rotate(turns=0.75, clockwise=False)
        await asyncio.sleep(1)

        print("Rotating counter-clockwise...")
        self.motor.rotate(turns=0.75, clockwise=True)

        print("complete")

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["FLUSH"]:
            await self._handle_motor_command()
        else:
            print(f"Unknown Command Received: {command}")


async def main():
    server = AutoFlusher()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
