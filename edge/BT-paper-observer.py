import asyncio
import bluetooth
from machine import ADC, Pin
from common import BenTechResponsiveDeviceServer


class Counter:
    def __init__(self):
        # これないとうまく動かない
        Pin(26, Pin.IN)
        self.led = Pin("LED", Pin.OUT)
        self.adc = ADC(0)
        self.coeff = 3.3 / 65535

        self.current_flag = False
        self.threshold = 1.5
        self.interval = 100
        self.roll = 0
        self.count = 0
        self.coef = 3.3 / 65535

    async def start(self):
        while True:
            v = self.adc.read_u16() * self.coeff
            print("V = {:.2f}, roll = {}".format(v, self.roll))
            print("=" * int(v / 0.03))
            await asyncio.sleep(0.01)

            flag = v >= self.threshold and self.count >= self.interval

            if flag != self.current_flag:
                if flag:
                    self.led.on()
                    self.roll += 1
                    self.count = 0
                else:
                    self.led.off()
                self.current_flag = flag

            self.count += 1


class PaperObserver(BenTechResponsiveDeviceServer):
    """トイレットペーパー消費量観測機"""

    COMMANDS = {"START": b"\x01", "STOP": b"\x02"}

    def __init__(self):
        super().__init__(
            name="BT-paper-observer",
            service_id=bluetooth.UUID("0698d1ab-9144-496a-9878-9f6027e17ef9"),
            control_char_id=bluetooth.UUID("dcdbd8b8-0ad3-45b2-867a-1e449fd14646"),
            response_char_id=bluetooth.UUID("49fb080c-8d01-4996-b318-27186d78430a"),
        )

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["START"]:
            print("測定開始")
        elif command == __class__.COMMANDS["STOP"]:
            print("測定終了")
        else:
            print(f"Unknown Command Received: {command}")


async def main():
    observer = PaperObserver()
    await observer.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
