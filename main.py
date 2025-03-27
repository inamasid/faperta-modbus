import requests
import json
#import webview
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.label import Label
from pymodbus.client import ModbusTcpClient as ModbusClient

# Define Modbus server details
MODBUS_SERVER_IP = '192.168.0.2'  # Replace with your actual Modbus server IP
MODBUS_PORT = 502  # Default Modbus TCP port

# Define the Modbus register write addresses
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

class ActuatorApp(App):
    def build(self):
        self.label = Label(text="Waiting for API update...")
        return self.label

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_data = None  # Store the last fetched data

    def fetch_and_update(self, dt):  # Add the 'dt' parameter here
        url = "http://inamas.id/dev/faperta/?actuator"  # Replace with your actual API URL

        try:
            # Try to make the GET request to the API
            response = requests.get(url)

            if response.status_code == 200:
                # Parse the response as JSON
                data = response.json()

                # Read the current data from actuator.json
                try:
                    with open("actuator.json", "r") as json_file:
                        stored_data = json.load(json_file)
                except (FileNotFoundError, json.JSONDecodeError):
                    stored_data = None

                # If current data differs from stored data, update actuator.json and Modbus
                if stored_data != data:
                    # Save the new data to actuator.json
                    with open("actuator.json", "w") as json_file:
                        json.dump(data, json_file, indent=4)

                    # Write to Modbus registers based on the new data
                    self.write_to_modbus(data)

                    # Update the label to reflect the changes
                    self.label.text = "Data updated and saved to actuator.json and Modbus"
                else:
                    self.label.text = "No changes in data. No update needed."
            else:
                self.handle_no_internet()

        except requests.exceptions.RequestException:
            self.handle_no_internet()


    def handle_no_internet(self):
        # In case of no internet, read from actuator.json and update Modbus
        try:
            with open("actuator.json", "r") as json_file:
                data = json.load(json_file)

            # Write the data to Modbus registers
            self.write_to_modbus(data)

            self.label.text = "No internet connection. Writing actuator.json data to Modbus."

        except (FileNotFoundError, json.JSONDecodeError):
            self.label.text = "No internet and actuator.json file not found."

    def write_to_modbus(self, data):
        # Initialize the Modbus client
        client = ModbusClient(MODBUS_SERVER_IP, port=MODBUS_PORT)

        # Connect to the Modbus server
        client.connect()

        # Write data to the specified Modbus registers
        for address, value in data.items():
            register = write_addresses.get(address)
            if register is not None:
                # Write coil if the value is binary (0 or 1)
                if isinstance(value, int) and value in [0, 1]:
                    client.write_coil(register, value)
                else:
                    # Write holding register for other integer values
                    client.write_register(register, value)
                print(f"Written {value} to address {address} (register {register})")

        # Disconnect after the operation
        client.close()

    def on_start(self):
        # Set up Kivy Clock to check the API every second (1-second interval)
        Clock.schedule_interval(self.fetch_and_update, 1)

        # Open Google in fullscreen with pywebview
        self.open_browser()

    def open_browser(self):
        # Open the browser with the URL (https://google.com) in fullscreen mode
        #webview.create_window('Faperta Dashboard', 'http://dev.inamas.id/faperta', width=1920, height=1080, resizable=False)
        #webview.start()
        pass

if __name__ == '__main__':
    ActuatorApp().run()
