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
        self.response_char.notify(self.connection, data)
        print(f"レスポンスを通知しました\n\t{data}")


class BenTechStreamableDeviceServer(BenTechResponsiveDeviceServer):
    def __init__(
        self, name, service_id, control_char_id, response_char_id, stream_char_id
    ):
        super().__init__(
            name=name,
            service_id=service_id,
            control_char_id=control_char_id,
            response_char_id=response_char_id,
        )
        self.stream_char = aioble.Characteristic(
            self.service, stream_char_id, write=True, notify=True, capture=True
        )

    async def _send_stream(self, msg):
        byte_array = msg.encode("utf-8")
        length = len(byte_array)

        count = (length // 20) + 1
        print(f"[_send_stream] {msg} を {count} 回に分けて送信することを伝えます")
        self.stream_char.notify(self.connection, count.to_bytes(4, "big"))

        for i in range(count):
            start = i * 20
            end = length if i == (count - 1) else (start + 20)
            packet = byte_array[start:end]
            self.stream_char.notify(self.connection, packet)
        print("[_send_stream] 送信終了")

    async def _listen_stream(self):
        _, data = await self.stream_char.written()
        length = int.from_bytes(data)
        print(
            f"[_receive_socker_communication] これから{length}個のデータが送られてきます"
        )

        joinned_data = bytes()

        for _ in range(length):
            _, data = await self.stream_char.written()
            print(data)
            joinned_data += data

        msg = joinned_data.decode("utf-8")
        print(f"[_receive_socker_communication] メッセージを受け取りました\n\t{msg}")
        return msg
