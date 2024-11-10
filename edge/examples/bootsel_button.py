import utime

led = machine.Pin("LED", machine.Pin.OUT)

while True:
    if rp2.bootsel_button() == 1:
        led.on()
    else:
        led.off()
    utime.sleep(0.1)
