import time
from hardware.lcd_display import init_lcd, lcd_write, lcd_clear
init_lcd()
try:
    while True:
        lcd_write('Hola Selvin', 'LCD OK')
        time.sleep(2)
finally:
    lcd_clear()
