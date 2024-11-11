# BT-deodorant

import asyncio
import bluetooth
from machine import Pin, PWM
from common import BenTechDeviceServer


class Deodorant(BenTechDeviceServer):
    """自動で消臭"""

    COMMANDS = {"SPRAY": b"\x01"}

    def __init__(self):
        super().__init__(
            name="BT-deodorant",
            service_id=bluetooth.UUID("cb1786f9-3211-410a-941b-269ee08c47ad"),
            control_char_id=bluetooth.UUID("a13e8dd4-0046-4c9b-b320-b0fba7a2f651"),
        )
        self.servo = PWM(Pin(0))
        self.servo.freq(50)

    # 角度(degree)からデュティー比を0〜65535 の範囲の値として返す関数
    def _servo_value(self, degree):
        return int((degree * 9.5 / 180 + 2.5) * 65535 / 100)

    async def _spray(self):
        self.servo.duty_u16(self._servo_value(0))
        await asyncio.sleep(1)
        self.servo.duty_u16(self._servo_value(50))
        await asyncio.sleep(0.5)
        self.servo.duty_u16(self._servo_value(0))

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["SPRAY"]:
            await self._spray()
        else:
            print(f"Unknown Command Received: {command}")


async def main():
    deodorant = Deodorant()
    await deodorant.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
