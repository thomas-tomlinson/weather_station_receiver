from machine import Pin, UART
import json
import time
import asyncio
import binascii
from microdot import Microdot
import ntptime

app = Microdot()
currentWeatherData = {}
# hc-12 radio setup
uart2 = UART(2, baudrate=9600, tx=17, rx=16)

# try to get the time
while True:
    try:
        ntptime.settime()
        break
    except OSError:
        print("couldn't sync ntp, waiting 2 seconds")
        time.sleep(2)

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

    mytime = time.gmtime()
    iso8601 = str("{}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}Z".format(mytime[0], mytime[1], mytime[2], mytime[3], mytime[4], mytime[5])) 
    weather_data['recordtime'] = iso8601
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
                await asyncio.sleep(0.1)
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