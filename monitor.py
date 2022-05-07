
import time
import os
import apt
import psutil
from datetime import datetime
import paho.mqtt.client as mqtt
from rpi_bad_power import new_under_voltage
from pySMART import Device

# configuration
brokerAdr = "192.168.1.1"
brokerPort = 1883
brokerUserName = ""
brokerPassword = ""
devicename = "Ouray"
external_drives = []

drive_list = {   # todo add this to json file
          'drive_path':
                 {'Disk1': '/media/disk1',}
                 #'Disk2': '/dev/sdb',}
}

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

def get_rpi_power_status(): # Get power supply undervoltage status
    under_voltage = new_under_voltage()
    if under_voltage is None:
      return('ON')
    elif under_voltage.get():
      return('ON')
    else:
      return('OFF')

def external_drive_base(drive, drive_path) -> dict:
    return {
        'name': f'Disk Use {drive}',
        'unit': '%',
        'icon': 'harddisk',
        'sensor_type': 'sensor',
        'function': lambda: get_disk_usage(f'{drive_path}')
        }

sensors = { # add uptime and fix drive temps
          'temperature':
                {'name':'Temperature',
                 'class': 'temperature',
                 'unit': '°C',
                 'icon': 'thermometer',
                 'sensor_type': 'sensor',
                 'function': get_cpu_temp},
          'clock_speed':
                {'name':'Clock Speed',
                 'unit': 'MHz',
                 'sensor_type': 'sensor',
                 'function': get_clock_speed},
          'disk_use':
                {'name':'Disk Use',
                 'unit': '%',
                 'icon': 'micro-sd',
                 'sensor_type': 'sensor',
                 'function': lambda: get_disk_usage('/')},
          'memory_use':
                {'name':'Memory Use',
                 'unit': '%',
                 'icon': 'memory',
                 'sensor_type': 'sensor',
                 'function': get_memory_usage},
          'cpu_usage':
                {'name':'CPU Usage',
                 'unit': '%',
                 'icon': 'chip',
                 'sensor_type': 'sensor',
                 'function': get_cpu_usage},
          'load_1m':
                {'name': 'Load 1m',
                 'icon': 'cpu-64-bit',
                 'sensor_type': 'sensor',
                 'function': lambda: get_load(0)},
          'load_5m':
                {'name': 'Load 5m',
                 'icon': 'cpu-64-bit',
                 'sensor_type': 'sensor',
                 'function': lambda: get_load(1)},
          'load_15m':
                {'name': 'Load 15m',
                 'icon': 'cpu-64-bit',
                 'sensor_type': 'sensor',
                 'function': lambda: get_load(2)},
          'top_cpu':
                {'name': 'Top CPU Process',
                 'icon': 'chip',
                 'sensor_type': 'sensor',
                 'function': lambda: most_cpu()},
          'top_memory':
                {'name': 'Top Memory Process',
                 'icon': 'memory',
                 'sensor_type': 'sensor',
                 'function': lambda: most_memory()},
          'swap_usage':
                {'name':'Swap Usage',
                 'unit': '%',
                 'icon': 'harddisk',
                 'sensor_type': 'sensor',
                 'function': get_swap_usage},
          'power_status':
                {'name': 'Under Voltage',
                 'class': 'problem',
                 'sensor_type': 'binary_sensor',
                 'function': get_rpi_power_status},
          'updates':
                {'name':'Updates',
                 'icon': 'cellphone-arrow-down',
                 'sensor_type': 'sensor',
                 'function': get_updates},
          'uptime':
                {'name':'Uptime',
                 'class': 'timestamp',
                 'icon': 'clock',
                 'sensor_type': 'sensor',
                 'function': get_uptime},
          'last_message':
                {'name': 'Last Message',
                 'class': 'timestamp',
                 'icon': 'clock-check',
                 'sensor_type': 'sensor',
                 'function': get_last_message},
}

def update_sensors(): # update sensors value
    payload_str = f'{{'
    for sensor, attr in sensors.items():
            payload_str += f'"{sensor}": "{attr["function"]()}",'
    payload_str = payload_str[:-1]
    payload_str += f'}}'
    MyClient.publish(
        topic=f'pimon/{devicename}/{attr["sensor_type"]}/state',
        payload=payload_str,
        qos=1,
        retain=False,
    )

def add_drives(): # add external drives storage percentage
    drives = drive_list['drive_path']
    if drives is not None:
        for drive in drives:
            drive_path = drive_list['drive_path'][drive]
            usage = get_disk_usage(drive_path)
            if usage:
                sensors[f'disk_use_{drive.lower()}'] = external_drive_base(drive, drives[drive])
                external_drives.append(f'disk_use_{drive.lower()}')
            else:
                print(drive + ' drive is not mounted, check that path was entered correct.')

# "on connect" event
def connectFunction (client, userdata, flags, rc):
  if rc==0:
    for sensor, attr in sensors.items():
        MyClient.publish( # home assistant discovery
            topic=f'homeassistant/{attr["sensor_type"]}/{devicename}/{sensor}/config',
            payload = (f'{{'
                    + (f'"device_class":"{attr["class"]}",' if 'class' in attr else '')
                    + f'"name":"{devicename} {attr["name"]}",'
                    + f'"state_topic":"pimon/{devicename}/sensor/state",'
                    + (f'"command_topic":"pimon/{devicename}/switch/set",' if 'command' in attr else '')
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

MyClient = mqtt.Client() # Create a MQTT client object
MyClient.username_pw_set(brokerUserName, brokerPassword)
MyClient.on_connect = connectFunction # run function on connect with broker
MyClient.will_set(f'pimon/{devicename}/availability', "offline", 0, True)
MyClient.connect(brokerAdr, brokerPort) # Connect to the test MQTT broker
MyClient.subscribe('homeassistant/status') # Subscribe to a topic
MyClient.on_message = messageFunction # Attach the messageFunction to subscription
MyClient.loop_start() # Start the MQTT client

add_drives()

while(1):
    try:
        MyClient.publish(f'pimon/{devicename}/availability', "online") # Publish message to MQTT broker
        update_sensors() # update sensors
        time.sleep(30) # sleep for awhile
    except Exception as e:
        print ('Error performing sensor update: ' + str(e))
        exit()
