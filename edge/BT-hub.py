# BT-hub

import asyncio
import aioble
from machine import Pin
from micropython import const
from common_hub import ResponsiveDeviceManager, ControllableDeviceManager


MOCKVAR_is_detection_started = False

led = Pin("LED", Pin.OUT)


class LidControllerManager(ResponsiveDeviceManager):
    def __init__(self):
        self.service_id = const("ac6dd643-a32e-42fb-836d-8130790d9ab4")
        super().__init__(
            name=const("BT-lid-controller"),
            control_service_id=self.service_id,
            control_char_id=const("74779bc7-1e28-4cb1-8dd7-3a3f2a9259ab"),
            response_service_id=self.service_id,
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


class PaperObserverManager(ResponsiveDeviceManager):
    def __init__(self):
        self.service_id = const("33d5f2a5-3c6e-4fc0-8f2f-05a76938a929")
        super().__init__(
            name="BT-paper-manager",
            control_service_id=self.service_id,
            control_char_id=const("e20af759-61d6-4406-819a-de6748d4e243"),
            response_service_id=self.service_id,
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


class AutoFlusherManager(ControllableDeviceManager):
    def __init__(self):
        super().__init__(
            name=const("BT-auto-flusher"),
            control_service_id=const("6408f4f4-5002-4787-8c6f-c44147b06802"),
            control_char_id=const("f36a79b8-f196-4975-8e53-15ed99efa275"),
        )

    async def flush(self):
        await self.control(b"\x01")
        self._log("水を流すように指示しました")


class DeodorantManager(ControllableDeviceManager):
    def __init__(self):
        super().__init__(
            name=const("BT-deodorant"),
            control_service_id=const("0b4878fb-2967-4a36-9c48-291dcca5bd1f"),
            control_char_id=const("8a34e943-55d4-4d69-a542-80a8867dac28"),
        )

    async def flush(self):
        await self.control(b"\x01")
        self._log("消臭を指示しました")


lid_controller_manager = LidControllerManager()
paper_observer_manager = PaperObserverManager()
auto_flusher_manager = AutoFlusherManager()
deodorant_manager = DeodorantManager()


async def scan():
    def calk_should_break():
        return (
            lid_controller_manager.is_having_device()
            and auto_flusher_manager.is_having_device()
            and deodorant_manager.is_having_device()
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
            auto_flusher_manager.is_this_device_your_charge(result)
            deodorant_manager.is_this_device_your_charge(result)

            if calk_should_break():
                print("各種デバイスを発見したのでスキャンを終了")
                break

            # print(result, result.name(), result.rssi, result.services())


async def connect():
    global deodorant, deodorant_connection

    await asyncio.gather(
        lid_controller_manager.connect(),
        paper_observer_manager.connect(),
        auto_flusher_manager.connect(),
        deodorant_manager.connect(),
    )


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

            # 蓋を閉じたら水を流す
            await auto_flusher_manager.flush()

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(disconnect())
