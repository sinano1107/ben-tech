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


class PIRMotionDetector:
    def is_detection_started(self):
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

    def is_detection_ended(self):
        """
        人の検知が終了したかどうかを返す
        モック：一度ブートセルボタンを押されてから離されたらTrueを返す
        """
        global MOCKVAR_is_detection_started
        if MOCKVAR_is_detection_started and rp2.bootsel_button() != 1:
            MOCKVAR_is_detection_started = False
            return True
        return False


class Hub(BenTechStreamableDeviceServer):
    COMMANDS = {"CONNECT_WIFI": b"\x01", "REQUEST_INFO": b"\x02"}

    RESPONSES = {"WIFI_CONNECT_COMPLETED": b"1"}

    def __init__(self):
        super().__init__(
            name=const("BT-hub"),
            service_id=bluetooth.UUID("e295c051-7ac4-4d72-b7ea-3e71e47e15a9"),
            control_char_id=bluetooth.UUID("4576af67-ecc6-434e-8ce7-52c6ab1d5f04"),
            response_char_id=bluetooth.UUID("d95426b1-2cb4-4115-bd4b-32ff24232864"),
            stream_char_id=bluetooth.UUID("feb2f5aa-ec75-46ef-8da6-2da832175d8e"),
        )
        self.wlan = network.WLAN(network.STA_IF)
        self.lid_controller_manager = LidControllerManager()
        self.paper_observer_manager = PaperObserverManager()
        self.auto_flusher_manager = AutoFlusherManager()
        self.deodorant_manager = DeodorantManager()
        self.motion_detector = PIRMotionDetector()
        self.subscription = None

    ###### Web Appとの通信関連 ######
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
        await self._notify_response(__class__.RESPONSES["WIFI_CONNECT_COMPLETED"])

    async def _stream_info(self):
        data = {
            "WIFI_CONNECTED": self.wlan.isconnected(),
            "SUBSCRIPTION": self.subscription,
        }
        await self._send_stream(json.dumps(data))

    async def _handle_control(self, command):
        if command == __class__.COMMANDS["CONNECT_WIFI"]:
            print("接続用のデータを受け付けます")
            ssid, password = await self._listen_wifi_data()

            print("WiFiへ接続します")
            await self._connect_wifi(ssid, password)
        elif command == __class__.COMMANDS["REQUEST_INFO"]:
            print("自身の情報を提供します")
            await self._stream_info()
        else:
            print(f"Unknown Command Received: {command}")

    ####### 周辺デバイスとの通信関連 ######

    async def _scan(self):
        def calk_should_break():
            return (
                self.lid_controller_manager.is_having_device()
                and self.auto_flusher_manager.is_having_device()
                and self.deodorant_manager.is_having_device()
                and self.paper_observer_manager.is_having_device()
            )

        # 最も高いデューティ サイクルで 5 秒間近くのデバイスをアクティブ スキャン
        async with aioble.scan(
            duration_ms=5000, interval_us=30000, window_us=30000, active=True
        ) as scanner:
            async for result in scanner:
                # 各種デバイスを発見したら変数に代入
                self.lid_controller_manager.is_this_device_your_charge(result)
                self.paper_observer_manager.is_this_device_your_charge(result)
                self.auto_flusher_manager.is_this_device_your_charge(result)
                self.deodorant_manager.is_this_device_your_charge(result)

                if calk_should_break():
                    print("各種デバイスを発見したのでスキャンを終了")
                    break

                # print(result, result.name(), result.rssi, result.services())

    async def _connect(self):
        await asyncio.gather(
            self.lid_controller_manager.connect(),
            self.paper_observer_manager.connect(),
            self.auto_flusher_manager.connect(),
            self.deodorant_manager.connect(),
        )

    async def disconnect(self):
        self.lid_controller_manager.disconnect()
        self.paper_observer_manager.disconnect()
        self.auto_flusher_manager.disconnect()
        self.deodorant_manager.disconnect()

    ###### Taskになるものたち ######

    async def _control_devices(self):
        self.led.on()
        await self._scan()
        await self._connect()
        self.led.off()

        while True:
            if self.motion_detector.is_detection_started():
                print("新しい動き検知を開始しました")

                await asyncio.gather(
                    # 蓋開閉機へ開けるように指示
                    self.lid_controller_manager.open(),
                    # ペーパー測定機へ測定を開始するように指示
                    self.paper_observer_manager.start_observe(),
                )

            if self.motion_detector.is_detection_ended():
                print("検知終了")

                await asyncio.gather(
                    # 蓋開閉機へ閉じるように指示
                    self.lid_controller_manager.close(),
                    # ペーパー測定機へ測定を終了するように指示
                    self.paper_observer_manager.stop_observe(),
                )

                await asyncio.gather(
                    # 水を流す
                    self.auto_flusher_manager.flush(),
                    # 消臭する
                    self.deodorant_manager.spray(),
                )

            await asyncio.sleep(0.1)

    async def _communicate_web_app(self):
        while True:
            await self._wait_to_connect()
            await self._listen_control()

    #############################

    async def run(self):
        aioble.register_services(self.service)

        control_devices_task = asyncio.create_task(self._control_devices())
        communicate_web_app_task = asyncio.create_task(self._communicate_web_app())

        await control_devices_task
        await communicate_web_app_task


if __name__ == "__main__":
    hub = Hub()
    try:
        asyncio.run(hub.run())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(hub.disconnect())
