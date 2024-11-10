from machine import ADC, Pin
import time

Pin(26, Pin.IN)
a = ADC(0)
coeff = 3.3 / 65535

while True:
    v = a.read_u16() * coeff
    # print("V = {:.2f}".format(v))
    print("=" * int(v / 0.025))
    time.sleep(0.1)
