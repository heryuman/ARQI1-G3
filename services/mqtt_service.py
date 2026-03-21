import json
import random
import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD

class MQTTService:
    def __init__(self, on_connect=None, on_message=None, on_disconnect=None):
        client_id = f'python-mqtt-{random.randint(0,1000)}'
        self.client = mqtt.Client(client_id=client_id)
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect
        self.client.reconnect_delay_set(min_delay=2, max_delay=15)

    def connect(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)

    def loop_start(self):
        self.client.loop_start()

    def loop_stop(self):
        self.client.loop_stop()

    def disconnect(self):
        self.client.disconnect()

    def publish_json(self, topic, payload, qos=0):
        self.client.publish(topic, json.dumps(payload), qos=qos)

    def subscribe(self, topic, qos=1):
        self.client.subscribe(topic, qos=qos)
