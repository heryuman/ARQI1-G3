import time
import threading
from config import ADC_CHANNEL_GAS, ADC_CHANNEL_SOIL, SENSOR_READ_SECONDS
from shared_state import state, state_lock, stop_event
from hardware.dht22_sensor import read_dht22
from hardware.ultrasonic import read_distance
from hardware.adc import read_mcp3208
from hardware.color_sensor import read_color
from logic.classifier import classify_color
from services.mongo_service import MongoService

mongo = MongoService()

class SensorThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        while not stop_event.is_set():
            temp, hum = read_dht22()
            try:
                dist = read_distance()
            except Exception as e:
                print('HC-SR04 error:', e)
                dist = None
            try:
                gas = read_mcp3208(ADC_CHANNEL_GAS)
            except Exception as e:
                print('MQ2 error:', e)
                gas = 0
            try:
                soil = read_mcp3208(ADC_CHANNEL_SOIL)
            except Exception as e:
                print('FC28 error:', e)
                soil = 0
            color_name = 'desconocido'
            r = g = b = c = 0
            lux = None
            try:
                r, g, b, c, lux = read_color()
                color_name = classify_color(r, g, b)
            except Exception as e:
                print('TCS34725 error:', e)
            with state_lock:
                if temp is not None:
                    state.temperature = round(temp, 2)
                    state.last_good_temp = state.temperature
                else:
                    state.temperature = state.last_good_temp
                if hum is not None:
                    state.humidity = round(hum, 2)
                    state.last_good_humidity = state.humidity
                else:
                    state.humidity = state.last_good_humidity
                state.distance_cm = dist
                state.gas_value = gas
                state.soil_value = soil
                state.color_r = r
                state.color_g = g
                state.color_b = b
                state.color_clear = c
                state.lux = lux
                state.detected_color = color_name
                payload = {
                    'temperature': state.temperature,
                    'humidity': state.humidity,
                    'distance_cm': state.distance_cm,
                    'gas_value': state.gas_value,
                    'soil_value': state.soil_value,
                    'color_r': state.color_r,
                    'color_g': state.color_g,
                    'color_b': state.color_b,
                    'color_clear': state.color_clear,
                    'lux': state.lux,
                    'detected_color': state.detected_color,
                }
            mongo.insert('sensor_readings', payload)
            time.sleep(SENSOR_READ_SECONDS)
