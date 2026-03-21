import board
import busio
import adafruit_tcs34725

_tcs = None

def init_color_sensor():
    global _tcs
    i2c = busio.I2C(board.SCL, board.SDA)
    _tcs = adafruit_tcs34725.TCS34725(i2c)
    _tcs.integration_time = 50
    _tcs.gain = 4

def read_color():
    r, g, b = _tcs.color_rgb_bytes
    raw = _tcs.color_raw
    c = raw[3] if raw and len(raw) > 3 else 0
    try:
        lux = _tcs.lux
    except Exception:
        lux = None
    return r, g, b, c, lux
