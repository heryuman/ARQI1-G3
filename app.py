import time
import board
import adafruit_dht
from rpi_lcd import LCD
# Configura el sensor en el pin GPIO 4
# Si usas un DHT11, cambia adafruit_dht.DHT22 por adafruit_dht.DHT11
dhtDevice = adafruit_dht.DHT22(board.D17)
lcd=LCD()
print("Iniciando lectura del DHT22...")

lcd.text("SISTEMA NAVE", 1) # Línea 1
lcd.text("INICIANDO...", 2)  # Línea 2
time.sleep(2)

lcd.clear()

while True:
    try:
        # Lectura de temperatura y humedad
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity

        print(
            "Temp: {:.1f} C    Humedad: {}% ".format(
                temperature_c, humidity
            )
        )

        if temperature_c >27:
            print("la temperatura esta yendose alch")

        lcd.text("Temp. Cabina:", 1)
        lcd.text(f"{temperature_c} C", 2)

    except RuntimeError as error:
        # Los errores de lectura son comunes en estos sensores, solo continuamos
        print("Error de lectura: ", error.args[0])
        time.sleep(2.0)
        continue
    except KeyboardInterrupt:
         lcd.clear()
         print("Pantalla limpia y programa detenido.")
    except Exception as error:
        dhtDevice.exit()
        raise error

    time.sleep(2.0)