from machine import Pin, UART
import json
import time
import asyncio
import binascii
from microdot import Microdot

app = Microdot()
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

async def uart_listener():
    global currentWeatherData
    while True: 
        await asyncio.sleep(1)
        if uart2.any() > 0:
            raw_data = uart2.readline()
            processedData = processPayload(raw_data)

            if processedData is not None:
                currentWeatherData = processedData

@app.route('/')
async def index(request):
    global currentWeatherData
    return currentWeatherData

def main():
    asyncio.create_task(uart_listener())
    app.run()
main()