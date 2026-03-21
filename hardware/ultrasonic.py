import time
import RPi.GPIO as GPIO
from config import TRIG_GPIO, ECHO_GPIO

def read_distance():
    GPIO.output(TRIG_GPIO, False)
    time.sleep(0.05)
    GPIO.output(TRIG_GPIO, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_GPIO, False)
    timeout_inicio = time.time()
    while GPIO.input(ECHO_GPIO) == 0:
        pulso_inicio = time.time()
        if pulso_inicio - timeout_inicio > 0.04:
            return None
    while GPIO.input(ECHO_GPIO) == 1:
        pulso_fin = time.time()
        if pulso_fin - pulso_inicio > 0.04:
            return None
    duracion = pulso_fin - pulso_inicio
    return round(duracion * 17150, 2)
