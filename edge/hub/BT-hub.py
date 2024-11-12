# BT-hub

import asyncio
import aioble
import bluetooth
import network
import json
from machine import Pin
from micropython import const
from ..common import (
    BenTechStreamableDeviceServer,
)  # pico側では同階層、開発側では違う階層
from device_managers import (
    LidControllerManager,
    PaperObserverManager,
    AutoFlusherManager,
    DeodorantManager,
)


MOCKVAR_is_detection_started = False

led = Pin("LED", Pin.OUT)

lid_controller_manager = LidControllerManager()
paper_observer_manager = PaperObserverManager()
auto_flusher_manager = AutoFlusherManager()
deodorant_manager = DeodorantManager()


class Hub(BenTechStreamableDeviceServer):
    COMMANDS = {"CONNECT_WIFI": b"\x01", "WIFI_CONNECT_COMPLETED": b"1"}

    def __init__(self):
        super().__init__(
            name=const("BT-hub"),
            service_id=bluetooth.UUID("e295c051-7ac4-4d72-b7ea-3e71e47e15a9"),
            control_char_id=bluetooth.UUID("4576af67-ecc6-434e-8ce7-52c6ab1d5f04"),
            response_char_id=bluetooth.UUID("d95426b1-2cb4-4115-bd4b-32ff24232864"),
            stream_char_id=bluetooth.UUID("feb2f5aa-ec75-46ef-8da6-2da832175d8e"),
        )

        self.wlan = network.WLAN(network.STA_IF)

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["CONNECT_WIFI"]:
            print("接続用のデータを受け付けます")
            ssid, password = await self._listen_wifi_data()

            print("WiFiへ接続します")
            await self._connect_wifi(ssid, password)
        else:
            print(f"Unknown Command Received: {command}")

    async def _listen_wifi_data(self):
        msg = await self._listen_stream()
        wifi_data = json.loads(msg)
        return wifi_data["ssid"], wifi_data["password"]

    async def _connect_wifi(self, ssid, password):
        self.wlan.active(True)

        self.wlan.connect(ssid, password)

        while not self.wlan.isconnected():
            print("WiFiルーターと接続中")
            await asyncio.sleep(1)

        print("WiFiルーターと接続完了")

        # 完了したことを伝える
        await self._notify_response(__class__.COMMANDS["WIFI_CONNECT_COMPLETED"])


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

            await asyncio.gather(
                # 水を流す
                auto_flusher_manager.flush(),
                # 消臭する
                deodorant_manager.spray(),
            )

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        hub = Hub()
        asyncio.run(hub.run())
        # asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(disconnect())
