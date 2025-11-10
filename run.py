import os
# Hent konfig fra add-on options
MQTT_BROKER = os.getenv("MQTT_BROKER", "10.0.0.32")
MQTT_USER = os.getenv("MQTT_USER", "mqttclient")
MQTT_PASS = os.getenv("MQTT_PASS", "")
APP_EMAIL = os.getenv("APP_EMAIL", "")
APP_PASS = os.getenv("APP_PASS", "")
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "300"))

# resten av koden din her, men bruk disse variablene
import requests
import json
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from datetime import datetime
import pytz
import threading
import time
import hashlib
import string
import random

# //////////////////////////////////////////////////// #
# CONFIGURE THESE VALUES VIA ENV OR HA SECRETS:
# MQTT BROKER SETTINGS
MQTT_BROKER = "YOUR_MQTT_BROKER_IP"
MQTT_USER = "YOUR_MQTT_USERNAME"
MQTT_PASS = "YOUR_MQTT_PASSWORD"

# MSPA LINK APP ACCOUNT
APP_EMAIL = "YOUR_EMAIL"
APP_PASS = "YOUR_PASSWORD"

# INTERVAL TO POLL API
POLLING_INTERVAL = 300
# END CONFIG
# //////////////////////////////////////////////////// #

APP_SECRET = 'YOUR_APP_SECRET'
APP_ID = 'YOUR_APP_ID'

HEADERS_TOKEN = {
    "push_type": "Android",
    "authorization": "",
    "appid": APP_ID,
    "nonce": "",
    "ts": "",
    "lan_code": "en",
    "sign": "",
    "content-type": "application/json; charset=UTF-8",
    "accept-encoding": "gzip"
}

HEADERS_POST = HEADERS_TOKEN.copy()
HEADERS_GET = HEADERS_TOKEN.copy()
COMMAND_URL = 'https://api.iot.the-mspa.com/api/device/command'

device_id = ""
product_id = ""
APP_PASS = hashlib.md5(APP_PASS.encode('utf-8')).hexdigest()

# MQTT Topics
SPA_STATUS = '/hjemme/mspa/status'
HEATER_TOPIC = '/hjemme/mspa/heater/control'
HEATER_STATE = '/hjemme/mspa/heater/state'
TEMP_TOPIC = '/hjemme/mspa/temp/control'
TEMP_STATE = '/hjemme/mspa/temp/state'
TEMP_CURRENT = '/hjemme/mspa/temp/current'
BUBBLE_TOPIC = '/hjemme/mspa/bubbles/control'
BUBBLE_STATE = '/hjemme/mspa/bubbles/state'
OZON_TOPIC = '/hjemme/mspa/ozon/control'
OZON_STATE = '/hjemme/mspa/ozon/state'
UVL_TOPIC = '/hjemme/mspa/uvl/control'
UVL_STATE = '/hjemme/mspa/uvl/state'
FILTER_TOPIC = '/hjemme/mspa/filter/control'
FILTER_STATE = '/hjemme/mspa/filter/state'

all_topics = [(HEATER_TOPIC, 0), (TEMP_TOPIC, 0), (BUBBLE_TOPIC, 0), (OZON_TOPIC, 0), (UVL_TOPIC, 0)]
version = 1.1
auth = {'username': MQTT_USER, 'password': MQTT_PASS}

Bubble_intensity = {1: "Lav", 2: "Middels", 3: "Høy"}
heater_action = {4: "idle", 3: "heating"}

# ----------------------- Helper Functions ----------------------- #
def get_nonce():
    letters = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(32))

def md5_encrypt(value):
    return hashlib.md5(value.encode('utf-8')).hexdigest()

def get_timestamp():
    return round(time.time())

# ----------------------- API Functions ----------------------- #
def get_token():
    body = {"account": APP_EMAIL, "app_id": APP_ID,
            "password": APP_PASS, "brand": "", "registration_id": "", "push_type": "android",
            "lan_code": "EN", "country": ""}
    url = 'https://api.iot.the-mspa.com/api/enduser/get_token/'
    headers = HEADERS_TOKEN
    timestamp = get_timestamp()
    nonce = get_nonce()
    sign = md5_encrypt(APP_ID + ',' + APP_SECRET + ',' + nonce + ',' + str(timestamp))
    headers.update({"ts": str(timestamp), "nonce": nonce, "sign": sign.upper()})
    resp = requests.post(url, json=body, headers=headers)
    jsondata = resp.json()
    if resp.status_code != 200:
        raise Exception(f"Failed to get auth token: {resp.text}")
    token = jsondata["data"]["token"]
    HEADERS_POST["authorization"] = f"token {token}"
    HEADERS_GET["authorization"] = f"token {token}"

def get_devices():
    url = 'https://api.iot.the-mspa.com/api/enduser/devices/'
    headers = HEADERS_GET
    timestamp = get_timestamp()
    nonce = get_nonce()
    sign = md5_encrypt(APP_ID + ',' + APP_SECRET + ',' + nonce + ',' + str(timestamp))
    headers.update({"ts": str(timestamp), "nonce": nonce, "sign": sign.upper()})
    resp = requests.get(url, headers=headers)
    jsondata = resp.json()
    global device_id, product_id
    if resp.status_code != 200:
        raise Exception(f"Request failed: {resp.text}")
    device_id = jsondata["data"]["list"][0]["device_id"]
    product_id = jsondata["data"]["list"][0]["product_id"]

# ----------------------- MQTT Functions ----------------------- #
def publish_ha(topic, state, retain, attributes=False, attributes_json=None):
    publish.single(topic=topic, payload=state, qos=1, retain=retain, hostname=MQTT_BROKER, port=1883,
                   client_id='mspa_publisher', keepalive=60, auth=auth, protocol=mqtt.MQTTv311)
    if attributes:
        payload = {'Last-updated': str(datetime.now(pytz.timezone('Europe/Oslo'))), 'Script-version': str(version)}
        if attributes_json:
            payload.update(attributes_json)
        publish.single(topic=topic+'/attributes', payload=json.dumps(payload), qos=1,
                       hostname=MQTT_BROKER, port=1883, client_id='mspa_publisher', keepalive=60, auth=auth,
                       protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(all_topics)
    else:
        print(f"Bad connection: {rc}")

def on_disconnect(client, userdata, rc):
    exit(1)

def on_message(client, userdata, message):
    payload = str(message.payload.decode("utf-8"))
    topic = message.topic
    # map message to mSPA API commands
    if topic == TEMP_TOPIC:
        set_temp(float(payload)*2)
        publish_ha(TEMP_STATE, float(payload), True)
    elif topic == UVL_TOPIC:
        set_uvc(int(payload))
        publish_ha(UVL_STATE, int(payload), True)
    elif topic == OZON_TOPIC:
        set_ozone(int(payload))
        publish_ha(OZON_STATE, int(payload), True)
    elif topic == BUBBLE_TOPIC:
        if payload == "Av":
            set_bubbles(0)
        elif payload == "Lav":
            set_bubbles(1,1)
        elif payload == "Middels":
            set_bubbles(1,2)
        elif payload == "Høy":
            set_bubbles(1,3)
        else:
            set_bubbles(int(payload))
        publish_ha(BUBBLE_STATE, payload, True)
    elif topic == HEATER_TOPIC:
        set_heater(payload)
        publish_ha(HEATER_STATE, payload, True)

# ----------------------- Control Functions ----------------------- #
def set_temp(value):
    body = {"device_id": device_id, "product_id": product_id,
            "desired": f'{{"state": {{"desired": {{"temperature_setting": {value}}}}}}}'}
    post_command(body)

def set_ozone(value):
    body = {"device_id": device_id, "product_id": product_id,
            "desired": f'{{"state": {{"desired": {{"ozone_state": {value}, "filter_state": 1}}}}}}'}
    post_command(body)

def set_uvc(value):
    body = {"device_id": device_id, "product_id": product_id,
            "desired": f'{{"state": {{"desired": {{"uvc_state": {value}, "filter_state": 1}}}}}}'}
    post_command(body)

def set_heater(value):
    if value == 'heat':
        body = {"device_id": device_id, "product_id": product_id,
                "desired": '{"state": {"desired": {"heater_state": 1, "filter_state": 1}}}'}
    else:
        body = {"device_id": device_id, "product_id": product_id,
                "desired": '{"state": {"desired": {"heater_state": 0, "filter_state": 1}}}'}
    post_command(body)

def set_bubbles(state, intensity=0):
    if intensity == 0:
        body = {"device_id": device_id, "product_id": product_id,
                "desired": f'{{"state": {{"desired": {{"bubble_state": {state}, "filter_state": 1}}}}}}'}
    else:
        body = {"device_id": device_id, "product_id": product_id,
                "desired": f'{{"state": {{"desired": {{"bubble_state": {state}, "filter_state": 1, "bubble_level": {intensity}}}}}}}'}
    post_command(body)

def post_command(body):
    headers = HEADERS_POST.copy()
    timestamp = get_timestamp()
    nonce = get_nonce()
    sign = md5_encrypt(APP_ID + ',' + APP_SECRET + ',' + nonce + ',' + str(timestamp))
    headers.update({"ts": str(timestamp), "nonce": nonce, "sign": sign.upper()})
    resp = requests.post(COMMAND_URL, json=body, headers=headers)
    print(resp.text)

# ----------------------- Start MQTT Loop ----------------------- #
def start():
    client = mqtt.Client()
    client._client_id = 'mSPA_Bridge'
    client.username_pw_set(username=MQTT_USER, password=MQTT_PASS)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883, 90)
    client.loop_forever()

# ----------------------- Main ----------------------- #
get_token()
get_devices()
# Here you could start a thread to update states periodically
# threading.Thread(target=update_state_interval).start()
start()
