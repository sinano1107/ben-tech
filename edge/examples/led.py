import aioble
import bluetooth
import uasyncio as asyncio
from machine import Pin

# LEDピンの設定
led_pin = Pin("LED", Pin.OUT)

# サービスとキャラクタリスティックのUUID
SERVICE_UUID = bluetooth.UUID("00A8A81D-4125-410E-A5C3-62615319BCBD")
CHARACTERISTIC_UUID = bluetooth.UUID("46898FE4-4B87-47C5-833F-6B9DF8CA3B13")


# LEDの状態を制御する関数
def set_led_state(state: bool):
    led_pin.value(state)


# Peripheral デバイスとして起動する関数
async def peripheral_server():
    # BLEサーバーの準備
    service = aioble.Service(SERVICE_UUID)
    characteristic = aioble.Characteristic(
        service,
        CHARACTERISTIC_UUID,
        read=True,
        write=True,
        write_no_response=True,
        capture=True,
    )
    aioble.register_services(service)

    # 初期状態でLEDを消灯
    set_led_state(False)
    print("LED Control Peripheral Ready")

    while True:
        # デバイスが接続されるのを待機
        connection = await aioble.advertise(
            100,  # 広告感覚（ms)
            name="masapico [LED]",
            services=[SERVICE_UUID],
        )
        print("Connected to Central")

        # 接続が切れるまでデータを待ち受け
        while connection.is_connected():
            try:
                print("待機開始")
                # Central からの書き込みを待機
                _, data = await characteristic.written()

                # 書き込まれたデータを解釈し、LEDを制御
                if data == b"\x01":
                    set_led_state(True)  # LED点灯
                    print("LED ON")
                elif data == b"\x00":
                    set_led_state(False)  # LED消灯
                    print("LED OFF")
                else:
                    print(f"Unknnown Command Received")

            except Exception as e:
                print(f"Error: {e}")
                break

        print("Disconnected from Central")


if __name__ == "__main__":
    # メインのイベントループを開始
    asyncio.run(peripheral_server())
