from machine import Pin
import time

# 定数の定義
MOTOR_PINS = {
    "IN1": 16,  # GP16
    "IN2": 17,  # GP17
    "IN3": 18,  # GP18
    "IN4": 19,  # GP19
}
MOTOR_DELAY = 0.001  # 1ミリ秒のディレイ

class MotorController:
    SEQUENCE = [
        [1, 0, 0, 0],
        [1, 1, 0, 0],
        [0, 1, 0, 0],
        [0, 1, 1, 0],
        [0, 0, 1, 0],
        [0, 0, 1, 1],
        [0, 0, 0, 1],
        [1, 0, 0, 1]
    ]
    
    def __init__(self):
        self.pins = [
            Pin(16, Pin.OUT),
            Pin(17, Pin.OUT),
            Pin(18, Pin.OUT),
            Pin(19, Pin.OUT)
        ]
    
    def rotate(self, turns, clockwise=True, delay=MOTOR_DELAY):
        steps = int(512 * turns)  # 1回転 = 512ステップ
        sequence = self.SEQUENCE if clockwise else self.SEQUENCE[::-1]
        
        for _ in range(steps):
            for step in sequence:
                for pin, value in zip(self.pins, step):
                    pin.value(value)
                time.sleep(delay)
    
    def cleanup(self):
        for pin in self.pins:
            pin.value(0)

def main():
    motor = MotorController()
    
    try:
        # 時計回りに1回転
        print("Rotating clockwise...")
        motor.rotate(turns=1, clockwise=True)
        time.sleep(1)
        
        # 反時計回りに1回転
        print("Rotating counter-clockwise...")
        motor.rotate(turns=1, clockwise=False)
        
    finally:
        motor.cleanup()

if __name__ == '__main__':
    main()
