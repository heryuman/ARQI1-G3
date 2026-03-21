import time
import json
import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime

import RPi.GPIO as GPIO
import spidev
import board
import busio
import adafruit_tcs34725
import adafruit_dht
from rpi_lcd import LCD
import paho.mqtt.client as mqtt
from pymongo import MongoClient

# =========================================================
# GPIO ACORDADOS
# =========================================================

# Sensores
DHT_GPIO = 4
TRIG_GPIO = 17
ECHO_GPIO = 27

# Reservados para siguiente etapa
SERVO_GPIO = 18
STEPPER_PINS = [5, 6, 13, 19]

# Buzzer
BUZZER_GPIO = 23

# LEDs acordados
# Reutilización práctica:
# GPIO21 -> bus R de 8 RGB
# GPIO16 -> bus G de 8 RGB
# GPIO26 -> bus B de 8 RGB
# GPIO20 -> LED amarillo de estado
RGB_R_GPIO = 21
RGB_G_GPIO = 16
RGB_B_GPIO = 26
LED_AMARILLO_GPIO = 20

# Ventiladores
FAN_RELAY_GPIO = 24

# Botones reservados
BTN_COMPUERTA_GPIO = 12
BTN_TORRETA_IZQ_GPIO = 22
BTN_TORRETA_DER_GPIO = 25
BTN_DISPARO_GPIO = 7
BTN_EMERGENCIA_GPIO = 1

# ADC
ADC_CHANNEL_GAS = 0
ADC_CHANNEL_SOIL = 1

# =========================================================
# CONFIG
# =========================================================

GAS_THRESHOLD = 260
SOIL_DRY_THRESHOLD = 3000
TEMP_THRESHOLD = 30

DIST_LEJANO_CM = 50
DIST_CERCANO_CM = 20

CAMOUFLAGE_SEQUENCE = ["rojo", "amarillo", "azul"]
CAMOUFLAGE_SEQUENCE_TIMEOUT = 15
CAMOUFLAGE_ACTIVE_SECONDS = 20

DISPLAY_ROTATE_SECONDS = 3
SENSOR_READ_SECONDS = 1.0
LOGIC_LOOP_SECONDS = 0.2
OUTPUT_LOOP_SECONDS = 0.1
DISPLAY_LOOP_SECONDS = 0.2
MQTT_PUBLISH_SECONDS = 2.0

RELAY_ACTIVE_HIGH = True
RGB_ACTIVE_HIGH = True
ENABLE_BUZZER = True

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883

TOPIC_GAS = "nave/sensores/gas/gp3"
TOPIC_PROX = "nave/sensores/proximidad/gp3"
TOPIC_COLOR = "nave/sensores/color/gp3"
TOPIC_AMB = "nave/sensores/ambiente/gp3"
TOPIC_SOIL = "nave/sensores/suelo/gp3"
TOPIC_STATE = "nave/estado/gp3"

TOPIC_TORRETA_CMD = "nave/actuadores/torreta/gp3"
TOPIC_COMPUERTA_CMD = "nave/actuadores/compuertas/gp3"
TOPIC_MSG = "nave/control/mensajes/gp3"
TOPIC_ALERT = "nave/alertas/criticas/gp3"

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "nave_espacial"

# =========================================================
# ESTADO COMPARTIDO
# =========================================================

@dataclass
class SharedState:
    temperature: float | None = None
    humidity: float | None = None
    distance_cm: float | None = None
    gas_value: int = 0
    soil_value: int = 0

    color_r: int = 0
    color_g: int = 0
    color_b: int = 0
    color_clear: int = 0
    lux: float | None = None
    detected_color: str = "desconocido"

    gas_alert: bool = False
    temp_alert: bool = False
    soil_dry: bool = False
    meteor_level: str = "sin_lectura"

    fans_on: bool = False
    rgb_color: str = "apagado"
    status_text: str = "Iniciando"

    camouflage_active: bool = False
    camouflage_until: float = 0.0
    recent_colors: list[str] = field(default_factory=list)
    recent_color_times: list[float] = field(default_factory=list)

    last_good_temp: float | None = None
    last_good_humidity: float | None = None

    total_gas_alerts: int = 0
    total_meteor_events: int = 0
    total_messages: int = 0

    dashboard_message: str = ""
    dashboard_message_until: float = 0.0


state = SharedState()
state_lock = threading.Lock()
stop_event = threading.Event()

mongo_queue = queue.Queue()
command_queue = queue.Queue()

# =========================================================
# HARDWARE INIT
# =========================================================

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(TRIG_GPIO, GPIO.OUT)
GPIO.setup(ECHO_GPIO, GPIO.IN)
GPIO.output(TRIG_GPIO, False)

GPIO.setup(FAN_RELAY_GPIO, GPIO.OUT)

GPIO.setup(RGB_R_GPIO, GPIO.OUT)
GPIO.setup(RGB_G_GPIO, GPIO.OUT)
GPIO.setup(RGB_B_GPIO, GPIO.OUT)
GPIO.setup(LED_AMARILLO_GPIO, GPIO.OUT)

GPIO.setup(BUZZER_GPIO, GPIO.OUT)

GPIO.output(BUZZER_GPIO, GPIO.LOW)
GPIO.output(LED_AMARILLO_GPIO, GPIO.LOW)

lcd = LCD()

spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

i2c = busio.I2C(board.SCL, board.SDA)
tcs = adafruit_tcs34725.TCS34725(i2c)
tcs.integration_time = 50
tcs.gain = 4

# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.utcnow().isoformat()

def push_mongo(collection: str, payload: dict):
    mongo_queue.put({
        "collection": collection,
        "payload": payload,
        "timestamp": now_iso()
    })

def lcd_write(line1="", line2=""):
    try:
        lcd.clear()
        lcd.text(str(line1)[:16], 1)
        lcd.text(str(line2)[:16], 2)
    except Exception:
        pass

def read_mcp3208(channel):
    cmd1 = 0b00000110 | ((channel & 0b100) >> 2)
    cmd2 = (channel & 0b011) << 6
    r = spi.xfer2([cmd1, cmd2, 0])
    return ((r[1] & 0x0F) << 8) | r[2]

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

def classify_color(r, g, b):
    if max(r, g, b) < 25:
        return "oscuro"

    if abs(r - g) < 20 and abs(g - b) < 20 and max(r, g, b) > 90:
        return "blanco"

    if r > g and r > b:
        if g > 0.6 * r:
            return "amarillo"
        return "rojo"

    if g > r and g > b:
        return "verde"

    if b > r and b > g:
        return "azul"

    if r > 120 and g > 120 and b < 80:
        return "amarillo"

    return "desconocido"

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

# =========================================================
# THREADS
# =========================================================

class SensorThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        while not stop_event.is_set():
            temp = None
            hum = None
            try:
                temp = dht.temperature
                hum = dht.humidity
            except RuntimeError:
                pass
            except Exception as e:
                print("DHT22 error:", e)

            try:
                dist = read_distance()
            except Exception as e:
                print("HC-SR04 error:", e)
                dist = None

            try:
                gas = read_mcp3208(ADC_CHANNEL_GAS)
            except Exception as e:
                print("MQ2 error:", e)
                gas = 0

            try:
                soil = read_mcp3208(ADC_CHANNEL_SOIL)
            except Exception as e:
                print("FC28 error:", e)
                soil = 0

            color_name = "desconocido"
            r = g = b = c = 0
            lux = None
            try:
                r, g, b = tcs.color_rgb_bytes
                raw = tcs.color_raw
                c = raw[3] if raw and len(raw) > 3 else 0
                try:
                    lux = tcs.lux
                except Exception:
                    lux = None
                color_name = classify_color(r, g, b)
            except Exception as e:
                print("TCS34725 error:", e)

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
                    "temperature": state.temperature,
                    "humidity": state.humidity,
                    "distance_cm": state.distance_cm,
                    "gas_value": state.gas_value,
                    "soil_value": state.soil_value,
                    "color_r": state.color_r,
                    "color_g": state.color_g,
                    "color_b": state.color_b,
                    "color_clear": state.color_clear,
                    "lux": state.lux,
                    "detected_color": state.detected_color,
                }

            push_mongo("sensor_readings", payload)
            time.sleep(SENSOR_READ_SECONDS)

class LogicThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.last_gas_event = False
        self.last_meteor_level = "sin_lectura"

    def run(self):
        while not stop_event.is_set():
            now = time.time()

            with state_lock:
                gas = state.gas_value
                soil = state.soil_value
                dist = state.distance_cm
                detected_color = state.detected_color
                temp = state.temperature

                state.gas_alert = gas >= GAS_THRESHOLD
                state.temp_alert = temp is not None and temp >= TEMP_THRESHOLD
                state.fans_on = state.gas_alert or state.temp_alert

                state.soil_dry = soil >= SOIL_DRY_THRESHOLD

                if dist is None:
                    state.meteor_level = "sin_lectura"
                elif dist > DIST_LEJANO_CM:
                    state.meteor_level = "lejano"
                elif DIST_CERCANO_CM <= dist <= DIST_LEJANO_CM:
                    state.meteor_level = "cercano"
                else:
                    state.meteor_level = "impacto"

                if detected_color in ["rojo", "amarillo", "azul"]:
                    if not state.recent_colors or detected_color != state.recent_colors[-1]:
                        state.recent_colors.append(detected_color)
                        state.recent_color_times.append(now)

                while state.recent_color_times and (now - state.recent_color_times[0] > CAMOUFLAGE_SEQUENCE_TIMEOUT):
                    state.recent_color_times.pop(0)
                    state.recent_colors.pop(0)

                if state.recent_colors[-3:] == CAMOUFLAGE_SEQUENCE:
                    state.camouflage_active = True
                    state.camouflage_until = now + CAMOUFLAGE_ACTIVE_SECONDS
                    state.recent_colors.clear()
                    state.recent_color_times.clear()

                    push_mongo("events", {
                        "event": "camouflage_activated",
                        "detected_color": detected_color
                    })

                if state.camouflage_active and now > state.camouflage_until:
                    state.camouflage_active = False
                    push_mongo("events", {
                        "event": "camouflage_deactivated"
                    })

                if state.camouflage_active:
                    state.rgb_color = detected_color
                else:
                    state.rgb_color = "apagado"

                if state.gas_alert:
                    state.status_text = "ALERTA GAS"
                elif state.temp_alert:
                    state.status_text = "TEMP ALTA"
                elif state.meteor_level == "impacto":
                    state.status_text = "IMPACTO"
                elif state.meteor_level == "cercano":
                    state.status_text = "METEORITO CER"
                elif state.camouflage_active:
                    state.status_text = "CAMUFLAJE ON"
                elif state.soil_dry:
                    state.status_text = "SUELO SECO"
                else:
                    state.status_text = "OPERATIVA"

                if state.gas_alert and not self.last_gas_event:
                    state.total_gas_alerts += 1
                    push_mongo("events", {
                        "event": "gas_alert",
                        "gas_value": state.gas_value
                    })

                if state.meteor_level != self.last_meteor_level and state.meteor_level in ["lejano", "cercano", "impacto"]:
                    state.total_meteor_events += 1
                    push_mongo("events", {
                        "event": "meteor_detected",
                        "level": state.meteor_level,
                        "distance_cm": state.distance_cm
                    })

                self.last_gas_event = state.gas_alert
                self.last_meteor_level = state.meteor_level

            time.sleep(LOGIC_LOOP_SECONDS)

class OutputThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.last_beep = 0

    def run(self):
        while not stop_event.is_set():
            with state_lock:
                fans_on = state.fans_on
                rgb_color = state.rgb_color
                gas_alert = state.gas_alert
                meteor_level = state.meteor_level

            relay_set(fans_on)

            if rgb_color == "apagado":
                rgb_off()
            else:
                show_color(rgb_color)

            set_led_amarillo(gas_alert)

            now = time.time()
            if ENABLE_BUZZER:
                if gas_alert:
                    buzzer_set(True)
                    time.sleep(0.08)
                    buzzer_set(False)
                    time.sleep(0.12)
                elif meteor_level == "cercano":
                    if now - self.last_beep > 1.0:
                        buzzer_set(True)
                        time.sleep(0.06)
                        buzzer_set(False)
                        self.last_beep = now
                elif meteor_level == "impacto":
                    buzzer_set(True)
                    time.sleep(0.1)
                    buzzer_set(False)
                    time.sleep(0.1)
                else:
                    buzzer_set(False)

            time.sleep(OUTPUT_LOOP_SECONDS)

class DisplayThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.screen = 0
        self.last_change = 0

    def run(self):
        while not stop_event.is_set():
            now = time.time()

            if now - self.last_change >= DISPLAY_ROTATE_SECONDS:
                self.screen = (self.screen + 1) % 4
                self.last_change = now

            with state_lock:
                temp = state.temperature
                hum = state.humidity
                dist = state.distance_cm
                gas = state.gas_value
                soil = state.soil_value
                color = state.detected_color
                status = state.status_text
                msg = state.dashboard_message
                msg_until = state.dashboard_message_until

            if msg and now < msg_until:
                lcd_write("Mensaje", msg)
            elif status == "ALERTA GAS":
                lcd_write("ALERTA GAS", f"MQ2:{gas}")
            elif self.screen == 0:
                lcd_write(f"T:{temp if temp is not None else '--'}C",
                          f"H:{hum if hum is not None else '--'}%")
            elif self.screen == 1:
                lcd_write("Distancia", f"{dist if dist is not None else '--'} cm")
            elif self.screen == 2:
                lcd_write(f"MQ2:{gas}", f"FC28:{soil}")
            else:
                lcd_write(color, status)

            time.sleep(DISPLAY_LOOP_SECONDS)
import json
import time
import random
import threading
import paho.mqtt.client as mqtt

class MQTTThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)

        client_id = f'python-mqtt-{random.randint(0,1000)}'
        self.client = mqtt.Client(client_id=client_id)

        # Si luego necesitás usuario/password:
        self.client.username_pw_set("emqx", "public")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Reintentos automáticos con backoff
        self.client.reconnect_delay_set(min_delay=2, max_delay=15)

        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("MQTT conectado correctamente")

            client.subscribe(TOPIC_MSG, qos=1)
            client.subscribe(TOPIC_ALERT, qos=1)

            # Si luego activás torreta y compuerta:
            # client.subscribe(TOPIC_TORRETA_CMD, qos=1)
            # client.subscribe(TOPIC_COMPUERTA_CMD, qos=1)
        else:
            self.connected = False
            print(f"MQTT error de conexión, rc={rc}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False

        if rc != 0:
            print(f"MQTT desconectado inesperadamente, rc={rc}")
        else:
            print("MQTT desconectado normalmente")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except Exception:
            payload = {"raw": msg.payload.decode(errors="ignore")}

        topic = msg.topic
        print("MQTT RX:", topic, payload)

        if topic == TOPIC_MSG:
            text = str(payload.get("message", ""))[:64]
            with state_lock:
                state.dashboard_message = text
                state.dashboard_message_until = time.time() + 5
                state.total_messages += 1

            push_mongo("messages", {"message": text})
            push_mongo("commands", {"topic": topic, "payload": payload})

        elif topic == TOPIC_ALERT:
            action = payload.get("action")

            if action == "camouflage_on":
                with state_lock:
                    state.camouflage_active = True
                    state.camouflage_until = time.time() + CAMOUFLAGE_ACTIVE_SECONDS

            elif action == "camouflage_off":
                with state_lock:
                    state.camouflage_active = False

            push_mongo("commands", {"topic": topic, "payload": payload})

    def connect_with_retry(self):
        while not stop_event.is_set():
            try:
                print(f"Intentando conectar a MQTT {MQTT_BROKER}:{MQTT_PORT} ...")
                self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
                return
            except Exception as e:
                print("No se pudo conectar al broker:", e)
                time.sleep(5)

    def run(self):
        self.connect_with_retry()
        self.client.loop_start()

        try:
            while not stop_event.is_set():
                if not self.connected:
                    print("MQTT no conectado, esperando reconexión...")
                    time.sleep(2)
                    continue

                with state_lock:
                    payload_gas = {
                        "value": state.gas_value,
                        "alert": state.gas_alert,
                        "timestamp": now_iso()
                    }
                    payload_prox = {
                        "distance_cm": state.distance_cm,
                        "level": state.meteor_level,
                        "timestamp": now_iso()
                    }
                    payload_color = {
                        "r": state.color_r,
                        "g": state.color_g,
                        "b": state.color_b,
                        "lux": state.lux,
                        "detected_color": state.detected_color,
                        "camouflage_active": state.camouflage_active,
                        "timestamp": now_iso()
                    }
                    payload_amb = {
                        "temperature": state.temperature,
                        "humidity": state.humidity,
                        "temp_alert": state.temp_alert,
                        "timestamp": now_iso()
                    }
                    payload_soil = {
                        "soil_value": state.soil_value,
                        "soil_dry": state.soil_dry,
                        "timestamp": now_iso()
                    }
                    payload_state = {
                        "status": state.status_text,
                        "fans_on": state.fans_on,
                        "rgb_color": state.rgb_color,
                        "gas_alerts": state.total_gas_alerts,
                        "meteor_events": state.total_meteor_events,
                        "messages": state.total_messages,
                        "timestamp": now_iso()
                    }

                try:
                    self.client.publish(TOPIC_GAS, json.dumps(payload_gas), qos=0)
                    self.client.publish(TOPIC_PROX, json.dumps(payload_prox), qos=0)
                    self.client.publish(TOPIC_COLOR, json.dumps(payload_color), qos=0)
                    self.client.publish(TOPIC_AMB, json.dumps(payload_amb), qos=0)
                    self.client.publish(TOPIC_SOIL, json.dumps(payload_soil), qos=0)
                    self.client.publish(TOPIC_STATE, json.dumps(payload_state), qos=0)
                except Exception as e:
                    print("Error publicando MQTT:", e)

                time.sleep(MQTT_PUBLISH_SECONDS)

        finally:
            try:
                self.client.loop_stop()
            except Exception:
                pass
            try:
                self.client.disconnect()
            except Exception:
                pass

class MongoThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB_NAME]

    def run(self):
        while not stop_event.is_set():
            try:
                item = mongo_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                doc = dict(item["payload"])
                doc["timestamp"] = item["timestamp"]
                self.db[item["collection"]].insert_one(doc)
            except Exception as e:
                print("Mongo insert error:", e)

# =========================================================
# MAIN
# =========================================================

def main():
    threads = [
        SensorThread(),
        LogicThread(),
        OutputThread(),
        DisplayThread(),
        MQTTThread(),
        MongoThread(),
    ]

    try:
        lcd_write("Iniciando", "MQTT+Mongo")
        rgb_off()
        relay_set(False)
        set_led_amarillo(False)
        buzzer_set(False)
        time.sleep(1)

        for t in threads:
            t.start()

        while True:
            with state_lock:
                print("======================================")
                print(f"T/H      : {state.temperature} C / {state.humidity} %")
                print(f"Dist     : {state.distance_cm} cm")
                print(f"MQ2/FC28 : {state.gas_value} / {state.soil_value}")
                print(f"Color    : {state.detected_color} | RGB=({state.color_r},{state.color_g},{state.color_b})")
                print(f"Fans     : {state.fans_on} | Gas: {state.gas_alert} | Temp: {state.temp_alert}")
                print(f"Meteor   : {state.meteor_level}")
                print(f"Camuflaje: {state.camouflage_active} | RGB out: {state.rgb_color}")
                print(f"Estado   : {state.status_text}")
            time.sleep(2)

    except KeyboardInterrupt:
        print("Apagando sistema...")

    finally:
        stop_event.set()
        time.sleep(0.5)

        relay_set(False)
        rgb_off()
        set_led_amarillo(False)
        buzzer_set(False)

        try:
            lcd.clear()
        except Exception:
            pass

        try:
            spi.close()
        except Exception:
            pass

        try:
            dht.exit()
        except Exception:
            pass

        GPIO.cleanup()

if __name__ == "__main__":
    main()