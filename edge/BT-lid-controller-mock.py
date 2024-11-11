# BT-lid-controller-mock

import asyncio
import bluetooth
import aioble
from machine import Pin

DEVICE_NAME = "BT-lid-controller"

# サービスとキャラクタリスティックのUUID
SERVICE_UUID = bluetooth.UUID("ac6dd643-a32e-42fb-836d-8130790d9ab4")
LISTEN_CONTROL_CHAR_UUID = bluetooth.UUID("74779bc7-1e28-4cb1-8dd7-3a3f2a9259ab")
NOTIFY_RESPONSE_CHAR_UUID = bluetooth.UUID("82bdb1a9-4ffd-4a97-8b5f-af7e84655133")

led = Pin("LED", Pin.OUT)


async def main():
    # 初期化中を知らせるためにLEDを点灯
    led.on()

    # serviceの生成
    service = aioble.Service(SERVICE_UUID)

    # characteristicの生成
    listen_control_char = aioble.Characteristic(
        service,
        LISTEN_CONTROL_CHAR_UUID,
        read=True,
        write=True,
        write_no_response=True,
        capture=True,
    )
    notify_response_char = aioble.Characteristic(
        service,
        NOTIFY_RESPONSE_CHAR_UUID,
        read=True,
        notify=True,
    )

    # サービスを登録
    aioble.register_services(service)

    # 初期化終了を知らせるためにLEDを消灯
    led.off()

    while True:
        # centralからの接続を待機
        connection = await aioble.advertise(100, name=DEVICE_NAME)  # 広告感覚(ms)
        print("接続されました")

        # 操作を受け付ける
        while connection.is_connected():
            try:
                _, data = await listen_control_char.written(timeout_ms=1000)

                # 書き込まれたデータを解釈し、指示された操作を実行
                if data == b"\x01":
                    print("蓋をあける")
                elif data == b"\x02":
                    print("蓋を閉じる")
                    await asyncio.sleep(3)
                    print("蓋を閉じることが完了しました")
                    notify_response_char.notify(connection, b"\x01")
                else:
                    print(f"Unknown Command Received")
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"予期しないエラーが発生 {e}")

        print("接続が切断されました")


if __name__ == "__main__":
    asyncio.run(main())
