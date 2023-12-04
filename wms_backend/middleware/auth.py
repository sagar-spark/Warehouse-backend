#Author: CP

import json
import traceback
from uuid import UUID

from infra.models import VendorUserToken
from infra.models import WarehouseUserToken
from wms_backend.utils.http_responses import respond_success, respond_error

class Auth:

    def __init__(self, get_response):
        self.get_response = get_response

        self.nonAuthUrls = [

            "/infra/delete-tokens/",

            "/infra/register-vendor/",

            "/infra/validate-access-token/",

            "/infra/vendor-user-signup/",
            "/infra/vendor-login/",

            "/infra/warehouse-user-signup/",
            "/infra/warehouse-login/",
            "/infra/admin-login/",

            "/infra/live-status/",

            "/infra/orderNotificationShopify/",

            "/infra/generateDraftBill/",

            "/infra/syncAllEmailsFromServer/",

            "/infra/refreshTransactionForAllPendingBills/",
            "/infra/cronUpdateAwbs/",
            
            "/infra/forgot-password-email/",
            "/infra/reset-password/",
        ]

        self.authUrlMapping = {
            "vendorUser": [
                # ASN
                "/inbound/get-asn/",
                "/inbound/add-asn/",
                "/inbound/get-all-asn/",

                # GRN
                "/inbound/confirm-grn/",
                "/inbound/get-all-grn/",
                "/inbound/get-grn/",

                # SKUs
                "/inbound/uploadSkus/",
                "/inbound/getVendorSkuById/",
                "/inbound/getAllVendorSKUs/",
                "/inbound/buildSKUsFromShopify/",
                "/infra/getVendorSkuFromInventory/",

                # Retailer
                "/inbound/add-retailer/",
                "/inbound/toggle-retailer/",
                "/inbound/get-all-retailers/",

                # SELF: VENDOR
                "/infra/get-vendor-user-details/",
                "/infra/getAllVendorUsers/",
                "/infra/get-vendor-details/",
                "/infra/vendor-address-add/",
                "/infra/vendor-address-del/",

                # WAREHOUSE & ADMINS
                "/infra/get-warehouse-details/",
                "/inbound/get-stats/",

                #"/inbound/add-grn/",

                # ORDER MANAGEMENT
                "/infra/getVendorSkuFromInventory/",
                "/infra/getOrderItems/",
                "/infra/createCustomOrder/",

                # NOTIFICATIONS
                "/infra/readNotification/",
                "/infra/getAllNotifications/",

                # INVOICES
                "/infra/getAllBills/",
                "/infra/getSubscriptionModelForVendor/",

                # INVENTORY
                "/infra/getVendorInventoryItems/",

                # PAYMENT LINKS
                "/infra/initiatePayment/",
                "/infra/executePayment/",
                "/infra/getTransactionsForABill/",
                "/infra/refreshTransactionsForBill/",

            ],
            "warehouseUser": [

                # ADMIN STUFF
                "/infra/addShopifyForVendors/",
                "/infra/setNewPassword/",

                # ASN
                "/inbound/get-asn/",
                "/inbound/get-all-asn/",

                # GRN
                "/inbound/add-grn/",
                "/inbound/get-all-grn/",
                "/inbound/get-grn/",

                # WAREHOUSE & ADMINS
                "/infra/get-warehouse-details/",
                "/infra/getAllVendors/",
                "/infra/getAllVendorUsers/",
                "/inbound/get-stats/",

                # WAREHOUSE MANAGEMENT
                "/infra/get-all-warehouse-objects/",

                "/infra/warehouse-user-addition/",
                "/infra/getAllWarehouseUsers/",

                "/infra/add-warehouse-master/",
                "/infra/add-warehouse-zones/",
                "/infra/add-warehouse-locations-shelves/",
                "/infra/add-warehouse-bins-trolleys/",

                # INVENTORY
                "/inbound/getAllVendorSKUs/",

                "/infra/getShelvingShelves/",
                "/infra/addShelvingLog/",
                "/infra/getShelvingLog/",
                "/infra/getInventoryItems/",

                # Stock Move Q
                "/infra/getLogsStocksInMoveQ/",
                "/infra/putStocksInMoveQ/",
                "/infra/removeStocksInMoveQ/",

                # ORDER MANAGEMENT
                "/infra/getVendorSkuFromInventory/",
                "/infra/getOrderItems/",
                "/infra/createCustomOrder/",

                "/infra/getOrderItemsByOrderId/",
                "/infra/updateOrderItemByRowId/",
                "/infra/cancelOrderItems/",
                "/infra/createShipping/",
                "/infra/getShippingByAWB/",
                "/infra/assignDeliveryAgentToShipping/",
                "/infra/markShippingAsDelivered/",
                "/infra/getAllAWB/",

                # NOTIFICATIONS
                "/infra/readNotification/",
                "/infra/getAllNotifications/",

                # INVOICES
                "/infra/generateAlaCarteBill/",
                "/infra/approveBill/",
                "/infra/getAllBills/",

                # INVOICES
                "/infra/getTransactionsForABill/",
                "/infra/refreshTransactionsForBill/",

                # EMAILS
                "/infra/registerEmailBoxForAVendor/",
                "/infra/getVendorOrderEmails/",
                "/infra/markVendorOrderEmailRead/",
                "/infra/getSpecificEmailFromId/",
                "/infra/parseEmailBodyContent/",

                # Queries
                "/infra/getAllQueries/",
                "/infra/addQuery/",
                "/infra/getAdminStats/",
                "/infra/setStatusQuery/",
            ]
        }

    def __call__(self, request):
        if "/infra/orderNotificationShopify/" in request.path:
            response = self.get_response(request)
            return response

        if request.path not in self.nonAuthUrls:  # RegEx based login

            self.process_auth(request)
            if "auth" not in request.META:
                return respond_error("Forbidden", status=403)
            auth = request.META["auth"]["authResult"]
            if not auth:
                print ("Not authorised with credentials")
                return respond_error("Not Authorised", status=401)

            authType = request.META["auth"]["authType"]
            if request.path not in self.authUrlMapping[authType]:
                print ("Forbidden resource", request.path)
                return respond_error("Forbidden resource", status=403)

        response = self.get_response(request)
        return response

    def getAccessToken(self, request):
        accessToken = request.headers.get("Authorization")
        return accessToken

    def getAuthTokenDetails(self, accessToken):

        v = accessToken[-1] == "v"
        w = accessToken[-1] == "w"

        tokenStr = accessToken[:-2]
        token = None
        authResult = {}

        if v:
            # Vendor
            try:
                token = VendorUserToken.objects.get(id=tokenStr)
                authResult["authType"] = "vendorUser"
            except VendorUserToken.DoesNotExist as e:
                print ("Vendor Token Does not exist: {accessToken}")
                return {"authResult": False}
        elif w:
            # Warehouse
            try:
                token = WarehouseUserToken.objects.get(id=tokenStr)
                authResult["authType"] = "warehouseUser"
            except WarehouseUserToken.DoesNotExist as e:
                print ("Warehouse Token Does not exist: {accessToken}")
                return {"authResult": False}

        tokenJson = token.asJson(update=True) if token is not None else {}
        flag = True
        for key in tokenJson.keys():
            if tokenJson[key] is None or len(str(tokenJson[key])) == 0:
                flag = False
                break

        authResult["authResult"] = flag
        authResult["tokenObject"] = tokenJson
        authResult["token"] = token
        return authResult

    def processToken(self, token):
        obj = {}
        if token is None:
            obj["valid"] = False
            return obj
        mainToken = token[:-2]
        if token[-2:] in ["-v", "-w"]:
            obj["valid"] = True
        else:
            obj["valid"] = False
        return obj

    def process_auth(self, request):

        accessToken = self.getAccessToken(request)

        tokenObjValidation = self.processToken(accessToken)
        if not tokenObjValidation["valid"]:
            request.META.update( {"results": {"authResult": False}} )
            return None

        js = { "auth": self.getAuthTokenDetails(accessToken) }
        request.META.update(js)

        return None

