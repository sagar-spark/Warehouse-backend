#Author: CP

import os
import json
import requests

from uuid import uuid4
from utils import barcode


DELIVERY_BASEURL = "https://apis-delivery.connectco.me"
DELIVERY_LOGINURL = "/infra/userlogin"
DELIVERY_CREATEORDERURL = "/infra/createOrder"
DELIVERY_GETAWB = "/infra/getAllOrders"

def authOauth2():
    client_id = os.environ.get("DELIVERY_USER", None)
    client_secret = os.environ.get("DELIVERY_PASS", None)

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "client_id": client_id,
        "client_secret": client_secret
    }
    resp = json.loads(requests.request(
        "POST",
        DELIVERY_BASEURL + DELIVERY_LOGINURL,
        headers=headers,
        data=payload
    ).text)
    return resp["access_token"]


def trackAwb(payload):
    accessToken = authOauth2()
    headers = {
        "Content-Type": "application/json",
        "Authorisation": accessToken
    }
    resp = json.loads(
        requests.request(
            "GET",
            DELIVERY_BASEURL + DELIVERY_GETAWB + "?shipmentId="+payload,
            headers=headers
        ).text
    )
    resp = resp["orders"][0]
    return resp


def createOrder(payload):
    accessToken = authOauth2()
    print (accessToken)
    print (payload)
    payload["vendorId"] = 1
    headers = {
        "Content-Type": "application/json",
        "Authorisation": accessToken
    }
    resp = json.loads(
        requests.request(
            "POST",
            DELIVERY_BASEURL + DELIVERY_CREATEORDERURL,
            headers=headers,
            data=json.dumps(payload)
        ).text
    )
    print (resp)
    return resp["shipmentId"]

def getAwbNumber(payload):
    awb = createOrder(payload)
    resp = barcode.handleBarCode(awb, "AWB")
    bc = None
    if resp["uploaded"]:
        bc = resp["path"]
    return awb, bc

