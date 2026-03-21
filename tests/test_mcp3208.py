import time
from hardware.adc import init_adc, read_mcp3208, close_adc
init_adc()
try:
    while True:
        print('MQ2:', read_mcp3208(0), 'FC28:', read_mcp3208(1))
        time.sleep(1)
finally:
    close_adc()
