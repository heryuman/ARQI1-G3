import time
from hardware.color_sensor import init_color_sensor, read_color
init_color_sensor()
while True:
    print(read_color())
    time.sleep(1)
