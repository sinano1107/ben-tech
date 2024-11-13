# BT-paper-observer

import asyncio
import aioble
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

        self.should_count = False
        self.current_flag = False
        self.threshold = 0.9
        self.interval = 100
        self.roll = 0
        self.count = 0
        self.coef = 3.3 / 65535

    async def _count_cycle(self):
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

    def start(self):
        self.count = 0
        self.roll = 0
        self.should_count = True

    def stop(self):
        self.should_count = False
        return self.roll

    async def run(self):
        while True:
            if not self.should_count:
                await asyncio.sleep(0.1)
                continue
            await self._count_cycle()


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
        self.counter = Counter()

    def _notify_count(self, roll):
        value = roll.to_bytes()
        print(value)
        self._notify_response(value)

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["START"]:
            print("測定開始")
            self.counter.start()
        elif command == __class__.COMMANDS["STOP"]:
            print("測定終了")
            roll = self.counter.stop()
            await asyncio.sleep(1)
            self._notify_count(roll)
        else:
            print(f"Unknown Command Received: {command}")

    async def run(self):
        aioble.register_services(self.service)

        count_task = None

        async def listen_control():
            await self._listen_control()
            count_task.cancel()

        while True:
            await self._wait_to_connect()

            listen_control_task = asyncio.create_task(listen_control())
            count_task = asyncio.create_task(self.counter.run())

            try:
                await listen_control_task
                await count_task
            except asyncio.CancelledError:
                print("キャンセルされました")


async def main():
    observer = PaperObserver()
    await observer.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
