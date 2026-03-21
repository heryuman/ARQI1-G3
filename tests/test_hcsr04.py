import time
from hardware.gpio_setup import setup_gpio, cleanup_gpio
from hardware.ultrasonic import read_distance
setup_gpio()
try:
    while True:
        print(read_distance())
        time.sleep(1)
finally:
    cleanup_gpio()
