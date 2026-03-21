from hardware.dht22_sensor import init_dht, read_dht22, close_dht
import time
init_dht()
try:
    while True:
        print(read_dht22())
        time.sleep(2)
finally:
    close_dht()
