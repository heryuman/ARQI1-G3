import time
import threading
from config import DISPLAY_ROTATE_SECONDS, DISPLAY_LOOP_SECONDS
from shared_state import state, state_lock, stop_event
from hardware.lcd_display import lcd_write

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
                lcd_write('Mensaje', msg)
            elif status == 'ALERTA GAS':
                lcd_write('ALERTA GAS', f'MQ2:{gas}')
            elif self.screen == 0:
                lcd_write(f'T:{temp if temp is not None else "--"}C', f'H:{hum if hum is not None else "--"}%')
            elif self.screen == 1:
                lcd_write('Distancia', f'{dist if dist is not None else "--"} cm')
            elif self.screen == 2:
                lcd_write(f'MQ2:{gas}', f'FC28:{soil}')
            else:
                lcd_write(color, status)
            time.sleep(DISPLAY_LOOP_SECONDS)
