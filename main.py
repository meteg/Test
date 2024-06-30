# -*- coding: utf-8 -*-
import os
import paho.mqtt.client as mqtt
from pyModbusTCP.client import ModbusClient
import json
import yaml
import time
import schedule
import threading
import sys

# MQTT broker bilgileri
mqtt_broker = os.getenv('MQTT_BROKER', 'mqtt.ndx.com.tr')
mqtt_port = int(os.getenv('MQTT_PORT', 1883))
mqtt_username = os.getenv('MQTT_USERNAME', 'ndx')
mqtt_password = os.getenv('MQTT_PASSWORD', 'ndx')
mqtt_topic_prefix = "homeassistant/sensor/Akvaryum/"

modbus_host = os.getenv('MODBUS_HOST', '172.16.70.1')
modbus_port = int(os.getenv('MODBUS_PORT', 5050))

def read_sensor_configurations(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)

def read_modbus_value(unit_id, address, registers):
    modbus_client = ModbusClient(host=modbus_host, port=modbus_port, unit_id=unit_id, auto_open=True)
    modbus_client.timeout = 2  # 2 saniye zaman aşımı

    result = None
    for attempt in range(3):  # 3 kez dene
        if registers == 1:
            regs = modbus_client.read_holding_registers(address, 1)
        elif registers == 2:
            regs = modbus_client.read_holding_registers(address, 2)
        else:
            return None

        if regs:
            modbus_client.close()
            if registers == 1:
                result = regs[0]  # uint8
            elif registers == 2:
                result = (regs[0] << 16) + regs[1]  # uint16
            break  # Başarılı sorguda döngüden çık

        print(f"Attempt {attempt + 1} failed for unit_id: {unit_id}, address: {address}", file=sys.stdout)
        time.sleep(1)  # Bir sonraki deneme için 1 saniye bekle

    modbus_client.close()
    return result

def send_to_mqtt(sensor_id, value, data_type):
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set(username=mqtt_username, password=mqtt_password)
    mqtt_client.connect(mqtt_broker, mqtt_port)

    mqtt_topic = "{}{}/state".format(mqtt_topic_prefix, sensor_id)
    mqtt_client.publish(mqtt_topic, value)

    config_topic = "{}{}/config".format(mqtt_topic_prefix, sensor_id)
    if data_type == "uint16":
        config_message = {
            "name": sensor_id,
            "state_topic": mqtt_topic,
            "unit_of_measurement": "C",
            "device_class": "temperature",
            "unique_id": sensor_id
        }
    elif data_type == "uint32":
        config_message = {
            "name": sensor_id,
            "state_topic": mqtt_topic,
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total",
            "unique_id": sensor_id
        }
    else:
        print("Invalid data type:", data_type, file=sys.stdout)
        mqtt_client.disconnect()
        return

    mqtt_client.publish(config_topic, json.dumps(config_message))
    mqtt_client.disconnect()

def job(sensor):
    value = read_modbus_value(sensor["unit_id"], sensor["address"], sensor["registers"])
    if value is not None:
        send_to_mqtt(sensor["unique_id"], value, sensor["data_type"])
    else:
        print(f"Failed to read value for sensor: {sensor['name']}", file=sys.stdout)

def schedule_jobs(sensor_configurations):
    for sensor in sensor_configurations["sensors"]:
        schedule.every(1).minutes.do(job, sensor)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    sensor_configurations = read_sensor_configurations("sensor.yaml")
    schedule_jobs(sensor_configurations)

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    scheduler_thread.join()

if __name__ == "__main__":
    main()
