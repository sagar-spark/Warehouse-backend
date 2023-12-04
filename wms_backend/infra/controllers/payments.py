# Author: CP

from wms_backend.utils.http_responses import respond_success, respond_error
from infra.models import Transactions, Invoices

from uuid import uuid4

import os, json, requests, traceback

#ACCESS_TOKEN = "rLtt6JWvbUHDDhsZnfpAhpYk4dxYDQkbcPTyGaKp2TYqQgG7FGZ5Th_WD53Oq8Ebz6A53njUoo1w3pjU1D4vs_ZMqFiz_j0urb_BH9Oq9VZoKFoJEDAbRZepGcQanImyYrry7Kt6MnMdgfG5jn4HngWoRdKduNNyP4kzcp3mRv7x00ahkm9LAK7ZRieg7k1PDAnBIOG3EyVSJ5kK4WLMvYr7sCwHbHcu4A5WwelxYK0GMJy37bNAarSJDFQsJ2ZvJjvMDmfWwDVFEVe_5tOomfVNt6bOg9mexbGjMrnHBnKnZR1vQbBtQieDlQepzTZMuQrSuKn-t5XZM7V6fCW7oP-uXGX-sMOajeX65JOf6XVpk29DP6ro8WTAflCDANC193yof8-f5_EYY-3hXhJj7RBXmizDpneEQDSaSz5sFk0sV5qPcARJ9zGG73vuGFyenjPPmtDtXtpx35A-BVcOSBYVIWe9kndG3nclfefjKEuZ3m4jL9Gg1h2JBvmXSMYiZtp9MR5I6pvbvylU_PP5xJFSjVTIz7IQSjcVGO41npnwIxRXNRxFOdIUHn0tjQ-7LwvEcTXyPsHXcMD8WtgBh-wxR8aKX7WPSsT1O8d8reb2aR7K3rkV3K82K_0OgawImEpwSvp9MNKynEAJQS6ZHe_J_l77652xwPNxMRTMASk1ZsJL"
ACCESS_TOKEN = "WIXcBiUL-_tBm3tZtZ1XV9lxlPeabjaOvLRPbmkBT4uH2x4Sq265CAUJswU_DLCDX4rR8HWfzTp6znBckrLQhFY-TJG8Lfqto0McqyIDFxqICJcQaJcSSOe9pZpQkv4Nlx3GMKdXm-AGLvorcr1_yVqrC_qDU1z-YmMfUopkR_b075BxA2Qhf7Y2YPpm4b3I-0L-ERZ1MgzLZ-AJ7xfEgn0fRoHVqcXjBuXLdPHHySdGhtYXghKRZcd5ZGz__F7J9IFaKJaGWtcYSFCQGchYrv1826e6H77cIX-IlepisSm122kzqqFTmaLR9do336uQA1IXrezLfMrW_QmbmgOtsQwz-p6unS5q3PT97Db35zb5d1ubJCEjlAZogklvlRZ-M3CHyAcNaraKz7E7kicM9RCdMfNsnKZqdHFfTVhQSN1GhdKZch7gPsjXgWk-WCHAKx13kpdbIrvOQiY9sVbDhuLOV8r3hgwLDeag6Y_1xTl8gQ0TS7kDJ0zumTe4h8noKfvB5QQuyaWYeo2VM6Cv2370TYpXhHwwoVXFHLXovqUYyFKVwnIOsIjMyCe2L3W_R6LBsXW0JJcYKy8rBOYRp3bfwKCdl3pOK7kksUDmL-OBk38RmRBBau2jPdOskU85M0pe4dYG8LJkHR88a-_cUj7RZSz9PKQDdEOYdGQzkVoCKIYo8na9OlWFMtfn-9LJp14bPQ"

#BASE_URL = "https://apitest.myfatoorah.com"
BASE_URL = "https://api.myfatoorah.com"

def getHeaders():
    headers = {
        #"Authorization": "Bearer {}".format(os.environ.get("PG_ACCESS_TOKEN", ACCESS_TOKEN)),
        "Authorization": "Bearer {}".format(ACCESS_TOKEN),
        "Content-Type": "application/json"
    }
    return headers

def executeCheckPaymentStatus(payload):
    ENDPOINT = "/v2/GetPaymentStatus"
    url = "{}{}".format(BASE_URL, ENDPOINT)
    payload = json.dumps(payload)
    resp = requests.request("POST", url=url, headers=getHeaders(), data=payload)
    return resp.json()

def executeWithFatoorah(payload):
    ENDPOINT = "/v2/ExecutePayment"
    url = "{}{}".format(BASE_URL, ENDPOINT)
    payload = json.dumps(payload)
    resp = requests.request("POST", url=url, headers=getHeaders(), data=payload)
    
    return resp.json()

def initiatePaymentWithFatoorah(payload):
    ENDPOINT = "/v2/InitiatePayment"

    url = "{}{}".format(BASE_URL, ENDPOINT)
    payload = json.dumps(payload)
    headers = getHeaders()

    resp = requests.request("POST", url=url, headers=headers, data=payload)

    return resp.json()

def initiatePayment(request):
    try:
        data = json.loads(request.body)
        billId = data["billId"]
        try:
            invoice = Invoices.objects.get(billId=billId)
        except Invoices.DoesNotExist as e:
            return respond_error({"msg": "Bill Id does not exist"})
        t = Transactions(
            transactionId = str(uuid4()),
            invoiceIdInternal = invoice,
            invoiceIdExternal = "",
            status = "CREATED",
            payload = {},
            dump = {}
        )
        t.save()
        billTotal = str(invoice.billTotal["total"])
        payload = {
            "InvoiceAmount": billTotal,
            "CurrencyIso": "KWD"
        }
        resp = initiatePaymentWithFatoorah(payload)
        print (resp)
        t.dump["initiate"] = resp
        t.save()
        success = resp["IsSuccess"]
        respObj = {}
        if success:
            respObj = {
                "internalTransactionId": t.transactionId,
                "invoice": invoice.asJson(),
                "paymentMethods": resp["Data"]["PaymentMethods"]
            }
            return respond_success(respObj)
        else:
            return respond_error(respObj)
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

def executePayment(request):
    try:
        data = json.loads(request.body)
        internalTransactionId = data["internalTransactionId"]
        paymentMethodId = data["paymentMethodId"]
        try:
            t = Transactions.objects.get(transactionId = internalTransactionId)
            # Check through existing payment method Id and see thats a legit entry from the user
            payload = {
                "InvoiceValue": t.invoiceIdInternal.billTotal["total"],
                "PaymentMethodId": paymentMethodId,
                "CustomerReference": "{}//{}".format(t.transactionId, t.invoiceIdInternal.id)
            }
            resp = executeWithFatoorah(payload)
            print (payload["CustomerReference"], resp)
            t.dump["execute"] = resp
            t.invoiceIdExternal = resp["Data"]["InvoiceId"]
            t.save()
            if resp["IsSuccess"]:
                respObj = {
                    "transaction": t.asJson(),
                    "paymentDetails": resp["Data"]
                }
                return respond_success(respObj)
            print (resp)
            return respond_error({"msg": "Some error", "resp": resp})
        except Transactions.DoesNotExist as e:
            return respond_error({"msg": "Transaction Id does not exist"})
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

def getTransactionsForABill(request):
    try:
        data = json.loads(request.body)
        billId = data["billId"]
        try:
            invoice = Invoices.objects.get(billId=billId)
            ts = Transactions.objects.filter(invoiceIdInternal=invoice)
            ts = [t.asJson() for t in ts]
            return respond_success(ts)
        except Invoices.DoesNotExist as e:
            return respond_error({"msg": "Bill Id does not exist"})
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

def refreshBill(invoice):
    ts = Transactions.objects.filter(invoiceIdInternal=invoice)
    for t in ts:
        if t.status == "PAID":
            continue
        payload = {
            "Key": t.invoiceIdExternal,
            "KeyType": "InvoiceId"
        }
        resp = executeCheckPaymentStatus(payload)
        if resp["IsSuccess"] and resp["Data"]["InvoiceStatus"] == "Paid":
            t.status = "PAID"
            t.save()
            invoice.status = "PAID"
            invoice.save()

def refreshTransactionsForBill(request):
    try:
        data = json.loads(request.body)
        billId = data["billId"]
        try:
            invoice = Invoices.objects.get(billId=billId)
            refreshBill(invoice)
            return respond_success("Ok")
        except Invoices.DoesNotExist as e:
            return respond_error({"msg": "Bill Id does not exist"})
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

def refreshTransactionForAllPendingBills(request):
    try:
        invoices = Invoices.objects.exclude(status="PAID")
        for invoice in invoices:
            refreshBill(invoice)
        return respond_success("Ok")
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")


