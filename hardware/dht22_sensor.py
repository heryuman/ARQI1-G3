import board
import adafruit_dht

dht = None

def init_dht():
    global dht
    dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

def read_dht22():
    temp = hum = None
    try:
        temp = dht.temperature
        hum = dht.humidity
    except RuntimeError:
        pass
    return temp, hum

def close_dht():
    if dht is not None:
        try:
            dht.exit()
        except Exception:
            pass
