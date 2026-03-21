import RPi.GPIO as GPIO
from config import (
    TRIG_GPIO, ECHO_GPIO, FAN_RELAY_GPIO, RGB_R_GPIO, RGB_G_GPIO,
    RGB_B_GPIO, LED_AMARILLO_GPIO, BUZZER_GPIO
)

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(TRIG_GPIO, GPIO.OUT)
    GPIO.setup(ECHO_GPIO, GPIO.IN)
    GPIO.output(TRIG_GPIO, False)
    for pin in [FAN_RELAY_GPIO, RGB_R_GPIO, RGB_G_GPIO, RGB_B_GPIO, LED_AMARILLO_GPIO, BUZZER_GPIO]:
        GPIO.setup(pin, GPIO.OUT)
    GPIO.output(BUZZER_GPIO, GPIO.LOW)
    GPIO.output(LED_AMARILLO_GPIO, GPIO.LOW)

def cleanup_gpio():
    GPIO.cleanup()
