
import time
import os
import apt
import psutil
import yaml
import argparse
import pathlib
import paho.mqtt.client as mqtt
from datetime import datetime
from rpi_bad_power import new_under_voltage
from pySMART import Device

devicename = None
external_storage = []
settings = {}

def get_disk_usage(path):  # Get hard drive usage
    try:
        disk_percentage = str(psutil.disk_usage(path).percent)
        return disk_percentage
    except Exception as e:
        print('Error while trying to obtain disk usage from ' + str(path) + ' with exception: ' + str(e))
        return 'Error'

def get_updates(): # Get number of apt updates
    cache = apt.Cache()
    cache.open(None)
    cache.upgrade()
    return str(cache.get_changes().__len__())

def get_uptime():
    x = os.popen('uptime -s').read()[:-1]
    date = datetime.strptime(x, "%Y-%m-%d %H:%M:%S").astimezone().isoformat()
    return date

def get_last_message():
    return datetime.now().astimezone().isoformat()

def get_clock_speed(): # get cpu clock speed
    clock_speed = int(psutil.cpu_freq().current)
    return clock_speed

def get_memory_usage(): # Get machine memory usage
    return str(psutil.virtual_memory().percent)

def get_load(arg): # Get machine load
    return str(psutil.getloadavg()[arg])

def get_cpu_usage(): # Get cpu usage
    return str(psutil.cpu_percent(interval=None))

def get_swap_usage(): # Get swapfile usage if one is available
    return str(psutil.swap_memory().percent)

def get_cpu_temp(): # Get pi cpu temperature
    tempFile = open( "/sys/class/thermal/thermal_zone0/temp" )
    cpu_temp = tempFile.read()
    tempFile.close()
    return round(float(cpu_temp)/1000, 1)

def most_cpu():
    x = max(psutil.process_iter(), key=lambda x: x.cpu_percent(0))
    return x.name()

def most_memory():
    y = max(psutil.process_iter(), key=lambda x: x.memory_info()[0])
    return y.name()

def get_rpi_power_status(): # Get undervoltage status
    under_voltage = new_under_voltage()
    if under_voltage is None:
      return('ON')
    elif under_voltage.get():
      return('ON')
    else:
      return('OFF')

def external_drive_base(drive, drive_path) -> dict: # external storage dictionary for home assistant discovery
    return {'name': f'{drive} Usage', 'unit': '%', 'icon': 'harddisk', 'sensor_type': 'sensor', 'function': lambda: get_disk_usage(f'{drive_path}')}

sensors = { # sensor dictionary for home assistant discovery
          'temperature': {'name':'Temperature', 'class': 'temperature', 'unit': '°C', 'icon': 'thermometer', 'sensor_type': 'sensor', 'function': get_cpu_temp},
          'clock_speed': {'name':'Clock Speed', 'unit': 'MHz', 'sensor_type': 'sensor', 'function': get_clock_speed},
          'disk_usage': {'name':'Disk Usage', 'unit': '%', 'icon': 'micro-sd', 'sensor_type': 'sensor', 'function': lambda: get_disk_usage('/')},
          'memory_use': {'name':'Memory Use', 'unit': '%', 'icon': 'memory', 'sensor_type': 'sensor', 'function': get_memory_usage},
          'cpu_usage': {'name':'CPU Usage', 'unit': '%', 'icon': 'chip', 'sensor_type': 'sensor', 'function': get_cpu_usage},
          'load_1m': {'name': 'Load 1m', 'icon': 'cpu-64-bit', 'sensor_type': 'sensor', 'function': lambda: get_load(0)},
          'load_5m': {'name': 'Load 5m', 'icon': 'cpu-64-bit', 'sensor_type': 'sensor', 'function': lambda: get_load(1)},
          'load_15m': {'name': 'Load 15m', 'icon': 'cpu-64-bit', 'sensor_type': 'sensor', 'function': lambda: get_load(2)},
          'top_cpu': {'name': 'Top CPU Process', 'icon': 'chip', 'sensor_type': 'sensor', 'function': lambda: most_cpu()},
          'top_memory': {'name': 'Top Memory Process', 'icon': 'memory', 'sensor_type': 'sensor', 'function': lambda: most_memory()},
          'swap_usage': {'name':'Swap Usage', 'unit': '%', 'icon': 'harddisk', 'sensor_type': 'sensor', 'function': get_swap_usage},
          'power_status': {'name': 'Under Voltage', 'class': 'problem', 'sensor_type': 'binary_sensor', 'function': get_rpi_power_status},
          'updates': {'name':'Updates', 'icon': 'cellphone-arrow-down', 'sensor_type': 'sensor', 'function': get_updates},
          'uptime': {'name':'Uptime', 'class': 'timestamp', 'icon': 'clock', 'sensor_type': 'sensor', 'function': get_uptime},
          'last_message': {'name': 'Last Message', 'class': 'timestamp', 'icon': 'clock-check', 'sensor_type': 'sensor', 'function': get_last_message},
          }

def update_sensors(): # update sensor values
    payload_str = f'{{'
    for sensor, attr in sensors.items():
        if sensor in external_storage or (settings['sensors'][sensor] is not None and settings['sensors'][sensor] == True):
            payload_str += f'"{sensor}": "{attr["function"]()}",'
    payload_str = payload_str[:-1]
    payload_str += f'}}'
    MyClient.publish(
        topic=f'pimon/{devicename}/{attr["sensor_type"]}/state',
        payload=payload_str,
        qos=1,
        retain=False,
    )

def add_drives(): # add external storage
    drives = settings['external_storage']
    if drives is not None:
        for drive in drives:
            drive_path = settings['external_storage'][drive]
            usage = get_disk_usage(drive_path)
            if usage:
                sensors[f'{drive.lower()}_usage'] = external_drive_base(drive, drives[drive])
                external_storage.append(f'{drive.lower()}_usage')
            else:
                print(drive + ' drive is not mounted, or path is incorrect.')

def _parser(): # Argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('settings', help='path to settings file')
    return parser

def settings_defaults(settings): # Set defaults in settings file
    poll_interval = settings['update_interval'] if 'update_interval' in settings else 30
    if 'port' not in settings['mqtt']:
        settings['mqtt']['port'] = 1883
    if 'sensors' not in settings:
        settings['sensors'] = {}
    for sensor in sensors:
        if sensor not in settings['sensors']:
            settings['sensors'][sensor] = True
    if 'external_storage' not in settings or settings['external_storage'] is None:
        settings['external_storage'] = {}
    return settings

def check_settings(settings): # Check settings file for mandatory settings
    values_to_check = ['mqtt', 'devicename']
    for value in values_to_check:
        if value not in settings:
            print(value + 'is not set in settings')
            exit()
    if 'hostname' not in settings['mqtt']:
        print('hostname is not set in settings')
        exit()
    if 'user' in settings['mqtt'] and 'password' not in settings['mqtt']:
        print('password not set in settings')
        exit()

def connectFunction (client, userdata, flags, rc): # "on connect" event
  if rc==0:
    for sensor, attr in sensors.items():
        MyClient.publish( # home assistant discovery
            topic=f'homeassistant/{attr["sensor_type"]}/{devicename}/{sensor}/config',
            payload = (f'{{'
                    + (f'"device_class":"{attr["class"]}",' if 'class' in attr else '')
                    + f'"name":"{devicename} {attr["name"]}",'
                    + f'"state_topic":"pimon/{devicename}/{attr["sensor_type"]}/state",'
                    + (f'"command_topic":"pimon/{devicename}/{attr["sensor_type"]}/set",' if 'command' in attr else '')
                    + (f'"unit_of_measurement":"{attr["unit"]}",' if 'unit' in attr else '')
                    + f'"value_template":"{{{{value_json.{sensor}}}}}",'
                    + f'"unique_id":"{devicename}_Pi_{sensor}",'
                    + f'"availability_topic":"pimon/{devicename}/availability",'
                    + f'"device":{{"identifiers":["{devicename}_Pi"],'
                    + f'"name":"{devicename}","model":"{devicename}", "manufacturer":"RPI"}}'
                    + (f',"icon":"mdi:{attr["icon"]}"' if 'icon' in attr else '')
                    + f'}}'
                      ),
            qos=1,
            retain=True,
        )

    MyClient.publish(f'pimon/{devicename}/availability', 'online', retain=True)
    print('MQTT connected OK Returned code=',rc)
  elif rc == 5:
    print('MQTT authentication failed.\n Exiting.')
    exit()
  else:
    print("MQTT bad connection Returned code=",rc)

# "on message" event
def messageFunction (client, userdata, message):
    topic = str(message.topic)
    payload = str(message.payload.decode("utf-8"))
    print("New message received:", topic+" "+payload)

try:
    args = _parser().parse_args()
    settings_file = args.settings
except:
    print('Attempting to find settings file in same folder as ' + str(__file__))
    default_settings_path = str(pathlib.Path(__file__).parent.resolve()) + '/settings.yaml'
    if os.path.isfile(default_settings_path):
        print('Settings file found, attempting to continue...')
        settings_file = default_settings_path
    else:
        print('Could not find settings.yaml.')
        exit()

with open(settings_file) as s:
    settings = yaml.safe_load(s)
devicename = settings['devicename']
settings = settings_defaults(settings)
check_settings(settings)

MyClient = mqtt.Client() # Create a MQTT client object
MyClient.username_pw_set(settings['mqtt']['user'], settings['mqtt']['password'])
MyClient.on_connect = connectFunction # run function on connect with broker
MyClient.will_set(f'pimon/{devicename}/availability', "offline", 0, True)
MyClient.connect(settings['mqtt']['hostname'], settings['mqtt']['port']) # Connect to the test MQTT broker
MyClient.subscribe('homeassistant/status') # Subscribe to a topic
MyClient.on_message = messageFunction # Attach the messageFunction to subscription
MyClient.loop_start() # Start the MQTT client

add_drives()

while(1):
    try:
        MyClient.publish(f'pimon/{devicename}/availability', "online") # Publish message to MQTT broker
        update_sensors() # update sensors
        time.sleep(settings['update_interval']) # sleep for awhile  todo add cofigurable delay
    except Exception as e:
        print ('Error performing sensor update: ' + str(e))
        exit()
