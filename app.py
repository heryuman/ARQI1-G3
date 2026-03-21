import time
from hardware.gpio_setup import setup_gpio, cleanup_gpio
from hardware.adc import init_adc, close_adc
from hardware.dht22_sensor import init_dht, close_dht
from hardware.color_sensor import init_color_sensor
from hardware.lcd_display import init_lcd, lcd_clear, lcd_write
from hardware.outputs import rgb_off, relay_set, set_led_amarillo, buzzer_set
from shared_state import state, state_lock, stop_event
from threads.sensor_thread import SensorThread
from threads.logic_thread import LogicThread
from threads.output_thread import OutputThread
from threads.display_thread import DisplayThread
from threads.mqtt_thread import MQTTThread

def main():
    setup_gpio()
    init_adc()
    init_dht()
    init_color_sensor()
    init_lcd()
    threads = [SensorThread(), LogicThread(), OutputThread(), DisplayThread(), MQTTThread()]
    try:
        lcd_write('Iniciando', 'MQTT+Mongo')
        rgb_off()
        relay_set(False)
        set_led_amarillo(False)
        buzzer_set(False)
        time.sleep(1)
        for t in threads:
            t.start()
        while True:
            with state_lock:
                print('======================================')
                print(f'T/H      : {state.temperature} C / {state.humidity} %')
                print(f'Dist     : {state.distance_cm} cm')
                print(f'MQ2/FC28 : {state.gas_value} / {state.soil_value}')
                print(f'Color    : {state.detected_color} | RGB=({state.color_r},{state.color_g},{state.color_b})')
                print(f'Fans     : {state.fans_on} | Gas: {state.gas_alert} | Temp: {state.temp_alert}')
                print(f'Meteor   : {state.meteor_level}')
                print(f'Camuflaje: {state.camouflage_active} | RGB out: {state.rgb_color}')
                print(f'Estado   : {state.status_text}')
            time.sleep(2)
    except KeyboardInterrupt:
        print('Apagando sistema...')
    finally:
        stop_event.set()
        time.sleep(0.5)
        relay_set(False)
        rgb_off()
        set_led_amarillo(False)
        buzzer_set(False)
        lcd_clear()
        close_adc()
        close_dht()
        cleanup_gpio()

if __name__ == '__main__':
    main()
