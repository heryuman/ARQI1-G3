import time
import threading
from config import (
    GAS_THRESHOLD, SOIL_DRY_THRESHOLD, TEMP_THRESHOLD, DIST_LEJANO_CM,
    DIST_CERCANO_CM, CAMOUFLAGE_SEQUENCE_TIMEOUT, CAMOUFLAGE_ACTIVE_SECONDS,
    CAMOUFLAGE_SEQUENCE, LOGIC_LOOP_SECONDS
)
from shared_state import state, state_lock, stop_event
from services.mongo_service import MongoService

mongo = MongoService()

class LogicThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.last_gas_event = False
        self.last_meteor_level = 'sin_lectura'

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
                    state.meteor_level = 'sin_lectura'
                elif dist > DIST_LEJANO_CM:
                    state.meteor_level = 'lejano'
                elif DIST_CERCANO_CM <= dist <= DIST_LEJANO_CM:
                    state.meteor_level = 'cercano'
                else:
                    state.meteor_level = 'impacto'
                if detected_color in ['rojo', 'amarillo', 'azul']:
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
                    mongo.insert('events', {'event': 'camouflage_activated', 'detected_color': detected_color, 'timestamp': now})
                if state.camouflage_active and now > state.camouflage_until:
                    state.camouflage_active = False
                    mongo.insert('events', {'event': 'camouflage_deactivated', 'timestamp': now})
                state.rgb_color = detected_color if state.camouflage_active else 'apagado'
                if state.gas_alert:
                    state.status_text = 'ALERTA GAS'
                elif state.temp_alert:
                    state.status_text = 'TEMP ALTA'
                elif state.meteor_level == 'impacto':
                    state.status_text = 'IMPACTO'
                elif state.meteor_level == 'cercano':
                    state.status_text = 'METEORITO CER'
                elif state.camouflage_active:
                    state.status_text = 'CAMUFLAJE ON'
                elif state.soil_dry:
                    state.status_text = 'SUELO SECO'
                else:
                    state.status_text = 'OPERATIVA'
                if state.gas_alert and not self.last_gas_event:
                    state.total_gas_alerts += 1
                    mongo.insert('events', {'event': 'gas_alert', 'gas_value': state.gas_value, 'timestamp': now})
                if state.meteor_level != self.last_meteor_level and state.meteor_level in ['lejano', 'cercano', 'impacto']:
                    state.total_meteor_events += 1
                    mongo.insert('events', {'event': 'meteor_detected', 'level': state.meteor_level, 'distance_cm': state.distance_cm, 'timestamp': now})
                self.last_gas_event = state.gas_alert
                self.last_meteor_level = state.meteor_level
            time.sleep(LOGIC_LOOP_SECONDS)
