from machine import Pin, ADC
import dht
import time

# Pin definitions
RGB_RED_PIN = 23
RGB_GREEN_PIN = 22
RGB_BLUE_PIN = 21
DHT1_PIN = 33
DHT2_PIN = 26
GAS_PIN = 32
ULTRASONIC_TRIG_PIN = 12
ULTRASONIC_ECHO_PIN = 14
PIR_PIN = 2
LDR_PIN = 27

# Setting up Analog Sensors with Attenuation
gas_adc = ADC(Pin(GAS_PIN))
gas_adc.atten(ADC.ATTN_11DB)

ldr_adc = ADC(Pin(LDR_PIN))
ldr_adc.atten(ADC.ATTN_11DB)

# Setting up Digital Sensors
pir_sensor = Pin(PIR_PIN, Pin.IN)
ultrasonic_trig = Pin(ULTRASONIC_TRIG_PIN, Pin.OUT)
ultrasonic_echo = Pin(ULTRASONIC_ECHO_PIN, Pin.IN)
dht1 = dht.DHT22(Pin(DHT1_PIN))
dht2 = dht.DHT22(Pin(DHT2_PIN))

# Setting up RGB LED
rgb_red = Pin(RGB_RED_PIN, Pin.OUT)
rgb_blue = Pin(RGB_BLUE_PIN, Pin.OUT)
rgb_green = Pin(RGB_GREEN_PIN, Pin.OUT)

def read_ultrasonic_distance():
    '''Read distance from ultrasonic sensor'''
    try:
        # Sending trigger pulse
        ultrasonic_trig.value(0)
        time.sleep_us(2)
        ultrasonic_trig.value(1)
        time.sleep_us(10)
        ultrasonic_trig.value(0)
        
        # Wait for echo and measure
        while ultrasonic_echo.value() == 0:
            pass
        start = time.ticks_us()
        
        while ultrasonic_echo.value() == 1:
            pass
        end = time.ticks_us()
        
        # Calculate distance
        duration = time.ticks_diff(end, start)
        distance = (duration * 0.0343) / 2
        return round(distance, 1)
    except:
        return 0.0

def set_rgb_color(red: int, green: int, blue: int) -> None:
    ''''Set RGB LED Color (0 - LOW and 1 - HIGH)'''
    rgb_red.value(red)
    rgb_green.value(green)
    rgb_blue.value(blue)

def read_sensors() -> dict:
    '''Read Sensor Data'''
    data = {}
    
    # Read Analog sensors
    data['Gas'] = gas_adc.read()
    data['Light'] = round((ldr_adc.read() / 4095) * 100, 1)
    
    # Read Digital sensors
    data['Motion'] = bool(pir_sensor.value())
    data['Distance'] = read_ultrasonic_distance()
    
    # Read DHT22 sensors
    try:
        dht1.measure()
        data['DHT1_Temp'] = dht1.temperature()
        data['DHT1_Humidity'] = dht1.humidity()
    except:
        data['DHT1_Temp'], data['DHT1_Humidity'] = 0.0, 0.0
    
    try:
        dht2.measure()
        data['DHT2_Temp'] = dht2.temperature()
        data['DHT2_Humidity'] = dht2.humidity()
    except:
        data['DHT2_Temp'], data['DHT1_Humidity'] = 0.0, 0.0
    
    return data

def print_sensor_readings(data: dict) -> None:
    '''Print Sensor Readings'''

    print("-" * 30)
    print(f'Timestamp: {time.time()}\n')

    if data['DHT1_Temp'] != 0.0:
        print("[DHT1]") 
        print(f"Temp: {data['DHT1_Temp']}°C - Humidity: {data['DHT1_Humidity']}%\n")
    else:
        print("DHT1: Error")
    
    if data['DHT2_Temp'] != 0.0:
        print("[DHT2]")
        print(f"Temp: {data['DHT2_Temp']}°C - Humidity: {data['DHT2_Humidity']}%\n")
    else:
        print("DHT2: Error")
    
    print(f"Gas: {data['Gas']} | Light: {data['Light']}%")
    print(f"Motion: {'YES' if data['Motion'] else 'NO'} | Distance: {data['Distance']} cm")
    print("-" * 30)

def glow_LED(data: dict) -> None:
    '''Update LED based on DHT22 #2 Temperature'''

    if data['DHT2_Temp'] == 0.0:
        set_rgb_color(1, 0, 1)
    elif data['DHT2_Temp'] < 20:
        set_rgb_color(0, 0, 1)
    elif data['DHT2_Temp'] > 30:
        set_rgb_color(1, 0, 0)
    elif data['DHT2_Temp'] > 25:
        set_rgb_color(1, 1, 0)
    else:
        set_rgb_color(0, 1, 0)


print("Initializing...")

if __name__ == '__main__':
    try:
        while True:
            data: dict = read_sensors()
            print_sensor_readings(data)
            glow_LED(data)
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("Stopped!")
        set_rgb_color(0, 0, 0)