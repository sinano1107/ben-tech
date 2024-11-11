from machine import Pin, PWM
import utime

servo = PWM(Pin(0))
servo.freq(50)


# 角度(degree)からデュティー比を0〜65535 の範囲の値として返す関数
def servo_value(degree):
    return int((degree * 9.5 / 180 + 2.5) * 65535 / 100)


servo.duty_u16(servo_value(0))
utime.sleep(1)
servo.duty_u16(servo_value(60))
utime.sleep(1)
servo.duty_u16(servo_value(0))
