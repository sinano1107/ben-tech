# BT-hub

import asyncio
import aioble
import bluetooth
import network
import json

# import urequests
# import utime
from micropython import const
from common import (
    BenTechStreamableDeviceServer,
)  # pico側では同階層、開発側では違う階層
from device_managers import (
    LidControllerManager,
    PaperObserverManager,
    AutoFlusherManager,
    DeodorantManager,
)
from motion_sensor import PIRMotionDetector
from usocket_firebase_test import send_post_request

MOCKVAR_is_detection_started = False


class MockPIRMotionDetector:
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


"""
class Timer:
    def __init__(self):
        self.start_time = None

    def start(self):
        self.start_time = utime.time()

    def stop(self):
        if self.start_time is None:
            print("タイマーがスタートされていないのでストップできません")
            return
        end_time = utime.time()
        diff = end_time - self.start_time
        self.start_time = None
        return diff
"""


class Hub(BenTechStreamableDeviceServer):
    COMMANDS = {
        "CONNECT_WIFI": b"\x01",
        "REQUEST_INFO": b"\x02",
        "DISCONNECT_WIFI": b"\x03",
        "SET_SUBSCRIPTION": b"\x04",
        "RE_SCAN": b"\x05",
    }

    RESPONSES = {
        "WIFI_CONNECT_COMPLETED": (1).to_bytes(4, "big"),
        "WIFI_CONNECT_FAILED": (2).to_bytes(4, "big"),
    }

    def __init__(self):
        super().__init__(
            name=const("BT-hub"),
            service_id=bluetooth.UUID("e295c051-7ac4-4d72-b7ea-3e71e47e15a9"),
            control_char_id=bluetooth.UUID("4576af67-ecc6-434e-8ce7-52c6ab1d5f04"),
            response_char_id=bluetooth.UUID("d95426b1-2cb4-4115-bd4b-32ff24232864"),
            stream_char_id=bluetooth.UUID("feb2f5aa-ec75-46ef-8da6-2da832175d8e"),
        )
        self.wlan = network.WLAN(network.STA_IF)
        # self.timer = Timer()
        self.lid_controller_manager = LidControllerManager()
        self.paper_observer_manager = PaperObserverManager()
        self.auto_flusher_manager = AutoFlusherManager()
        self.deodorant_manager = DeodorantManager()
        self.motion_detector = PIRMotionDetector()
        self.mock_motion_detector = MockPIRMotionDetector()
        self.subscription = None

    ###### Firebase関連 ######
    async def _save_history(self, staying_time, used_roll_count):
        print("履歴を保存します")
        if not self.wlan.isconnected():
            print("WiFiにつながっていないので通知できません")
            return

        data = {
            "stayingTime": staying_time,
            "usedRollCount": used_roll_count,
            "subscription": self.subscription,
        }

        """
        data = json.dumps(data).encode("utf-8")

        response = urequests.post(
            "https://savehistory-t2l7bkkhbq-an.a.run.app",
            headers={"Content-Type": "application/json"},
            data=data,
        )
        print(
            f"履歴保存をリクエストしました\n\tstatus_code: {response.status_code}\n\ttext: {response.text}"
        )
        response.close()
        """

        send_post_request(
            "https://asia-northeast1-jphacks-ben-tech.cloudfunctions.net/saveHistory",
            data,
        )
        print(f"履歴保存をリクエストしました")

    async def _update_data(self, params):
        # dev/dataを編集する
        if not self.wlan.isconnected():
            print("WiFiにつながっていないので通知できません")
            return
        send_post_request(
            "https://asia-northeast2-jphacks-ben-tech.cloudfunctions.net/editData",
            params,
        )
        """
        response = urequests.post(
            "https://editdata-t2l7bkkhbq-dt.a.run.app",
            headers={"Content-Type": "application/json"},
            data=json.dumps(params),
        )
        """
        print(f"dataの変更をリクエストしました\n\tparams: {params}")
        # response.close()

    ###### Web Appとの通信関連 ######
    async def _listen_wifi_data(self):
        msg = await self.start_listen()
        wifi_data = json.loads(msg)
        return wifi_data["ssid"], wifi_data["password"]

    async def _connect_wifi(self, ssid, password):
        print(ssid, password)
        self.wlan.active(True)

        self.wlan.connect(ssid.encode("utf-8"), password)

        limit_sec = 30
        count = 0

        while not self.wlan.isconnected() and count <= limit_sec:
            print("WiFiルーターと接続中")
            count += 1
            await asyncio.sleep(1)

        if count >= limit_sec:
            print("WiFiルーターと接続失敗")
            # 失敗したことを伝える
            self._notify_response(__class__.RESPONSES["WIFI_CONNECT_FAILED"])
            return

        print("WiFiルーターと接続完了")
        # 完了したことを伝える
        self._notify_response(__class__.RESPONSES["WIFI_CONNECT_COMPLETED"])

    async def _disconnect_wifi(self):
        self.wlan.disconnect()
        print("wifiとの接続解除をwlanに指示しました")

    def _get_connected_devices_list(self):
        retv = []

        if self.lid_controller_manager.is_connected():
            retv.append("lid-controller")
        if self.paper_observer_manager.is_connected():
            retv.append("paper-observer")
        if self.auto_flusher_manager.is_connected():
            retv.append("auto-flusher")
        if self.deodorant_manager.is_connected():
            retv.append("deodorant")

        return retv

    async def _stream_info(self):
        data = {
            "WIFI_CONNECTED": self.wlan.isconnected(),
            "SUBSCRIPTION": self.subscription,
            "CONNECTED_DEVICES": self._get_connected_devices_list(),
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
        elif command == __class__.COMMANDS["DISCONNECT_WIFI"]:
            await self._disconnect_wifi()
        elif command == __class__.COMMANDS["SET_SUBSCRIPTION"]:
            subscription = await self.start_listen()
            self.subscription = json.loads(subscription)
            print(f"subscriptionを設定しました\n\t{self.subscription}")
        elif command == __class__.COMMANDS["RE_SCAN"]:
            print("再スキャンして接続を試みます")
            self.led.on()
            await self._scan()
            await self._connect()
            self.led.off()
            await self._send_stream(json.dumps(self._get_connected_devices_list()))
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
        # gatherはダメだった
        """
        await asyncio.gather(
            self.lid_controller_manager.connect(),
            self.paper_observer_manager.connect(),
            self.auto_flusher_manager.connect(),
            self.deodorant_manager.connect(),
        )
        """
        await self.lid_controller_manager.connect(),
        await self.paper_observer_manager.connect(),
        await self.auto_flusher_manager.connect(),
        await self.deodorant_manager.connect(),

    async def disconnect(self):
        self.lid_controller_manager.disconnect()
        self.paper_observer_manager.disconnect()
        self.auto_flusher_manager.disconnect()
        self.deodorant_manager.disconnect()

    ###### Taskになるものたち ######

    async def _control_devices(self):
        while True:
            if (
                self.motion_detector.is_detection_started()
                or self.mock_motion_detector.is_detection_started()
            ):
                print("新しい動き検知を開始しました")
                self.led.on()

                # self.timer.start()

                await asyncio.gather(
                    # 蓋開閉機へ開けるように指示
                    self.lid_controller_manager.open(),
                    # ペーパー測定機へ測定を開始するように指示
                    self.paper_observer_manager.start_observe(),
                    # ユーザーが入ってきたことをfirebaseに保存
                    self._update_data({"in_room": True}),
                )

            if (
                self.motion_detector.is_detection_ended()
                or self.mock_motion_detector.is_detection_ended()
            ):
                staying_time = self.motion_detector.get_current_duration()
                print(f"検知終了 - 合計滞在時間: {staying_time}秒")
                self.led.off()

                # staying_time = self.timer.stop()

                _, used_roll_count = await asyncio.gather(
                    # 蓋開閉機へ閉じるように指示
                    self.lid_controller_manager.close(),
                    # ペーパー測定機へ測定を終了するように指示
                    self.paper_observer_manager.stop_observe(),
                )
                print(f"消費ロール数 {used_roll_count}")

                await asyncio.gather(
                    # 水を流す
                    self.auto_flusher_manager.flush(),
                    # 消臭する
                    self.deodorant_manager.spray(),
                )

                await asyncio.gather(
                    # 履歴を保存します（自動的に通知も送る）
                    self._save_history(staying_time, used_roll_count),
                )

            await asyncio.sleep(0.1)

    async def _communicate_web_app(self):
        # BenTechStreamableDeviceServerのrun()を参考
        while True:
            await self._wait_to_connect()

            listen_control_task = asyncio.create_task(self._listen_control())
            listen_stream_task = asyncio.create_task(self._listen_stream())

            await listen_control_task
            await listen_stream_task

    #############################

    async def run(self):
        aioble.register_services(self.service)

        self.led.on()
        await self._scan()
        await self._connect()
        self.led.off()

        self.motion_detector.monitoring = True
        control_devices_task = asyncio.create_task(self._control_devices())
        communicate_web_app_task = asyncio.create_task(self._communicate_web_app())
        monitor_presence_task = asyncio.create_task(
            self.motion_detector.monitor_presence()
        )

        await control_devices_task
        await communicate_web_app_task
        await monitor_presence_task


if __name__ == "__main__":
    hub = Hub()
    try:
        asyncio.run(hub.run())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(hub.disconnect())
