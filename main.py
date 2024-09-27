REGISTERS = [("tag_{}".format(i), 199 + i) for i in range(1, 21)]
print(REGISTERS)
import os
import minimalmodbus
import requests
import serial
from serial import Serial
import time
import serial.tools.list_ports
import logging.handlers
from logging.handlers import TimedRotatingFileHandler
import sys
from datetime import datetime
import schedule
import threading

# region Rotating Logs
# dirname = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    dirname = os.path.dirname(sys.executable)
else:
    dirname = os.path.dirname(os.path.abspath(__file__))

log_level = logging.INFO
FORMAT = '{asctime} {levelname:2} {module}:{lineno} {message}'
SEND_DATA = False
IP = ''
logFormatter = logging.Formatter(FORMAT, style='{')
log = logging.getLogger("LOGS")
M_NAME = 'KFM'
TELEMETRY_SAMPLE_RATE = 60
VALUE_SAMPLE_RATE = 1
SEND_DATA_API = False

# checking and creating logs directory here
if not os.path.isdir("./logs"):
    log.info("[-] logs directory doesn't exists")
    try:
        os.mkdir("./logs")
        log.info("[+] Created logs dir successfully")
    except Exception as e:
        log.error(f"[-] Can't create dir logs Error: {e}")

fileHandler = TimedRotatingFileHandler(os.path.join(dirname, f'logs/app_log'),
                                       when='midnight', interval=1)

# fileHandler = TimedRotatingFileHandler(f"D:/HIS_LOGS", when='midnight', interval=1)
fileHandler.setFormatter(logFormatter)
fileHandler.suffix = "%Y-%m-%d.log"
log.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
log.addHandler(consoleHandler)
log.setLevel(log_level)
SEND_DATA = True
HOST_TB = 'lcaforyou.com'
HEADERS = {"Content-Type": "application/json"}
ACCESS_TOKEN = 'syhJCoZ5tzywtpdEqz7m'

#COM_PORT = "/dev/serial/by-id/usb-Silicon_Labs_CP2103_USB_to_UART_Bridge_Controller_0001-if00-port0"
COM_PORT = "COM3"
REGISTERS = [('tag_1', 200), ('tag_2', 201), ('tag_3', 202), ('tag_4', 203), ('tag_5', 204), ('tag_6', 205),
             ('tag_7', 206), ('tag_8', 207), ('tag_9', 208), ('tag_10', 209), ('tag_11', 210), ('tag_12', 211),
             ('tag_13', 212), ('tag_14', 213), ('tag_15', 214), ('tag_16', 215), ('tag_17', 216), ('tag_18', 217),
             ('tag_19', 218), ('tag_20', 219)]
GL_PAYLOAD = {}
GL_PERMANENT = {}

SAVE = False


# def get_serial_port():
#     try:
#         ports = serial.tools.list_ports.comports()
#         usb_ports = [p.device for p in ports if "USB" in p.description]
#         log.info(usb_ports)
#         if len(usb_ports) < 1:
#             raise Exception("Could not find USB ports")
#         return usb_ports[0]
#     except Exception as e:
#         log.info(f"[-] Error Can't Open Port {e}")
#         return None


def get_serial_port():
    try:
        ports = serial.tools.list_ports.comports()
        # Only check for COM ports
        usb_ports = [p.device for p in ports if "COM" in p.device]
        log.info(usb_ports)
        if len(usb_ports) < 1:
            raise Exception("Could not find COM ports")
        return usb_ports[0]
    except Exception as e:
     log.error(f"[-] Error Can't Open Port {e}")
    return None

def initiate_modbus():
    com_port = COM_PORT
    try:
        i = 1
        instrument = minimalmodbus.Instrument(com_port, i)
        instrument.serial.baudrate = 9600
        instrument.serial.bytesize = 8
        instrument.serial.parity = serial.PARITY_NONE
        instrument.serial.stopbits = 1
        instrument.serial.timeout = 3
        instrument.serial.close_after_each_call = True
        # log.info("Modbus ID Initialized: " + str(i))
        # Set mode to ASCII
        instrument.mode = minimalmodbus.MODE_RTU
        log.info(" Modbus ID Initialized: " + str(i))
        return instrument
    except Exception as e:
        log.error(f"Error : {e}")
        return None


def convert_to_signed_16bit(value):
    # If the value is greater than 32767, it's a negative number in two's complement
    return value - 65536 if value > 32767 else value


def post_data(payload):
    """posting an error in the attributes if the data is None"""
    global HEADERS
    url = f'http://{HOST_TB}/api/v1/{ACCESS_TOKEN}/telemetry'
    log.info(str(payload))
    if SEND_DATA:
        try:
            request_response = requests.post(url, json=payload, headers=HEADERS, timeout=2)
            log.info(f"[+] {request_response.status_code}")
        except Exception as e:
            log.error(f"{e}")


def threaded_post_data(payload):
    """This function runs `post_data` in a separate thread every 5 seconds."""
    while True:
        post_data(payload)
        time.sleep(5)  # Sleep for 5 seconds between each post


def get_machine_data():
    global GL_PAYLOAD, GL_PERMANENT, SAVE
    slave_id = 1
    # log.info(f"[+] Getting data for slave id {slave_id}")
    # try:

    data = []
    converted_data = []
    permanent_tags = []
    # for i in REGISTERS:
    mb_client = initiate_modbus()
    if mb_client:
        try:
            data = mb_client.read_registers(200, 40)
            for i in data:
                value = convert_to_signed_16bit(i)
                permanent_tags.append(value)
            p_tag_no = 1
            for i in permanent_tags:
                if i != 0:
                    GL_PERMANENT[f"tag_{p_tag_no}"] = i
                    p_tag_no += 1
            # post_data(GL_PERMANENT)
            trigger = mb_client.read_registers(198, 1)
            log.info(f"Trigger is : {trigger}")
            if trigger[0] == 1:
                time_ = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                GL_PAYLOAD["time_"] = time_
            if trigger[0] == 0:
                SAVE = False
            if trigger[0] and not SAVE:
                SAVE = True
                # reg_starting = 200
                # while reg_starting < 219:
                #     value = mb_client.read_registers(reg_starting, 2)
                #     data.append(value)
                #     reg_starting += 2
                data = mb_client.read_registers(200, 40)
                log.info(f"Data is {data}")
                # log.info(f"")
                # data[i[0]] = value[0]

                for i in data:
                    value = convert_to_signed_16bit(i)
                    converted_data.append(value)
                log.info(f"converted data : {converted_data}")
                # making payload
                tag_no = 1
                for i in converted_data:
                    if i != 0:
                        GL_PAYLOAD[f"trig_tag_{tag_no}"] = i
                        tag_no += 1

                post_data(GL_PAYLOAD)
            else:
                log.info("Trigger is not available")
            if SAVE:
                mb_client.write_register(198, 2)
                log.info("Trigger reset")
        except Exception as e:
            log.error(f"Error while reading registers : {e}")
            # data[i[0]] = None
    else:
        log.info("Check modbus connection")
    # time.sleep(0.5)
    # log.info(f"DATA IS : {data}")
    # return data


if __name__ == '__main__':
    # Create a thread for posting data every 5 seconds
    post_data_thread = threading.Thread(target=threaded_post_data, args=(GL_PERMANENT,), daemon=True)

    # Start the thread
    post_data_thread.start()

    while True:
        # Run your machine data function as usual
        get_machine_data()
        time.sleep(0.5)