import asyncio
import bluetooth
import aioble
from machine import Pin

# peripheralとして動作するが、ボタンを押された時にnotificationを送信する

# LEDピンの設定
led = Pin("LED", Pin.OUT)

# サービスとキャラクタリスティックのUUID
SERVICE_UUID = bluetooth.UUID("00a8a81d-4125-410e-a5c3-62615319bcbd")
LISTEN_CONTROL_CHAR_UUID = bluetooth.UUID("46898fe4-4b87-47c5-833f-6b9df8ca3b13")
NOTIFY_ON_BUTTON_PRESSED_CHAR_UUID = bluetooth.UUID(
    "2273b7b4-fbbd-4904-81f5-d9f6ea4dadc7"
)


async def main():
    # BLEサーバーの準備
    service = aioble.Service(SERVICE_UUID)
    listen_control_char = aioble.Characteristic(
        service,
        LISTEN_CONTROL_CHAR_UUID,
        read=True,
        write=True,
        write_no_response=True,
        capture=True,
    )
    notify_on_button_pressed_char = aioble.Characteristic(
        service,
        NOTIFY_ON_BUTTON_PRESSED_CHAR_UUID,
        read=True,
        notify=True,
    )
    aioble.register_services(service)

    # LEDをオフにする
    led.off()

    # 接続を待機
    connection = await aioble.advertise(
        100,  # 広告間隔(ms)
        name="masapico [COMMUNICATION]",
        services=[SERVICE_UUID],
    )
    print("Connected to central")

    listen_operation_task = asyncio.create_task(
        listen_operation(listen_control_char, connection)
    )
    notify_on_button_pressed_task = asyncio.create_task(
        notify_on_button_pressed(notify_on_button_pressed_char, connection)
    )
    await listen_operation_task
    await notify_on_button_pressed_task
    # await asyncio.gather(listen_operation_task, notify_on_button_pressed_task)


async def listen_operation(char, connection):
    print("操作を観測します")

    while connection.is_connected():
        try:
            _, data = await char.written()

            # 書き込まれたデータを解釈し、LEDを制御
            if data == b"\x01":
                led.on()  # LED点灯
                print("LED ON")
            elif data == b"\x00":
                led.off()  # LED消灯
                print("LED OFF")
            else:
                print(f"Unknnown Command Received")

        except Exception as e:
            print(f"Error: {e}")

    print("Disconnected from Central")


async def notify_on_button_pressed(char, connection):
    print("ボタン操作を観測します")

    value = False
    while connection.is_connected():
        if not value and rp2.bootsel_button() == 1:
            value = True
            char.notify(connection, b"pressed")
        elif value and rp2.bootsel_button() == 0:
            value = False
            char.notify(connection, b"released")

        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
