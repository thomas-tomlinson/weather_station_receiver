from machine import Pin, UART
import json
import time
import asyncio
import binascii
from microdot import Microdot

app = Microdot()
currentWeatherData = {}
# hc-12 radio setup
uart2 = UART(2, baudrate=9600, tx=17, rx=16)

def processPayload(payload):
    filtered_data = payload.replace(b'\xff', b'')
    if len(filtered_data) == 0:
        # empty data, most likely from noise on the radio
        return None

    try:
        decoded = binascii.a2b_base64(filtered_data)
        weather_data = json.loads(decoded)
        
    except ValueError as e:
        print('decode error: ', e, 'payload: ', filtered_data)
        return None

    return weather_data

async def flash_led():
    led_pin = Pin(23, Pin.OUT)
    led_pin.on()
    await asyncio.sleep_ms(500)
    led_pin.off()

async def uart_listener():
    global currentWeatherData
    while True: 
        await asyncio.sleep(1)
        if uart2.any() > 0:
            readbuf = b''
            stopCharReached = False
            # we need to read up to the first new line, then process
            while stopCharReached is False:
                char = uart2.read(1)
                if char is None:
                    continue
                if char == b'\n':
                    #break character reached, end this
                    stopCharReached = True
                else:
                    readbuf = readbuf + char

            processedData = processPayload(readbuf)

            if processedData is not None:
                currentWeatherData = processedData
                # flash the status LED to indicate we received good data
                asyncio.create_task(flash_led())

@app.route('/')
async def index(request):
    global currentWeatherData
    return currentWeatherData

async def main():
    asyncio.create_task(uart_listener())
    await app.start_server()

asyncio.run(main())
main()