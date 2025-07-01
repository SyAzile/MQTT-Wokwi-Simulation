from umqtt.simple import MQTTClient
from machine import Pin, ADC

import network
import ujson
import time
import dht

# MQTT Configuration
MQTT_BROKER = "test.mosquitto.org"
BASE_TOPIC = "home"

# Setting up Digital Sensors
dht1_sensor = dht.DHT22(Pin(33))
dht2_sensor = dht.DHT22(Pin(26))
pir_sensor = Pin(2, Pin.IN)
ultrasonic_trig = Pin(12, Pin.OUT)
ultrasonic_echo = Pin(14, Pin.IN)

# Setting up Analog Sensors
ldr_adc = ADC(Pin(27))
ldr_adc.atten(ADC.ATTN_11DB)

gas_adc = ADC(Pin(32))
gas_adc.atten(ADC.ATTN_11DB)

# RGB LED
rgb_red = Pin(23, Pin.OUT)
rgb_green = Pin(22, Pin.OUT)
rgb_blue = Pin(21, Pin.OUT)


# Room Configuration
AVAILABLE_ROOMS = {
    'room1': {
        'description': "My Room",
        'sensors': ["temperature", "humidity", "light"]
    },
    'kitchen': {
        'description': "Kitchen", 
        'sensors': ["temperature", "humidity", "gas_level"]
    },
    'gate': {
        'description': "Main Gate",
        'sensors': ["distance", "motion"]
    }
}

# Manage Active Clients - {client_id: {rooms: set(), time: timestamp}}
ACTIVE_CLIENTS = {}  

def connect_wifi() -> None:
    '''Connect to WiFi network'''
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    wifi.connect('Wokwi-GUEST', '')
    
    print("Connecting to WiFi...")
    start = time.time()
    
    while not wifi.isconnected():
        if time.time() - start > 20:
            print("WiFi connection timeout!")
            return False
        time.sleep(1)
    
    print("\nWiFi Connected!")
    return True

def message_callback(topic: str, msg: str) -> None:
    '''Handle MQTT messages on home/control'''
    try:
        topic = topic.decode()
        message = ujson.loads(msg.decode())
        
        if topic == f"{BASE_TOPIC}/control":
            handle_control_message(message)
            
    except Exception as e:
        print(f"Message Callback Error: {e}")

def handle_control_message(msg: dict) -> None:
    '''Handle Control Commands'''

    action = msg.get("action")
    client_id = msg.get("client_id")
    
    if not client_id:
        print("Invalid Client-ID")
        return
    
    print(f"Control: {action} from {client_id}")
    
    if action == "subscribe":
        rooms = msg.get("rooms", [])
        subscribe(client_id, rooms)
        
    elif action == "unsubscribe":
        rooms = msg.get("rooms", [])
        unsubscribe(client_id, rooms)
        
    elif action == "disconnect":
        disconnect(client_id)
                
    elif action == "status":
        send_client_status(client_id)

def subscribe(client_id: str, rooms: list) -> None:
    '''Subscribe Client to Rooms'''

    # Check for Valid Rooms
    valid_rooms = []
    for room in rooms:
        if room in AVAILABLE_ROOMS.keys():
            valid_rooms.append(room)
    
    if not valid_rooms:
        handle_error(client_id, 'Invalid Rooms!!!')
        return
    
    # Client is not Active -> Add to Active Client List
    if client_id not in ACTIVE_CLIENTS:
        ACTIVE_CLIENTS[client_id] = {'rooms': set(), 'time': time.time()}
    
    # Avoid Duplicate Room Entries
    ACTIVE_CLIENTS[client_id]['rooms'].update(valid_rooms)
    ACTIVE_CLIENTS[client_id]['time'] = time.time()
    
    print(f"Client {client_id} subscribed to rooms: {list(ACTIVE_CLIENTS[client_id]['rooms'])}")
    
    # Send ACK
    response = {
        "client_id": client_id,
        "action": "subscribed",
        "rooms": list(ACTIVE_CLIENTS[client_id]['rooms']),
        "timestamp": time.time()
    }
    mqtt.publish(f"{BASE_TOPIC}/control/response/{client_id}", ujson.dumps(response))

def unsubscribe(client_id: str, rooms: list) -> None:
    '''Unsubscribe Client from Rooms'''

    if client_id not in ACTIVE_CLIENTS:
        handle_error(client_id, "Client not found")
        return
    
    current = ACTIVE_CLIENTS[client_id]['rooms']
    removed = []
    
    for room in rooms:
        if room in current:
            current.remove(room)
            removed.append(room)
    
    ACTIVE_CLIENTS[client_id]["time"] = time.time()
    
    print(f"Client {client_id} unsubscribed from rooms: {removed}")
    
    # Send ACK
    response = {
        "client_id": client_id,
        "action": "unsubscribed",
        "rooms": list(ACTIVE_CLIENTS[client_id]['rooms']),
        "timestamp": time.time()
    }
    mqtt.publish(f"{BASE_TOPIC}/control/response/{client_id}", ujson.dumps(response))

def disconnect(client_id: str) -> None:
    '''Disconnect Client'''

    if client_id in ACTIVE_CLIENTS:
        rooms = list(ACTIVE_CLIENTS[client_id]['rooms'])
        print(f"Client {client_id} disconnected from rooms: {rooms}")
        
        del ACTIVE_CLIENTS[client_id]
        
        # Send ACK
        response = {
            "client_id": client_id,
            "action": "disconnected",
            "timestamp": time.time()
        }
        mqtt.publish(f"{BASE_TOPIC}/control/response/{client_id}", ujson.dumps(response))

def send_client_status(client_id: str) -> None:
    '''Send Client Status'''

    if client_id in ACTIVE_CLIENTS:
        client_info = ACTIVE_CLIENTS[client_id]
        response = {
            "client_id": client_id,
            "action": "status",
            "subscribed_rooms": list(client_info["rooms"]),
            "last_seen": client_info['time'],
            "timestamp": time.time()
        }
    else:
        response = {
            "client_id": client_id,
            "action": "status",
            "message": "Client Not Found!!!",
            "timestamp": time.time()
        }
    
    mqtt.publish(f"{BASE_TOPIC}/control/response/{client_id}", ujson.dumps(response))

def handle_error(client_id: str, error: str) -> None:
    '''Report Error to Client Control'''

    response = {
        "client_id": client_id,
        "action": "error",
        "message": error,
        "timestamp": time.time()
    }
    mqtt.publish(f"{BASE_TOPIC}/control/response/{client_id}", ujson.dumps(response))

def connect_mqtt() -> None:
    '''Connect MQTT Broker and Subscribe to Home/Control'''

    global mqtt
    try:
        print("Connecting to MQTT Broker...")
        mqtt = MQTTClient("home", MQTT_BROKER, port=1883, keepalive=60)
        mqtt.set_callback(message_callback)
        mqtt.connect()
        
        # Sub to Home/Control
        mqtt.subscribe(f"{BASE_TOPIC}/control")
        print("MQTT Broker Connected!")
        return mqtt

    except Exception as e:
        print(f"MQTT Connection Failed: {e}")
        return None

def read_ultrasonic_distance() -> float:
    '''Read Ultrasonic Distance Sensor'''

    try:
        # Send Trigger Pulse
        ultrasonic_trig.off()
        time.sleep_us(2)
        ultrasonic_trig.on()
        time.sleep_us(10)
        ultrasonic_trig.off()
        
        # Wait for ECHO and measure
        while ultrasonic_echo.value() == 0:
            pass
        start = time.ticks_us()
        
        while ultrasonic_echo.value() == 1:
            pass
        end = time.ticks_us()
        
        # Compute Distance
        duration = time.ticks_diff(end, start)
        distance = (duration * 0.034) / 2
        
        return round(distance, 2)

    except Exception as e:
        print(f'Ultrasonic Sensor Error: {e}')
        return -1

def set_rgb_color(red: int, green: int, blue: int) -> None:
    ''''Set RGB LED Color (0 - LOW and 1 - HIGH)'''
    rgb_red.value(red)
    rgb_green.value(green)
    rgb_blue.value(blue)

def read_all_sensors() -> dict:
    '''Read all Sensors'''

    current_time = time.time()
    
    # Room1
    try:
        dht1_sensor.measure()
        time.sleep(0.2)
        temp1 = dht1_sensor.temperature()
        hum1 = dht1_sensor.humidity()
        light = round((ldr_adc.read() / 4095) * 100, 1)
        
        room1_data = {
            "temperature": round(temp1, 1),
            "humidity": round(hum1, 1),
            "light": light,
            "timestamp": current_time,
            "status": "ONLINE"
        }

    except Exception as e:
        room1_data = {
            "temperature": 0.0,  # Default values
            "humidity": 0.0,
            "light": round((ldr_adc.read() / 4095) * 100, 1),
            "timestamp": current_time,
            "status": "ERROR",
            "error": str(e)
        }
    
    # Kitchen
    try:
        dht2_sensor.measure()
        time.sleep(0.2)
        temp2 = dht2_sensor.temperature()
        hum2 = dht2_sensor.humidity()
        gas = gas_adc.read()
        
        kitchen_data = {
            "temperature": round(temp2, 1),
            "humidity": round(hum2, 1),
            "gas_level": gas,
            "timestamp": current_time,
            "status": "ONLINE"
        }

    except Exception as e:
        kitchen_data = {
            "temperature": 0.0,
            "humidity": 0.0,
            "gas_level": gas_adc.read(),
            "timestamp": current_time,
            "status": "ERROR",
            "error": str(e)
        }
    
    # Gate
    try:
        distance = read_ultrasonic_distance()
        motion = bool(pir_sensor.value())
        
        gate_data = {
            "distance": distance,
            "motion": motion,
            "timestamp": current_time,
            "status": "ONLINE"
        }

    except Exception as e:
        gate_data = {
            "distance": 0.0,
            "motion": False,
            "timestamp": current_time,
            "status": "ERROR",
            "error": str(e)
        }
    
    return {
        "room1": room1_data,
        "kitchen": kitchen_data,
        "gate": gate_data
    }

def glow_LED(data: dict):
   '''Update LED based on Kitchen Temperature'''

   kitchen_temp = data['kitchen']['temperature']
   
   if kitchen_temp == 0.0:
       set_rgb_color(1, 0, 1)
   elif kitchen_temp < 20:
       set_rgb_color(0, 0, 1)
   elif kitchen_temp > 30:
       set_rgb_color(1, 0, 0)
   elif kitchen_temp > 25:
       set_rgb_color(1, 1, 0)
   else:
       set_rgb_color(0, 1, 0)

def publish_room_readings(data: dict) -> None:
    '''Publish Sensor Readings to Room Topics'''

    try:
        for r_name, r_data in data.items():
            # Check if any client is subscribed to this room
            subscribers = []
            for client_id, client_info in ACTIVE_CLIENTS.items():
                if r_name in client_info['rooms']:
                    subscribers.append(client_id)
            
            # Only publish if there are subscribers
            if subscribers:
                readings = {
                    "room": r_name,
                    "description": AVAILABLE_ROOMS[r_name]["description"],
                    "sensors": r_data,
                    # "subscribers": subscribers,
                    "subscriber_count": len(subscribers)
                }
                
                # Publish to room-specific topic
                topic = f"{BASE_TOPIC}/rooms/{r_name}"
                mqtt.publish(topic, ujson.dumps(readings))
                print(f"Published {r_name} data to {len(subscribers)} Subscribers.")

    except Exception as e:
        print(f"Error Publishing: {e}")

def publish_system_summary(data: dict) -> None:
    '''Publish System Summary'''

    try:
        summary = {
            "ACTIVE_CLIENTS": len(ACTIVE_CLIENTS),
            "SENSOR_READINGS": data,
            "TIME": time.time()
        }
        
        mqtt.publish(f"{BASE_TOPIC}/summary", ujson.dumps(summary))
    except Exception as e:
        print(f"Error Publishing: {e}")

def print_system_status(data: dict) -> None:
    '''Print Sensor Readings in Serial Monitor'''
    try:
        room1 = data["room1"]
        kitchen = data["kitchen"] 
        gate = data["gate"]
        
        print("-" * 50)
        print("[HOME SYSTEM]")
        print(f"ROOM1: {room1.get('temperature', 'N/A')}°C, {room1.get('humidity', 'N/A')}%, Light: {room1.get('light', 'N/A')}%")
        print(f"KITCHEN: {kitchen.get('temperature', 'N/A')}°C, {kitchen.get('humidity', 'N/A')}%, Gas: {kitchen.get('gas_level', 'N/A')}")
        print(f"GATE: {gate.get('distance', 'N/A')} cm, Motion: {'YES' if gate.get('motion') else 'NO'}")
        print(f"Active Clients: {len(ACTIVE_CLIENTS)}")

        if ACTIVE_CLIENTS:
            for client_id, info in ACTIVE_CLIENTS.items():
                print(f"  - {client_id}: {list(info['rooms'])}")

        print("-" * 50)

    except Exception as e:
        print(f"Error printing status: {e}")

def main():
    global mqtt
    
    print("-" * 50)
    
    # Connecting to WIFI and MQTT Broker
    if not connect_wifi():
        print("Failed to connect to WiFi!")
        return
    
    mqtt = connect_mqtt()
    if not mqtt:
        print("Failed to connect to MQTT!")
        return
    
    print("\nSystem Ready!")
    print(f"MQTT Topics:")
    print(f"  Control: {BASE_TOPIC}/control")
    print(f"  Room Readings: {BASE_TOPIC}/rooms/<r_name>")
    print(f"  System Summary: {BASE_TOPIC}/summary")
    print(f"  Control Responses: {BASE_TOPIC}/control/response/<client_id>")
    
    print(f"\nAvailable Rooms:")
    for room, info in AVAILABLE_ROOMS.items():
        print(f"  - {room}: {info['description']} ({', '.join(info['sensors'])})")
    
    start = time.time()
    while True:
        try:
            mqtt.check_msg()
            readings = read_all_sensors()
            glow_LED(readings)
            
            if ACTIVE_CLIENTS:
                publish_room_readings(readings)

            publish_system_summary(readings)
            print_system_status(readings)
            
            # Cleanup Inactive Client
            if time.time() - start > 60:
                current_time = time.time()
                inactive_clients = []
                
                for client_id, client_info in ACTIVE_CLIENTS.items():
                    if current_time - client_info['time'] > 300:
                        inactive_clients.append(client_id)
                
                for client_id in inactive_clients:
                    print(f"Removing inactive client: {client_id}")
                    disconnect(client_id)
                    
                start = time.time()
            
            time.sleep(3)
            
        except KeyboardInterrupt:
            print("\nShutting down system...")
            break

        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()