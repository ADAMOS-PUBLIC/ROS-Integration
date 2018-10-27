# -*- coding: utf-8 -*-

import requests, base64, json, os, time, sys, time
from adamos import AdamosClient
from ros import RosBridgeClient
from datetime import datetime
import cv2
import numpy as np

# --- CONFIG START ---
ADAMOS_URL = 'http://<tenant>.adamos-dev.com'
ADAMOS_TENANT = '<tenant>'
ADAMOS_DEVICE_NAME = 'Cobot'
ADAMOS_DEVICE_SERIAL = 'cobot-5428'
ROS_IP = '192.168.4.44:9090'
# --- CONFIG END ---


def transformCallback(m):
    """Receives transform messages from one of the following:
    1. base_to_cam_transform
    2. cam_to_tcp_transform
    3. base_to_tcp_transform
    Converts and sends measurements to ADAMOS
    """
    #m.msg.position     #.x, .y, .z
    #m.msg.orientation  #.x, .y, .z, .w

    if (m.topic == "/festo/cobotv1_1/base_to_cam_transform"):
        mtype = "base_to_cam_transform"
    elif (m.topic == "/festo/cobotv1_1/cam_to_tcp_transform"):
        mtype = "cam_to_tcp_transform"
    elif (m.topic ==  "/festo/cobotv1_1/base_to_tcp_transform"):
        mtype = "base_to_tcp_transform"
    else:
        return

    measurement = createMeasurement(m.topic, mtype)
    measurement[mtype+"_position"] = {
        "x": {
            "value": m.msg.position.x,
            "unit": "m"
        },
        "y": {
            "value": m.msg.position.y,
            "unit": "m"
        },
        "z": {
            "value": m.msg.position.z,
            "unit": "m"
        }
    }
    measurement[mtype+"_orientation"] = {
        "x": {
            "value": m.msg.orientation.x,
            "unit": "m"
        },
        "y": {
            "value": m.msg.orientation.y,
            "unit": "m"
        },
        "z": {
            "value": m.msg.orientation.z,
            "unit": "m"
        },
        "w": {
            "value": m.msg.orientation.w,
            "unit": "m"
        }
    }
    adamosClient.sendMeasurement(measurement)
    

def statusCallback(m):
    """Receives status messages containing stiffness_factor, mode, p1, joint_names and joint_positions.
    Converts and sends measurements and device updates to ADAMOS
    """
    #m.msg.stiffness_factor #float
    #m.msg.mode             #integer
    #m.msg.p1               #0,1
    #m.msg.joint_names      #string-array
    #m.msg.joint_positions  #float-array

    measurement = createMeasurement(m.topic, "cobot_status")
    measurement['status'] = {
        "stiffness_factor": {
            "value": m.msg.stiffness_factor
        },
        "mode": {
            "value": m.msg.mode
        },
        "claw": {
            "value": m.msg.p1
        }
    }

    # Add position values
    measurement['positions'] = {}
    positionNames = m.msg.joint_names
    position = m.msg.joint_positions
    for x in range(0, len(position)):
        measurement['positions'][positionNames[x]] = {
            "value": position[x],
            "unit": 'rad'
        }

    update = {
        "status": {
            "stiffness_factor": m.msg.stiffness_factor,
            "mode": m.msg.mode,
            "modeString": modeToString(m.msg.mode),
            "claw": m.msg.p1,
            "clasString": clawToString(m.msg.p1)
        }
    }

    adamosClient.sendMeasurement(measurement)
    adamosClient.updateDevice(update)


def imageCallback(m):
    """Receives messages containing the camera image.
    Converts and sends the image as a device update to ADAMOS.
    """
    convertedImage = convertImage(m.msg.data)

    update = {
        "camera": {
            "data": convertedImage,
            "format": m.msg.format
        }
    }
    
    # Save to local file
    #img_data = m.msg.data.encode('utf-8')
    #with open("video.jpg", "wb") as fh:
    #    fh.write(base64.decodebytes(img_data))

    adamosClient.updateDevice(update)


def createMeasurement(topic, mtype):
    """Create a measurement object that can be sent to ADAMOS

    :param str topic: Name of the topic the message came from
    :param str mtype: Type of the measurement
    :return dict: newly created measurement object
    """
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    measurement = {
        "topic": topic,
        "type": mtype,
        "source": { "id": adamosClient.DEVICE_ID },
        "time": timestamp
    }
    return measurement


def modeToString(mode):
    """Converts the status mode to a string representation
    :param int mode: mode value to be converted
    :return string: string representation of the mode
    """
    if (mode == 1):
        return "BALANCER"
    elif (mode == 2):
        return "RUN"
    elif (mode == 3):
        return "ERROR"
    elif (mode == 4):
        return "COLLISION_DETECTED"
    else:
        return mode


def clawToString(claw):
    """Converts the claw value (p1) to a string representation
    :param int claw: claw value to be converted
    :return string: string representation of the claw
    """
    if (claw == 1.0):
        return "CLOSED"
    if (claw < 1.0):
        return "OPEN"

def convertImage(rawImage):
    # Read image
    inputImageDecoded = base64.b64decode(rawImage)
    nparr = np.frombuffer(inputImageDecoded, dtype="int8")
    bayer = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE | cv2.IMREAD_ANYDEPTH)

    # Convert and resize
    rgb = cv2.cvtColor(bayer, cv2.COLOR_BAYER_BG2BGR)
    small = cv2.resize(rgb, (0,0), fx=0.5, fy=0.5) 

    # Output as base64
    retval, buffer = cv2.imencode('.jpg', small)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

    return jpg_as_text



"""----------------------------------
Main method
1. Connect to ADAMOS and to ROS
2. Subscribe to topics with callbacks
 """
try:
    # Connect to ADAMOS with (URL, tenant-name, device-serial)
    adamosClient = AdamosClient(ADAMOS_URL, ADAMOS_TENANT, ADAMOS_DEVICE_NAME, ADAMOS_DEVICE_SERIAL)
    adamosClient.connect()

    # Connect to ROS with IP
    rosClient = RosBridgeClient('ws://' + ROS_IP)
    rosClient.connect()

    # Subscribe to ROS topic with (topic-name, interval-ms, callback)
    rosClient.subscribe('/festo/cobotv1_1/festo_status', 1000, statusCallback)
    rosClient.subscribe('/festo/cobotv1_1/base_to_cam_transform', 1000, transformCallback)
    rosClient.subscribe('/festo/cobotv1_1/cam_to_tcp_transform', 1000, transformCallback)
    rosClient.subscribe('/festo/cobotv1_1/base_to_tcp_transform', 1000, transformCallback)
    rosClient.subscribe('/festo/cobotv1_1/cobot_wrist_cam/image_raw/compressed', 2000, imageCallback)


    while (True):
        time.sleep(1)

except KeyboardInterrupt:
    rosClient.close()
