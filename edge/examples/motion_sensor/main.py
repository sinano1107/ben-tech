import time
from machine import Pin
import uasyncio as asyncio

# 設定
MOTION_SENSOR_PIN = 18  # GP28ピンを使用
PIR_SETTINGS = 5     # 30秒のタイムアウト

class PIRMotionDetector:
    def __init__(self, motion_sensor_pin=MOTION_SENSOR_PIN, presence_timeout=PIR_SETTINGS):
        # 設定値の確認を追加
        print("\n=== 設定値の確認 ===")
        print(f"MOTION_SENSOR_PIN: {motion_sensor_pin}")
        print(f"PIR_SETTINGS: {presence_timeout}")
        print("==================\n")

        self.pir_pin = motion_sensor_pin
        self.presence_timeout = presence_timeout
        self.pir_sensor = Pin(self.pir_pin, Pin.IN)

        # デバッグ情報を出力
        print(f"初期化: PIN={self.pir_pin}, TIMEOUT={self.presence_timeout}")

        self.person_present = False
        self.last_detection_time = 0

        self.current_session_start = None
        self.detection_started = False
        self.detection_ended = False
        self.current_duration = 0

        self.monitoring = False
        self._monitor_task = None

    # async def start_monitoring(self):
    #     """監視を開始する"""
    #     if not self.monitoring:
    #         self.monitoring = True
    #         self._monitor_task = asyncio.create_task(self.monitor_presence())
    #         print("モニタリングタスクを開始しました")

    # async def stop_monitoring(self):
    #     """監視を停止する"""
    #     self.monitoring = False
    #     if self._monitor_task:
    #         await self._monitor_task
    #         print("モニタリングタスクを停止しました")

    async def monitor_presence(self):
        try:
            print("\n=== モニタリング開始 ===")
            print("PIRセンサーの監視を開始します...")
            print(f"PIRセンサーピン: {self.pir_pin}")
            print(f"不在判定時間: {self.presence_timeout}秒")
            print("=====================\n")

            # センサーの初期化と初期状態の確認
            await asyncio.sleep(2)
            initial_state = self.pir_sensor.value()
            print(f"センサーの初期状態: {initial_state}")

            while self.monitoring:
                current_time = time.time()
                try:
                    pir_state = self.pir_sensor.value()
                    # センサーの値の変化をデバッグ出力
                    if pir_state:
                        print(f"センサー状態: HIGH ({pir_state})")

                    # フラグのリセット
                    self.detection_started = False
                    self.detection_ended = False

                    if pir_state == 1:  # 人を検知
                        self.last_detection_time = current_time
                        if not self.person_present:
                            print("動きを検知しました")
                            self.person_present = True
                            self.detection_started = True
                            self.current_session_start = time.time()

                    # 一定時間検知がない場合
                    elif (current_time - self.last_detection_time > self.presence_timeout 
                          and self.person_present):
                        print("タイムアウトによる検知終了")
                        self.person_present = False
                        self.detection_ended = True

                        if self.current_session_start:
                            self.current_duration = time.time() - self.current_session_start
                            self.current_session_start = None

                    # 現在進行中のセッションの滞在時間を更新
                    if self.person_present and self.current_session_start:
                        self.current_duration = time.time() - self.current_session_start

                    await asyncio.sleep(0.1)

                except Exception as e:
                    print(f"センサー読み取りエラー: {e}")
                    await asyncio.sleep(1)  # エラー時は少し待機

        except Exception as e:
            print(f"監視中にエラーが発生しました: {e}")
        finally:
            self.monitoring = False
            print("監視を終了します")

    def is_detection_started(self):
        """人の検知が開始されたかどうかを返す"""
        return self.detection_started

    def is_detection_ended(self):
        """人の検知が終了したかどうかを返す"""
        return self.detection_ended

    def get_current_duration(self):
        """現在の滞在時間（秒）を返す"""
        return int(self.current_duration)

    async def cleanup(self):
        """リソースの解放"""
        await self.stop_monitoring()

async def main():
    try:
        # PIRモーションセンサーの初期化
        detector = PIRMotionDetector()
        
        # モニタリング開始
        await detector.start_monitoring()
        
        # メインループ
        while True:
            if detector.is_detection_started():
                print("新しい動き検知を開始しました")
            if detector.is_detection_ended():
                print(f"検知終了 - 合計滞在時間: {detector.get_current_duration()}秒")
            await asyncio.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nプログラムを終了します...")
    finally:
        await detector.cleanup()
        
# プログラムの実行
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nプログラムが中断されました")
except Exception as e:
    print(f"エラーが発生しました: {e}")
