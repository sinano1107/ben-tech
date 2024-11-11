import asyncio
import aioble
from machine import Pin


class BenTechDeviceServer:
    """
    BenTechデバイスのBLEサーバーの共通部分の実装
    共通部分 = hubからの命令を受け付ける処理
    """

    led = Pin("LED", Pin.OUT)

    def __init__(self, name, service_id, control_char_id):
        self.name = name
        self.service = aioble.Service(service_id)
        self.control_char = aioble.Characteristic(
            self.service,
            control_char_id,
            read=True,
            write=True,
            write_no_response=True,
            capture=True,
        )
        self.connection = None

    async def _wait_to_connect(self):
        print("接続を待ちます")
        while self.connection is None:
            try:
                self.connection = await aioble.advertise(
                    100,
                    name=self.name,
                )
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"[_do_wait_to_connect] 予期しないエラーが発生\n\t{e}")
        print("接続されました")

    async def _listen_control(self):
        while self.connection.is_connected():
            try:
                _, command = await self.control_char.written(timeout_ms=1000)

                await self._handle_control(command)
            except asyncio.TimeoutError:
                pass
        print("接続が切断されたため操作の受付を終了しました")

    async def _handle_control(self, command):
        print(
            f"commandを受け取りましたが、ハンドラがオーバーライドされていません\n\tcommand:{command}"
        )

    async def run(self):
        aioble.register_services(self.service)

        await self._wait_to_connect()

        await self._listen_control()


class BenTechResponsiveDeviceServer(BenTechDeviceServer):
    def __init__(self, name, service_id, control_char_id, response_char_id):
        super().__init__(
            name=name,
            service_id=service_id,
            control_char_id=control_char_id,
        )
        self.response_char = aioble.Characteristic(
            self.service,
            response_char_id,
            read=True,
            notify=True,
        )

    async def _notify_response(self, data):
        await self.response_char.notify(self.connection, data)
        print(f"レスポンスを通知しました\n\t{data}")
