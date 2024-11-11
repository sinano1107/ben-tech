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
            self._log("[connect] deviceを保持していません")
            return
        self.connection = await self.device.connect()
        self._log("接続完了")

    async def disconnect(self):
        if self.connection is None:
            self._log("[disconnect] 接続されていません")
            return
        await self.connection.disconnect()
        self._log("接続解除完了")

    async def disconnect(self):
        if self.connection is None:
            self._log("コネクションを保持していないので接続解除の必要がありません")
            return
        await self.connection.disconnect()
        self._log("接続を解除しました")

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


class ControllableDeviceManager(BenTechDeviceManager):
    def __init__(self, name, control_service_id, control_char_id):
        super().__init__(name)
        self.control_service_id = control_service_id
        self.control_char_id = control_char_id

    async def control(self, value):
        char = await self.get_characteristic(
            self.control_service_id, self.control_char_id
        )
        if char is None:
            self._log("characteristicが不明のためコントロールできません")
            return
        await char.write(value)


class ResponsableDeviceManager(ControllableDeviceManager):
    def __init__(
        self,
        name,
        control_service_id,
        control_char_id,
        response_service_id,
        response_char_id,
    ):
        super().__init__(name, control_service_id, control_char_id)
        self.response_service_id = response_service_id
        self.response_char_id = response_char_id

    async def listen_response(
        self,
        callback=lambda data: print(
            f"レスポンスを受け取りましたがコールバックが設定されていません\n\tdata:{data}"
        ),
    ):
        char = await self.get_characteristic(
            self.response_service_id, self.response_char_id
        )
        if char is None:
            self._log("charactaristicが不明のためresponseを待てません")
            return
        data = await char.notified()
        callback(data)


class LidControllerManager(ResponsableDeviceManager):
    def __init__(self):
        service_id = const("ac6dd643-a32e-42fb-836d-8130790d9ab4")
        super().__init__(
            name=const("BT-lid-controller"),
            control_service_id=service_id,
            control_char_id=const("74779bc7-1e28-4cb1-8dd7-3a3f2a9259ab"),
            response_service_id=service_id,
            response_char_id=const("82bdb1a9-4ffd-4a97-8b5f-af7e84655133"),
        )

    async def listen_response(self):

        def callback(data):
            if data == b"\x01":
                self._log("蓋を閉じる事を完了したようです")
            else:
                self._log("Unknown Command Received")

        await super().listen_response(callback)

    async def open(self):
        await self._control(True)

    async def close(self):
        await self._control(False)
        await self.listen_response()

    async def _control(self, open):
        await super().control(b"\x01" if open else b"\x02")
        self._log(f"蓋の操作を指示しました\n\topen:{open}")


class PaperObserverManager(ResponsableDeviceManager):
    def __init__(self):
        self.service_id = const("33d5f2a5-3c6e-4fc0-8f2f-05a76938a929")
        super().__init__(
            name="BT-paper-manager",
            control_service_id=service_id,
            control_char_id=const("e20af759-61d6-4406-819a-de6748d4e243"),
            response_service_id=service_id,
            response_char_id=const("5ff44fbd-11ef-46db-b3d5-794ee0f88449"),
        )

    async def start_observe(self):
        await self._control(True)

    async def stop_observe(self):
        await self._control(False)
        await self._listen_response()

    async def _control(self, start):
        await super().control(b"\x01" if start else b"\x02")
        self._log(f"トイレットペーパーの監視を指示しました\n\tstart:{start}")

    async def _listen_response(self):
        await super().listen_response()


lid_controller_manager = LidControllerManager()
paper_observer_manager = PaperObserverManager()

auto_flusher_name = "BT-auto-flusher"
deodorant_name = "BT-deodorant"

auto_flusher_connection = None
deodorant_connection = None


async def scan():
    global auto_flusher, auto_flusher_name
    global deodorant, deodorant_name

    def calk_should_break():
        return (
            lid_controller_manager.is_having_device()
            and auto_flusher is not None
            and deodorant is not None
            and paper_observer_manager.is_having_device()
        )

    # 最も高いデューティ サイクルで 5 秒間近くのデバイスをアクティブ スキャン
    async with aioble.scan(
        duration_ms=5000, interval_us=30000, window_us=30000, active=True
    ) as scanner:
        async for result in scanner:
            # 各種デバイスを発見したら変数に代入
            lid_controller_manager.is_this_device_your_charge(result)
            paper_observer_manager.is_this_device_your_charge(result)
            if auto_flusher is None and result.name() == auto_flusher_name:
                auto_flusher = result.device
            elif deodorant is None and result.name() == deodorant_name:
                deodorant = result.device

            if calk_should_break():
                print("各種デバイスを発見したのでスキャンを終了")
                break

            # print(result, result.name(), result.rssi, result.services())


async def connect():
    global auto_flusher, auto_flusher_connection
    global deodorant, deodorant_connection

    await asyncio.gather(
        lid_controller_manager.connect(), paper_observer_manager.connect()
    )
    if auto_flusher is not None:
        auto_flusher_connection = await auto_flusher.connect()
    if deodorant is not None:
        deodorant_connection = await deodorant.connect()


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


async def disconnect():
    lid_controller_manager.disconnect()


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

            await asyncio.gather(
                # 蓋開閉機へ開けるように指示
                lid_controller_manager.open(),
                # ペーパー測定機へ測定を開始するように指示
                paper_observer_manager.start_observe(),
            )

        if is_detection_ended():
            print("検知終了")

            await asyncio.gather(
                # 蓋開閉機へ閉じるように指示
                lid_controller_manager.close(),
                # ペーパー測定機へ測定を終了するように指示
                paper_observer_manager.stop_observe(),
            )

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(disconnect())
