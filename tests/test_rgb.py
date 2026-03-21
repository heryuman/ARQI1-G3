import time
from hardware.gpio_setup import setup_gpio, cleanup_gpio
from hardware.outputs import show_color, rgb_off
setup_gpio()
try:
    for color in ['rojo', 'verde', 'azul', 'amarillo', 'blanco']:
        show_color(color)
        time.sleep(2)
    rgb_off()
finally:
    cleanup_gpio()
