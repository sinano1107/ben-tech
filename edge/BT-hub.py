# BT-hub

import asyncio
import aioble
import bluetooth
from machine import Pin
from micropython import const

MOCKVAR_is_detection_started = False

led = Pin("LED", Pin.OUT)

auto_flusher = None
deodorant = None
paper_observer = None


class BenTechDeviceManager:
    def __init__(self, name):
        self.name = const(name)
        self.device = None
        self.connection = None
        self.services = {}
        self.characteristics = {}

    def is_having_device(self):
        return self.device is not None

    def is_this_device_your_charge(self, result):
        if self.device is not None:
            return
        if result.name() == self.name:
            self.device = result.device

    async def connect(self):
        if self.device is None:
            self._log("deviceを保持していません")
            return
        self.connection = await self.device.connect()

    async def get_service(self, id):
        if self.connection is None:
            self._log("接続されていません")
            return
        if self.services.get(id) is None:
            self.services[id] = await self.connection.service(bluetooth.UUID(id))
        return self.services[id]

    async def get_characteristic(self, service_id, char_id):
        if self.connection is None:
            self._log("接続されていません")
            return
        service_is_nothing = self.characteristics.get(service_id) is None
        char_is_nothing = (
            service_is_nothing
            or self.characteristics.get(service_id).get(char_id) is None
        )
        if char_is_nothing:
            service = await self.get_service(service_id)
            char = await service.characteristic(bluetooth.UUID(char_id))
            if service_is_nothing:
                self.characteristics[service_id] = {}
            self.characteristics[service_id][char_id] = char
        return self.characteristics[service_id][char_id]

    def _log(self, msg):
        print(f"[{self.name}] {msg}")


class LidControllerManager(BenTechDeviceManager):
    def __init__(self):
        super().__init__("BT-lid-controller")
        self.service_id = const("00a8a81d-4125-410e-a5c3-62615319bcbd")
        self.listen_control_char_id = const("46898fe4-4b87-47c5-833f-6b9df8ca3b13")
        self.notify_response_char_id = const("2273b7b4-fbbd-4904-81f5-d9f6ea4dadc7")

    async def listen_response(self):
        char = await self.get_characteristic(
            self.service_id, self.notify_response_char_id
        )
        if char is None:
            return
        data = await char.notified()
        if data == b"\x01":
            print("蓋を閉じる事を完了したようです")
        else:
            print("Unknown Command Received")

    async def open(self):
        await self._control(True)

    async def close(self):
        await self._control(False)
        await self.listen_response()

    async def _control(self, open):
        char = await self.get_characteristic(
            self.service_id, self.listen_control_char_id
        )
        if char is None:
            return
        await char.write(b"\x01" if open else b"\x02")


lid_controller_manager = LidControllerManager()

auto_flusher_name = "BT-auto-flusher"
deodorant_name = "BT-deodorant"
paper_observer_name = "BT-paper-observer"

auto_flusher_connection = None
deodorant_connection = None
paper_observer_connection = None


async def scan():
    global auto_flusher, auto_flusher_name
    global deodorant, deodorant_name
    global paper_observer, paper_observer_name

    def calk_should_break():
        return (
            lid_controller_manager.is_having_device()
            and auto_flusher is not None
            and deodorant is not None
            and paper_observer is not None
        )

    # 最も高いデューティ サイクルで 5 秒間近くのデバイスをアクティブ スキャン
    async with aioble.scan(
        duration_ms=5000, interval_us=30000, window_us=30000, active=True
    ) as scanner:
        async for result in scanner:
            # 各種デバイスを発見したら変数に代入
            lid_controller_manager.is_this_device_your_charge(result)
            if auto_flusher is None and result.name() == auto_flusher_name:
                auto_flusher = result.device
            elif deodorant is None and result.name() == deodorant_name:
                deodorant = result.device
            elif paper_observer is None and result.name() == paper_observer_name:
                paper_observer = result.device

            if calk_should_break():
                print("各種デバイスを発見したのでスキャンを終了")
                break

            # print(result, result.name(), result.rssi, result.services())


async def connect():
    global auto_flusher, auto_flusher_connection
    global deodorant, deodorant_connection
    global paper_observer, paper_observer_connection

    # TODO 接続を並列で実行する
    await lid_controller_manager.connect()
    if auto_flusher is not None:
        auto_flusher_connection = await auto_flusher.connect(timeout_ms=timeout)
    if deodorant is not None:
        deodorant_connection = await deodorant.connect(timeout_ms=timeout)
    if paper_observer is not None:
        paper_observer = await paper_observer.connect(timeout_ms=timeout)


def is_detection_started():
    """
    人の検知が開始されたかどうかを返す
    モック：ブートセルボタンが押されている間Trueを返す
    """
    if rp2.bootsel_button() == 1:
        global MOCKVAR_is_detection_started
        if MOCKVAR_is_detection_started:
            return False
        MOCKVAR_is_detection_started = True
        return True
    return False


def is_detection_ended():
    """
    人の検知が終了したかどうかを返す
    モック：一度ブートセルボタンを押されてから離されたらTrueを返す
    """
    global MOCKVAR_is_detection_started
    if MOCKVAR_is_detection_started and rp2.bootsel_button() != 1:
        MOCKVAR_is_detection_started = False
        return True
    return False


async def main():
    led.on()
    await scan()
    led.off()

    led.on()
    await connect()
    led.off()

    while True:
        if is_detection_started():
            print("新しい動き検知を開始しました")

            # 蓋開閉機へ開けるように指示
            await lid_controller_manager.open()

            # TODO ペーパー測定機へ測定を開始するように指示する

        if is_detection_ended():
            print("検知終了")

            # 蓋開閉機へ閉じるように指示
            await lid_controller_manager.close()

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
