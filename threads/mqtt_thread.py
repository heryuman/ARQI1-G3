import time
import json
import threading
from config import (
    MQTT_PUBLISH_SECONDS, TOPIC_MSG, TOPIC_ALERT, TOPIC_GAS, TOPIC_PROX,
    TOPIC_COLOR, TOPIC_AMB, TOPIC_SOIL, TOPIC_STATE, MQTT_BROKER, MQTT_PORT
)
from shared_state import state, state_lock, stop_event
from services.mqtt_service import MQTTService
from services.mongo_service import MongoService

mongo = MongoService()

class MQTTThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.connected = False
        self.service = MQTTService(
            on_connect=self.on_connect,
            on_message=self.on_message,
            on_disconnect=self.on_disconnect,
        )

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print('MQTT conectado correctamente')
            self.service.subscribe(TOPIC_MSG, qos=1)
            self.service.subscribe(TOPIC_ALERT, qos=1)
        else:
            self.connected = False
            print(f'MQTT error de conexión, rc={rc}')

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        print('MQTT desconectado' + (' inesperadamente' if rc != 0 else ' normalmente'))

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
        except Exception:
            payload = {'raw': msg.payload.decode(errors='ignore')}
        topic = msg.topic
        print('MQTT RX:', topic, payload)
        if topic == TOPIC_MSG:
            text = str(payload.get('message', ''))[:64]
            with state_lock:
                state.dashboard_message = text
                state.dashboard_message_until = time.time() + 5
                state.total_messages += 1
            mongo.insert('messages', {'message': text, 'timestamp': time.time()})
            mongo.insert('commands', {'topic': topic, 'payload': payload, 'timestamp': time.time()})
        elif topic == TOPIC_ALERT:
            action = payload.get('action')
            if action == 'camouflage_on':
                with state_lock:
                    state.camouflage_active = True
                    state.camouflage_until = time.time() + 20
            elif action == 'camouflage_off':
                with state_lock:
                    state.camouflage_active = False
            mongo.insert('commands', {'topic': topic, 'payload': payload, 'timestamp': time.time()})

    def connect_with_retry(self):
        while not stop_event.is_set():
            try:
                print(f'Intentando conectar a MQTT {MQTT_BROKER}:{MQTT_PORT} ...')
                self.service.connect()
                return
            except Exception as e:
                print('No se pudo conectar al broker:', e)
                time.sleep(5)

    def run(self):
        self.connect_with_retry()
        self.service.loop_start()
        try:
            while not stop_event.is_set():
                if not self.connected:
                    print('MQTT no conectado, esperando reconexión...')
                    time.sleep(2)
                    continue
                with state_lock:
                    payload_gas = {'value': state.gas_value, 'alert': state.gas_alert, 'timestamp': time.time()}
                    payload_prox = {'distance_cm': state.distance_cm, 'level': state.meteor_level, 'timestamp': time.time()}
                    payload_color = {'r': state.color_r, 'g': state.color_g, 'b': state.color_b, 'lux': state.lux, 'detected_color': state.detected_color, 'camouflage_active': state.camouflage_active, 'timestamp': time.time()}
                    payload_amb = {'temperature': state.temperature, 'humidity': state.humidity, 'temp_alert': state.temp_alert, 'timestamp': time.time()}
                    payload_soil = {'soil_value': state.soil_value, 'soil_dry': state.soil_dry, 'timestamp': time.time()}
                    payload_state = {'status': state.status_text, 'fans_on': state.fans_on, 'rgb_color': state.rgb_color, 'gas_alerts': state.total_gas_alerts, 'meteor_events': state.total_meteor_events, 'messages': state.total_messages, 'timestamp': time.time()}
                try:
                    self.service.publish_json(TOPIC_GAS, payload_gas)
                    self.service.publish_json(TOPIC_PROX, payload_prox)
                    self.service.publish_json(TOPIC_COLOR, payload_color)
                    self.service.publish_json(TOPIC_AMB, payload_amb)
                    self.service.publish_json(TOPIC_SOIL, payload_soil)
                    self.service.publish_json(TOPIC_STATE, payload_state)
                except Exception as e:
                    print('Error publicando MQTT:', e)
                time.sleep(MQTT_PUBLISH_SECONDS)
        finally:
            try:
                self.service.loop_stop()
            except Exception:
                pass
            try:
                self.service.disconnect()
            except Exception:
                pass
