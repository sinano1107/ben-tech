from micropython import const
import bluetooth
import asyncio


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
            if service == None:
                raise Exception("serviceがNoneです。service_idを確認してください")
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


class ResponsiveDeviceManager(ControllableDeviceManager):
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

    async def control_with_response(self, value, callback):
        retv = None
        listen_response_task = None
        control_task = asyncio.create_task(self.control(value))

        async def listen_response():
            nonlocal retv

            char = await self.get_characteristic(
                self.response_service_id, self.response_char_id
            )
            if char is None:
                self._log("charactaristicが不明のためresponseを待てません")
                control_task.cancel()
                return
            data = await char.notified()
            retv = callback(data)

        listen_response_task = asyncio.create_task(listen_response())
        await listen_response_task
        await control_task

        return retv

    async def response_callback(self):
        print(
            f"レスポンスを受け取りましたがコールバックが設定されていません\n\tdata:{data}"
        )
        return None
