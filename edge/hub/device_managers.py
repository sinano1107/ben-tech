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
            control_service_id=const("cb1786f9-3211-410a-941b-269ee08c47ad"),
            control_char_id=const("a13e8dd4-0046-4c9b-b320-b0fba7a2f651"),
        )

    async def spray(self):
        await self.control(b"\x01")
        self._log("消臭を指示しました")
