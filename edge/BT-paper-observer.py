# BT-paper-observer

import asyncio
import aioble
import bluetooth
from machine import ADC, Pin
from common import BenTechResponsiveDeviceServer


class FixedList:
    def __init__(self, size):
        self.size = size
        self.data = []

    def add(self, value):
        # リストの長さが指定されたサイズよりも大きければ、古い要素を削除
        if len(self.data) >= self.size:
            self.data.pop(0)
        self.data.append(value)

    def variance(self):
        # 要素がない場合、分散はゼロとする
        if len(self.data) == 0:
            return 0

        # 平均を計算
        mean = sum(self.data) / len(self.data)

        # 分散を計算
        variance = sum((x - mean) ** 2 for x in self.data) / len(self.data)
        return variance


class Counter:
    def __init__(self):
        # これないとうまく動かない
        Pin(26, Pin.IN)
        self.led = Pin("LED", Pin.OUT)
        self.adc = ADC(0)
        self.coeff = 3.3 / 65535

        self.should_count = False
        self.current_flag = False
        self.threshold = 0.005
        self.interval = 100
        self.roll = 0
        self.count = 0
        self.coef = 3.3 / 65535

        self.list = FixedList(5)

    async def _count_cycle(self):
        v = self.adc.read_u16() * self.coeff

        self.list.add(v)
        variance = self.list.variance()

        # print("=" * int(v / 0.03))
        print("-" * int(variance / 0.001))
        print("V = {:.2f}, roll = {}, variance = {:.2f}".format(v, self.roll, variance))

        flag = variance >= self.threshold and self.count >= self.interval

        if flag != self.current_flag:
            if flag:
                self.led.on()
                self.roll += 1
                self.count = 0
            else:
                self.led.off()
            self.current_flag = flag

        self.count += 1
        await asyncio.sleep(0.01)

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

    # counterだけテスト
    """
    counter = Counter()
    counter.start()
    task = asyncio.create_task(counter.run())
    await task
    """


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
