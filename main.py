from machine import Pin, UART
import json
import time


# hc-12 radio setup
uart2 = UART(2, baudrate=9600, tx=17, rx=16)

def processPayload(payload):
    filtered_data = payload.replace(b'\xff', b'')
    if len(filtered_data) == 0:
        # empty data, most likely from noise on the radio
        return None

    try:
        decoded = filtered_data.decode()
        weather_data = json.loads(decoded)
        
    except UnicodeError as e:
        print('invalid Unicode decode: ',filtered_data)
        return None
    
    except ValueError as e:
        print('json parse failed, payload: ', decoded)
        return None

    return weather_data

while True:
    if uart2.any() > 0:
        raw_data = uart2.readline()
        processedData = processPayload(raw_data)
    else:
        continue

    if processedData is not None:
        print(processedData)