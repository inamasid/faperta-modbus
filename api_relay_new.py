import requests
from pymodbus.client import ModbusTcpClient
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
import time, hashlib, datetime, gc

is_post_disabled = True
previous_data = {}

def fetch_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers, timeout=3)
    response.raise_for_status()
    data = response.json()['advice']
    data.pop("id", None)
    data.pop("updated_at", None)
    return data

def write_to_plc(client, address_map, data):
    global previous_data
    status = {}
    for key, address in address_map.items():
        value = bool(data[key])
        if previous_data.get(key) != value:  # Only write if data has changed
            try:
                client.write_register(address, value)
                status[address] = value
            except Exception as e:
                print(f"Error writing to Modbus: {e}")
    previous_data = data.copy()
    return status

def read_from_plc(client, addresses):
    results = {}
    for key, address in addresses.items():
        result = client.read_coils(address, 1)
        if result.isError():
            print(f"Error reading {key} at address {address}")
            results[key] = None
        else:
            results[key] = result.bits[0]
    return results

def send_post(url, data):
    date_today = time.strftime("%Y-%m-%d")
    hashToday = hashlib.md5(date_today.encode()).hexdigest()
    payload = {f"{hashToday}": data}
    response = requests.post(url, json=payload, timeout=3)
    response.raise_for_status()
    return response.status_code, payload

def check_schedule(schedule):
    """ Check if the current time is within any scheduled range. """
    now = datetime.datetime.now().time()
    for period in schedule:
        on_time = datetime.datetime.strptime(period["ontime"], "%H:%M:%S").time()
        off_time = datetime.datetime.strptime(period["offtime"], "%H:%M:%S").time()
        if on_time <= now <= off_time:
            return True
    return False

def main():
    api_url = 'https://inamas.id/dev/faperta/?actuator'
    post_url = 'https://inamas.id/dev/faperta/?sensor'

    write_addresses = {
        'dAB': 0,
        'dPhUp': 1,
        'dPhDown': 2,
        'co2': 3,
        'plantPump': 4,
        'sensorPump': 5,
        'grow1': 6,
        'grow2': 7,
        'grow3': 8,
        'grow4': 9,
        'grow5': 10,
        'grow6': 11
    }

    read_addresses = {
        'wl_low': 12,
        'wl_mid': 13,
        'wl_hig': 14
    }

    PLC_IP = '192.168.0.2'
    PLC_PORT = 502

    client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
    client.connect()

    try:
        while True:
            try:
                print(f"Online mode, synced: {datetime.datetime.now().time()}")
                
                if not client.connected:
                    client.connect()

                # Fetch data from API
                data = fetch_data(api_url)

                # Write fetched data to PLC only if changed
                write_data = write_to_plc(client, write_addresses, data)
                print(f"API Write: {write_data}")

                if not is_post_disabled:
                    # Read data from PLC    
                    read_data = read_from_plc(client, read_addresses)
                    # Send data to server
                    status_code, response_text = send_post(post_url, read_data)
                    print(f"POST status: {status_code}, response: {response_text}\n")
                
                del data  # Free memory
                gc.collect()  # Manual garbage collection
                
                print(" ")
                time.sleep(1)

            except (Timeout, ConnectionError, HTTPError) as e:
                print(f"Network error: {e}, switching to offline mode.")
                
                # Offline mode handling
                if 'auto_watering' in locals() and data.get("auto_watering", 0) == 1:
                    in_watering_time = check_schedule(data.get("watering_schedule", []))
                    plant_pump_state = 1 if in_watering_time else 0
                    client.write_register(write_addresses['plantPump'], plant_pump_state)
                    print(f"Offline mode: Plant Pump set to {'ON' if plant_pump_state else 'OFF'}")

                if 'auto_growlight' in locals() and data.get("auto_growlight", 0) == 1:
                    in_growlight_time = check_schedule(data.get("growlight_schedule", []))
                    growlight_state = 1 if in_growlight_time else 0
                    for i in range(6, 12):  # grow1 to grow6
                        client.write_register(i, growlight_state)
                    print(f"Offline mode: Growlights set to {'ON' if growlight_state else 'OFF'}")

                print(" ")
                time.sleep(5)  # Wait before retrying

            except RequestException as e:
                print(f"Request failed: {e}")
                time.sleep(5)  # Wait before retrying

            except Exception as e:
                print(f"Unexpected error: {e}")
                time.sleep(5)  # Wait before retrying

    except KeyboardInterrupt:
        print("Stopping the script.")

    finally:
        client.close()

if __name__ == "__main__":
    main()
