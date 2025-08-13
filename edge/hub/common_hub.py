from micropython import const
import bluetooth
import uasyncio


class BenTechDeviceManager:

    def __init__(self, name, service_id):
        self.name = const(name)
        self.service_id = const(service_id)
        self.device = None
        self.connection = None
        self.service = None
        self.characteristics = {}

    def is_having_device(self):
        return self.device is not None

    def is_this_device_your_charge(self, result):
        if self.device is not None:
            return
        if result.name() == self.name:
            self.device = result.device

    def is_connected(self):
        return self.connection is not None

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

    async def get_service(self):
        if self.connection is None:
            raise Exception("接続されていないのでサービスを取得できない")
        if self.service is None:
            self.service = await self.connection.service(
                bluetooth.UUID(self.service_id)
            )
        return self.service

    async def get_characteristic(self, char_id):
        if self.connection is None:
            raise Exception("接続されていないのでキャラクタリスティックを取得できない")
        is_char_nothing = self.characteristics.get(char_id) is None
        if is_char_nothing:
            service = await self.get_service()
            char = await service.characteristic(bluetooth.UUID(char_id))
            self.characteristics[char_id] = char
        return self.characteristics[char_id]

    def _log(self, msg):
        print(f"[{self.name}] {msg}")


class ControllableDeviceManager(BenTechDeviceManager):

    def __init__(self, name, service_id, control_char_id):
        super().__init__(name, service_id)
        self.control_char_id = control_char_id

    async def control(self, value):
        try:
            char = await self.get_characteristic(self.control_char_id)
            await char.write(value)
        except Exception as e:
            self._log(f"コントロールに失敗しました e: {e}")


class ResponsiveDeviceManager(ControllableDeviceManager):

    def __init__(
        self,
        name,
        service_id,
        control_char_id,
        response_char_id,
    ):
        super().__init__(name, service_id, control_char_id)
        self.response_char_id = response_char_id

    async def control_with_response(self, value, callback):
        retv = None
        listen_response_task = None

        try:
            char = await self.get_characteristic(self.response_char_id)
        except Exception as e:
            self._log("control_with_responseに失敗しました")
            return

        control_task = uasyncio.create_task(self.control(value))

        async def listen_response():
            nonlocal retv
            data = await char.notified()
            retv = callback(data)

        listen_response_task = uasyncio.create_task(listen_response())
        await listen_response_task
        await control_task

        return retv

    async def response_callback(self):
        print(
            f"レスポンスを受け取りましたがコールバックが設定されていません\n\tdata:{data}"
        )
        return None
