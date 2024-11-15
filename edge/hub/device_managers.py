from micropython import const
from common_hub import ResponsiveDeviceManager, ControllableDeviceManager


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

    async def open(self):
        await self.control(b"\x01")
        self._log("蓋を開けるように指示しました")

    async def close(self):
        def callback(data):
            if data == b"\x01":
                return True
            else:
                return False

        if self.connection == None:
            self._log("接続されていないのでpassします")
            return
        self._log("蓋を閉めるように指示します")
        result = await self.control_with_response(b"\x02", callback)
        self._log(
            "蓋を閉めることに成功したようです"
            if result
            else "error 蓋を閉められませんでした"
        )


class PaperObserverManager(ResponsiveDeviceManager):
    def __init__(self):
        self.service_id = const("0698d1ab-9144-496a-9878-9f6027e17ef9")
        super().__init__(
            name="BT-paper-observer",
            control_service_id=self.service_id,
            control_char_id=const("dcdbd8b8-0ad3-45b2-867a-1e449fd14646"),
            response_service_id=self.service_id,
            response_char_id=const("49fb080c-8d01-4996-b318-27186d78430a"),
        )

    async def start_observe(self):
        await self.control(b"\x01")
        self._log("トイレットペーパーの監視をスタートさせました")

    async def stop_observe(self):
        self._log("トイレットペーパーの監視をストップします")

        def callback(data):
            return int.from_bytes(data)

        response = await self.control_with_response(b"\x02", callback)
        # if response is None:
        #    return "不明"
        return response


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
            control_service_id=const("cb1786f9-3211-410a-941b-269ee08c47ad"),
            control_char_id=const("a13e8dd4-0046-4c9b-b320-b0fba7a2f651"),
        )

    async def spray(self):
        if self.connection is None:
            self._log("接続していないのでスプレーしません")
            return
        await self.control(b"\x01")
        self._log("消臭を指示しました")
