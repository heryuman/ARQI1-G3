from rpi_lcd import LCD

lcd = None

def init_lcd():
    global lcd
    lcd = LCD()

def lcd_write(line1="", line2=""):
    try:
        lcd.clear()
        lcd.text(str(line1)[:16], 1)
        lcd.text(str(line2)[:16], 2)
    except Exception:
        pass

def lcd_clear():
    try:
        lcd.clear()
    except Exception:
        pass
