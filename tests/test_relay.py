import time
from hardware.gpio_setup import setup_gpio, cleanup_gpio
from hardware.outputs import relay_set
setup_gpio()
try:
    while True:
        relay_set(True)
        time.sleep(2)
        relay_set(False)
        time.sleep(2)
finally:
    cleanup_gpio()
