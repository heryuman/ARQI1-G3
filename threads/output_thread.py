import time
import threading
from config import OUTPUT_LOOP_SECONDS, ENABLE_BUZZER
from shared_state import state, state_lock, stop_event
from hardware.outputs import relay_set, rgb_off, show_color, set_led_amarillo, buzzer_set

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
            if rgb_color == 'apagado':
                rgb_off()
            else:
                show_color(rgb_color)
            set_led_amarillo(gas_alert)
            now = time.time()
            if ENABLE_BUZZER:
                if gas_alert:
                    buzzer_set(True); time.sleep(0.08); buzzer_set(False); time.sleep(0.12)
                elif meteor_level == 'cercano':
                    if now - self.last_beep > 1.0:
                        buzzer_set(True); time.sleep(0.06); buzzer_set(False); self.last_beep = now
                elif meteor_level == 'impacto':
                    buzzer_set(True); time.sleep(0.1); buzzer_set(False); time.sleep(0.1)
                else:
                    buzzer_set(False)
            time.sleep(OUTPUT_LOOP_SECONDS)
