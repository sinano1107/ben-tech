# BT-hub

import asyncio
import aioble
from machine import Pin
from device_managers import (
    LidControllerManager,
    PaperObserverManager,
    AutoFlusherManager,
    DeodorantManager,
)


MOCKVAR_is_detection_started = False

led = Pin("LED", Pin.OUT)

lid_controller_manager = LidControllerManager()
paper_observer_manager = PaperObserverManager()
auto_flusher_manager = AutoFlusherManager()
deodorant_manager = DeodorantManager()


async def scan():
    def calk_should_break():
        return (
            lid_controller_manager.is_having_device()
            and auto_flusher_manager.is_having_device()
            and deodorant_manager.is_having_device()
            and paper_observer_manager.is_having_device()
        )

    # 最も高いデューティ サイクルで 5 秒間近くのデバイスをアクティブ スキャン
    async with aioble.scan(
        duration_ms=5000, interval_us=30000, window_us=30000, active=True
    ) as scanner:
        async for result in scanner:
            # 各種デバイスを発見したら変数に代入
            lid_controller_manager.is_this_device_your_charge(result)
            paper_observer_manager.is_this_device_your_charge(result)
            auto_flusher_manager.is_this_device_your_charge(result)
            deodorant_manager.is_this_device_your_charge(result)

            if calk_should_break():
                print("各種デバイスを発見したのでスキャンを終了")
                break

            # print(result, result.name(), result.rssi, result.services())


async def connect():
    global deodorant, deodorant_connection

    await asyncio.gather(
        lid_controller_manager.connect(),
        paper_observer_manager.connect(),
        auto_flusher_manager.connect(),
        deodorant_manager.connect(),
    )


def is_detection_started():
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


def is_detection_ended():
    """
    人の検知が終了したかどうかを返す
    モック：一度ブートセルボタンを押されてから離されたらTrueを返す
    """
    global MOCKVAR_is_detection_started
    if MOCKVAR_is_detection_started and rp2.bootsel_button() != 1:
        MOCKVAR_is_detection_started = False
        return True
    return False


async def disconnect():
    lid_controller_manager.disconnect()


async def main():
    led.on()
    await scan()
    led.off()

    led.on()
    await connect()
    led.off()

    while True:
        if is_detection_started():
            print("新しい動き検知を開始しました")

            await asyncio.gather(
                # 蓋開閉機へ開けるように指示
                lid_controller_manager.open(),
                # ペーパー測定機へ測定を開始するように指示
                paper_observer_manager.start_observe(),
            )

        if is_detection_ended():
            print("検知終了")

            await asyncio.gather(
                # 蓋開閉機へ閉じるように指示
                lid_controller_manager.close(),
                # ペーパー測定機へ測定を終了するように指示
                paper_observer_manager.stop_observe(),
            )

            await asyncio.gather(
                # 水を流す
                auto_flusher_manager.flush(),
                # 消臭する
                deodorant_manager.spray(),
            )

        await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("===中断しました===")
    finally:
        asyncio.run(disconnect())
