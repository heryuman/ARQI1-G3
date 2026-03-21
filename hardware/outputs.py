import RPi.GPIO as GPIO
from config import (
    FAN_RELAY_GPIO, RELAY_ACTIVE_HIGH, RGB_ACTIVE_HIGH,
    RGB_R_GPIO, RGB_G_GPIO, RGB_B_GPIO, LED_AMARILLO_GPIO,
    BUZZER_GPIO, ENABLE_BUZZER
)

def relay_set(on: bool):
    value = GPIO.HIGH if on else GPIO.LOW
    if not RELAY_ACTIVE_HIGH:
        value = GPIO.LOW if on else GPIO.HIGH
    GPIO.output(FAN_RELAY_GPIO, value)

def rgb_write(r=False, g=False, b=False):
    if RGB_ACTIVE_HIGH:
        GPIO.output(RGB_R_GPIO, GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(RGB_G_GPIO, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(RGB_B_GPIO, GPIO.HIGH if b else GPIO.LOW)
    else:
        GPIO.output(RGB_R_GPIO, GPIO.LOW if r else GPIO.HIGH)
        GPIO.output(RGB_G_GPIO, GPIO.LOW if g else GPIO.HIGH)
        GPIO.output(RGB_B_GPIO, GPIO.LOW if b else GPIO.HIGH)

def rgb_off():
    rgb_write(False, False, False)

def show_color(color_name: str):
    if color_name == "rojo":
        rgb_write(True, False, False)
    elif color_name == "verde":
        rgb_write(False, True, False)
    elif color_name == "azul":
        rgb_write(False, False, True)
    elif color_name == "amarillo":
        rgb_write(True, True, False)
    elif color_name == "blanco":
        rgb_write(True, True, True)
    else:
        rgb_off()

def set_led_amarillo(on: bool):
    GPIO.output(LED_AMARILLO_GPIO, GPIO.HIGH if on else GPIO.LOW)

def buzzer_set(on: bool):
    if ENABLE_BUZZER:
        GPIO.output(BUZZER_GPIO, GPIO.HIGH if on else GPIO.LOW)
