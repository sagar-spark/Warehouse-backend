import json
import traceback
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from wms_backend.utils.http_responses import respond_success, respond_error
from django.db import connection

from infra.models import VendorUserToken, Vendor, VendorUsers, VendorExternalIntegration
from infra.models import WarehouseUsers, WarehouseUserToken
from infra.models import WarehouseMaster, WarehouseShelves, WarehouseBinsAndTrolley
from infra.models import SQLQueries, StockMoveQ, Inventory

from uuid import uuid4

import infra.controllers.userManagement as user
import infra.controllers.warehouseManagement as wh
import infra.controllers.orders as od
import infra.controllers.invoices as inv
import infra.controllers.emailServices as em

import infra.controllers.payments as pm

# Create your views here.
@csrf_exempt
@require_http_methods(["GET"])
def live_status(request):
    success = {"status": 200, "message": "server up & running"}

    if request.method == "GET":
        return HttpResponse(
            json.dumps(success),
            status=success["status"],
            content_type="application/json",
        )


@csrf_exempt
@require_http_methods(["GET"])
def vendorAddressDelete(request):

    try:
        addressId = request.GET.get("addressId")
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        update = vendor.deleteAddress(addressId)
        return respond_success("Deleted Successfully")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def vendorAddressAdd(request):
    try:
        request_data = json.loads(request.body)

        address = request_data["address"]

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        update = vendor.appendAddress(address)
        return respond_success("Added successfully")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def warehouseUserSignup(request):

    # Warehouse users are the users who will be managing the warehouse
    # on a day to day basis. One of them could be assigned to

    return user.userSignup(request, "warehouse")

@csrf_exempt
@require_http_methods(["POST"])
def warehouseUserAddition(request):

    # Warehouse users are the users who will be managing the warehouse
    # on a day to day basis. One of them could be assigned to

    request_data = json.loads(request.body)
    if request_data['warehouseId'] is None:
        return respond_error("Want to add a user - please specify the warehouse", status=404)

    return user.userSignup(request, "warehouse")


@csrf_exempt
@require_http_methods(["POST"])
def vendorUserSignup(request):

    return user.userSignup(request, "vendor")

@csrf_exempt
@require_http_methods(["POST"])
def vendorSignup(request):

    try:
        request_data = json.loads(request.body)

        vendorId = str(uuid4())
        payload = request_data.get("payload")
        address = request_data.get("address")
        billing = request_data.get("billing")

        vendor = Vendor(
            vendorId=vendorId,
            payload=payload,
            address=address,
            billing=billing
        )
        vendor.save()
        return respond_success(vendorId)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def vendorLogin(request):

    return user.userLogin(request, "vendor")


@csrf_exempt
@require_http_methods(["POST"])
def warehouseLogin(request):

    return user.userLogin(request, "warehouse")

@csrf_exempt
@require_http_methods(["POST"])
def adminLogin(request):

    return user.userLogin(request, "warehouse", admin=True)



@csrf_exempt
@require_http_methods(["POST"])
def validateAccessToken(request):

    return user.validateLoginToken(request)


@csrf_exempt
@require_http_methods(["POST"])
def forgotPassword(request):

    return em.resetPasswordEmailLink(request)


@csrf_exempt
@require_http_methods(["POST"])
def resetPassword(request):

    return em.resetPassword(request)



@csrf_exempt
@require_http_methods(["GET"])
def delete_expired_tokens(request):

    VendorUserToken.delete_old_records()
    WarehouseUserToken.delete_old_records()
    return HttpResponse(
        status=202
    )

@csrf_exempt
@require_http_methods(["POST"])
def getCurrentUserDetails(request):

    try:
        userId = request.META.get("auth").get("token").userId
        return respond_success(userId.asJson())
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def getCurrentVendorDetails(request):

    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")

        try:
            vendor = Vendor.objects.get(id=vendorId)
            external = None
            try:
                ei = VendorExternalIntegration.objects.get(vendorId=vendor)
                external = {
                    "external": ei.asJson()
                }
            except VendorExternalIntegration.DoesNotExist as e:
                external = {}
            if vendor is not None:
                vendor = vendor.asJson()
                vendor.update(external)
                return respond_success(vendor)
            else:
                return respond_error("Vendor does not exist", status=404)
        except Exception as e:
            print (traceback.format_exc())
            return respond_error("Vendor does not exist", status=404)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

@csrf_exempt
@require_http_methods(["GET"])
def getAllVendors(request):

    vendors = Vendor.objects.all()
    resp = []

    for vendor in vendors:
        v = vendor.asJson()
        try:
            ei = VendorExternalIntegration.objects.get(vendorId=vendor)
            v["ei"] = ei.asJson()
        except VendorExternalIntegration.DoesNotExist as e:
            v["ei"] = None
        resp.append(v)

    return respond_success(resp)

@csrf_exempt
@require_http_methods(["GET"])
def getWarehouseDetails(request):

    houses = []
    warehouseObjects = WarehouseMaster.objects.all()
    for warehouse in warehouseObjects:
        houses.append(warehouse.asJson())

    retObj = {
        "payload": houses
    }
    return respond_success(retObj)


@csrf_exempt
@require_http_methods(["GET"])
def getDynamicMenuVendor(request):
    pass


@csrf_exempt
@require_http_methods(["GET"])
def getAllWarehouseObjects(request):

    return wh.getAllWarehouseObjects(request)


@csrf_exempt
@require_http_methods(["POST"])
def addWarehouse(request):

    return wh.addWarehouse(request)


@csrf_exempt
@require_http_methods(["POST"])
def addWarehouseZones(request):

    return wh.addWarehouseZones(request)


@csrf_exempt
@require_http_methods(["POST"])
def addWarehouseLocationsAndShelves(request):

    return wh.addWarehouseLocationsAndShelves(request)

@csrf_exempt
@require_http_methods(["POST"])
def addWarehouseBinsAndTrolleys(request):

    return wh.addWarehouseBinsAndTrolley(request)


@csrf_exempt
@require_http_methods(["POST"])
def getShelvingShelves(request):

    return wh.getShelvingShelves(request)

@csrf_exempt
@require_http_methods(["POST"])
def addShelvingLog(request):

    return wh.addShelvingLog(request)

@csrf_exempt
@require_http_methods(["POST"])
def getShelvingLog(request):

    return wh.getShelvingLog(request)

@csrf_exempt
@require_http_methods(["GET"])
def getInventoryItems(request):

    return wh.getInventoryItems(request)


@csrf_exempt
@require_http_methods(["GET"])
def getVendorsInventoryItems(request):
    try:
        page_seq = int(request.GET.get("page_seq", default=0))
        page_size = int(
            request.GET.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")

        if vendorId is None:
            return respond_error("VendorId is missing", status=404)

        vendor = None
        if vendorId is not None:
            try:
                vendor = Vendor.objects.get(id=vendorId)
            except Vendor.DoesNotExist as e:
                return respond_error("Vendor does not exist", status=404)

        filters = {}
        if vendorId is not None:
            filters["vendorId"] = vendor
        items = Inventory.objects.filter(**filters)
        count = items.count()
        startIndex = (max(0, page_seq - 1)) * page_size
        endIndex = min(startIndex + page_size, count)
        if startIndex > count:
            return respond_error(
                {"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

        objs = items[startIndex:endIndex]
        objs = [x.asJson() for x in objs]
        return respond_success({
            "totalCount": count,
            "pageNum": page_seq,
            "payloads": objs
        })

    except Exception as e:
        print(traceback.format_exc(), "+++++++++++++++++")
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def orderNotificationShopify(request, vendorId):

    return od.processOrdersShopify(request, vendorId)

@csrf_exempt
@require_http_methods(["POST"])
def addShopifyForVendors(request):

    return wh.addShopifyForVendors(request)

@csrf_exempt
@require_http_methods(["GET"])
def getVendorSkuFromInventory(request):

    return od.getVendorSkuFromInventory(request)

@csrf_exempt
@require_http_methods(["GET"])
def getOrderItems(request):

    return od.getOrderItems(request)

@csrf_exempt
@require_http_methods(["POST"])
def createCustomOrder(request):

    return od.createCustomOrder(request)

@csrf_exempt
@require_http_methods(["GET"])
def getOrderItemsByOrderId(request):

    return od.getOrderItemsByOrderId(request)

@csrf_exempt
@require_http_methods(["POST"])
def updateOrderItemByRowId(request):

    return od.updateOrderItemByRowId(request)

@csrf_exempt
@require_http_methods(["GET"])
def readNotification(request):

    return od.readNotification(request)

@csrf_exempt
@require_http_methods(["GET"])
def getAllNotifications(request):

    return od.getAllNotifications(request)

@csrf_exempt
@require_http_methods(["POST"])
def createShipping(request):

    return od.createShipping(request)

@csrf_exempt
@require_http_methods(["POST"])
def cancelOrderItems(request):

    return od.cancelOrderItems(request)

@csrf_exempt
@require_http_methods(["GET"])
def getShippingByAWB(request):

    return od.getShippingByAWB(request)

@csrf_exempt
@require_http_methods(["GET"])
def cronUpdateAwbs(request):

    return od.cronUpdateAwbs(request)


@csrf_exempt
@require_http_methods(["GET"])
def getAllWarehouseUsers(request):
    return user.getAllUsers(request, "warehouse")

@csrf_exempt
@require_http_methods(["GET"])
def getAllVendorUsers(request):

    return user.getAllUsers(request, "vendor")

@csrf_exempt
@require_http_methods(["POST"])
def markShippingAsDelivered(request):
    return od.markShippingAsDelivered(request)

@csrf_exempt
@require_http_methods(["POST"])
def assignDeliveryAgentToShipping(request):

    return od.assignDeliveryAgentToShipping(request);

@csrf_exempt
@require_http_methods(["GET"])
def getAllAWB(request):

    return od.getAllAWB(request)

@csrf_exempt
@require_http_methods(["POST"])
def generateDraftBill(request):

    return inv.generateDraftBill(request);

@csrf_exempt
@require_http_methods(["POST"])
def generateAlaCarteBill(request):

    return inv.generateAlaCarteBill(request);

@csrf_exempt
@require_http_methods(["POST"])
def approveBill(request):

    return inv.approveBill(request);

@csrf_exempt
@require_http_methods(["GET"])
def getAllBills(request):

    return inv.getAllBills(request)

@csrf_exempt
@require_http_methods(["GET"])
def getSubscriptionModelForVendor(request):

    return inv.getSubscriptionModelForVendor(request)

@csrf_exempt
@require_http_methods(["POST"])
def registerEmailBoxForAVendor(request):
    return em.registerEmailBoxForAVendor(request)

@csrf_exempt
@require_http_methods(["GET"])
def syncAllEmailsFromServer(request):
    return em.syncAllEmailsFromServer(request)

@csrf_exempt
@require_http_methods(["GET"])
def getVendorOrderEmails(request):
    return em.getVendorOrderEmails(request)

@csrf_exempt
@require_http_methods(["POST"])
def markVendorOrderEmailRead(request):
    return em.markVendorOrderEmailRead(request)

@csrf_exempt
@require_http_methods(["GET"])
def getSpecificEmailFromId(request):
    return em.getSpecificEmailFromId(request)

@csrf_exempt
@require_http_methods(["POST"])
def parseEmailBodyContent(request):
    return em.parseEmailBodyContent(request)

@csrf_exempt
@require_http_methods(["POST"])
def executePayment(request):
    return pm.executePayment(request)

@csrf_exempt
@require_http_methods(["POST"])
def initiatePayment(request):
    return pm.initiatePayment(request)

@csrf_exempt
@require_http_methods(["POST"])
def getTransactionsForABill(request):
    return pm.getTransactionsForABill(request)

@csrf_exempt
@require_http_methods(["POST"])
def refreshTransactionsForBill(request):
    return pm.refreshTransactionsForBill(request)

@csrf_exempt
@require_http_methods(["POST"])
def refreshTransactionForAllPendingBills(request):
    return pm.refreshTransactionForAllPendingBills(request)

@csrf_exempt
@require_http_methods(["GET"])
def getAllQueries(request):
    queries = SQLQueries.objects.all()
    queries = [x.asJson() for x in queries]
    return respond_success(queries)

@csrf_exempt
@require_http_methods(["POST"])
def addQuery(request):

    try:
        data = json.loads(request.body)

        active = data["active"]

        query = SQLQueries(
            payload=data,
            active=active
        )
        query.save()

        return respond_success(query.asJson())

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def setStatusQuery(request):
    data = json.loads(request.body)
    queryId = data["id"]
    active = data["active"]
    query = SQLQueries.objects.get(id=queryId)
    query.active = active
    query.save()
    return respond_success(query.asJson())

@csrf_exempt
@require_http_methods(["GET"])
def getAdminStats(request):
    queries = SQLQueries.objects.filter(active=True)
    resp = {}
    for query in queries:

        payload = query.payload
        context = payload["context"]
        if context not in resp:
            resp[context] = []

        mainQuery = payload["query"]
        cursor = connection.cursor()
        cursor.execute(mainQuery)
        columns = cursor.description
        results = [{columns[index][0]:column for index, column in enumerate(value)} for value in cursor.fetchall    ()]
        print (type(results))
        print (results)
        resp[context].append(
            {
                "name": payload["name"],
                "respLabel": payload["respLabel"],
                "imageUrl": payload["imageUrl"],
                "result": results
            }
        )
    print (resp)
    return respond_success(resp)

@csrf_exempt
@require_http_methods(["POST"])
def setNewPassword(request):
    return user.setNewPassword(request)

@csrf_exempt
@require_http_methods(["GET"])
def getLogsStocksInMoveQ(request):
    reqParams = request.GET
    id = int(reqParams.get("id", default=0))
    inventoryId = int(reqParams.get("inventoryId", default=0))
    shelved = int(reqParams.get("shelved", default=0))
    shelved = True if shelved > 0 else False

    filters = {}
    if id != 0:
        filters["id"] = id
    if inventoryId != 0:
        filters["inventoryId_id"] = inventoryId
    filters["shelvedBack"] = shelved

    objs = StockMoveQ.objects.filter(**filters)
    objs = [x.asJson() for x in objs]

    return respond_success(objs)

@csrf_exempt
@require_http_methods(["POST"])
def putStocksInMoveQ(request):
    try:
        body = json.loads(request.body)
        inventoryId = body["inventoryId"]
        quantity    = body["quantity"]
        movePayload = body["movePayload"]

        try:
            inventory = Inventory.objects.get(id=inventoryId)
            if inventory.moveQInitiated and not inventory.finishedQMove:
                return respond_error("Inventory already in movement", status=404)
            createMoveQ = StockMoveQ(
                inventoryId=inventory,
                userId=request.META.get("auth").get("token").userId,
                movePayload=movePayload,
                quantity=quantity,
                shelvedBack=False
            )
            createMoveQ.save()
            inventory.moveQInitiated = True
            inventory.alteredWithMoveQ = True
            inventory.finishedQMove = False
            inventory.save()
            return respond_success(createMoveQ.asJson())
        except Inventory.DoesNotExist as e:
            return respond_error("Inventory ID does not exist", status=404)
        return respond_success(body)
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def removeStocksInMoveQ(request):
    try:
        body = json.loads(request.body)
        id = body["id"]
        targetShelfId = body["targetShelfId"]
        targetBinId = body["targetBinId"]

        try:
            targetShelfId = WarehouseShelves.objects.get(qualifiedName=targetShelfId)
        except WarehouseShelves.DoesNotExist as e:
            targetShelfId = None
        try:
            targetBinId = WarehouseBinsAndTrolley.objects.get(qualifiedName=targetBinId)
        except WarehouseBinsAndTrolley.DoesNotExist as e:
            targetBinId = None
        if targetBinId is None and targetShelfId is None:
            return respond_error("Kuch to sahi dede bhai, khali fekega kya item ko", status=404)
        try:
            moveItem = StockMoveQ.objects.get(id=id)
            if moveItem.shelvedBack:
                return respond_error("This item is already shelved back.", status=404)
            moveItem.targetShelfId = targetShelfId
            moveItem.targetBinId = targetBinId
            moveItem.shelvedBack = True
            moveItem.save()

            if targetShelfId is not None:
                moveItem.inventoryId.allocatedShelfId = targetShelfId
            if targetBinId is not None:
                moveItem.inventoryId.allocatedBinId = targetBinId
            moveItem.inventoryId.finishedQMove = True
            moveItem.inventoryId.save()

            return respond_success(moveItem.asJson())

        except StockMoveQ.DoesNotExist as e:
            return respond_error("StockMoveQ id does not exist", status=404)
        return respond_success(body)
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

