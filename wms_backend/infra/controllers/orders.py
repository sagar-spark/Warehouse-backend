# Author: CP

import hmac, hashlib, base64, json
from wms_backend.utils.http_responses import respond_success, respond_error

import traceback
from django.conf import settings
from django.db.models import Q
from inbound.models import Vendor
from infra.models import Inventory, Orders, OrderItems, WarehouseMaster, WarehouseUsers, ShippingDetails
from utils import shopify as externalUpdate
from utils import notification, awb
from datetime import datetime


# import pdb; pdb.set_trace()

def getAllAWB(request):
    try:

        request_data = request.GET
        page_seq = int(request_data.get("page_seq", default=0))
        page_size = int(
            request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        filters = {}
        deliveryAgentId = request_data.get("delivery_agent_id", default=None)
        status = request_data.get("status", default=None)
        if deliveryAgentId is not None:
            try:
                user = WarehouseUsers.objects.get(email=deliveryAgentId)
                filters["deliveryAgent"] = user
            except WarehouseUsers.DoesNotExist as e:
                return respond_error("Delivery User Id is incorrect")
        if status is not None:
            filters["status"] = status

        agentAssigned = request_data.get("delivery_agent_assigned", default=None)
        if agentAssigned is None:
            pass
        elif agentAssigned.lower() == "true":
            filters["deliveryAgent__isnull"] = False
        else:
            filters["deliveryAgent__isnull"] = True

        items = ShippingDetails.objects.filter(**filters)
        count = items.count()

        startIndex = (max(0, page_seq - 1)) * page_size
        endIndex = min(startIndex + page_size, count)
        if startIndex > count:
            return respond_error({"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

        objs = items[startIndex:endIndex]
        objs = [x.asJson() for x in objs]
        return respond_success({
            "totalCount": count,
            "pageNum": page_seq,
            "payloads": objs
        })

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getShippingByAWB(request, manualAwb=None):
    try:
        if manualAwb is None:
            request_data = request.GET
            awbNumber = request_data.get("awbNumber", default=None)
        else:
            awbNumber = manualAwb
        updateTable = True
        try:
            shipping = ShippingDetails.objects.get(awbNumber=awbNumber)
            if shipping.status == "DELIVERED" or shipping.status == "CANCELLED":
                updateTable = False
            if updateTable:
                # Call the API to fetch the recent status and update the local table
                deliveryDetails = awb.trackAwb(shipping.awbNumber)

                # Step 1: Update ShippingDetails
                shipping.status = deliveryDetails["status"]
                shipping.save()

                # Step 2: Go through OrderItems and update their statuses
                for oi in shipping.orderItems:
                    tt = None
                    for s in deliveryDetails["statusHistory"]:
                        if s["status"] == deliveryDetails["status"]:
                            tt = s["datetime"]
                    newStatus = {
                        "flag": True,
                        "userId": {
                            "userId": "Delivery Partner"
                        },
                        "timestamp": tt
                    }
                    orderItem = OrderItems.objects.get(id=oi)
                    orderItem.itemStatus[shipping.status] = newStatus
                    orderItem.save()
                    pass
                pass
            return respond_success(shipping.asJson())
        except ShippingDetails.DoesNotExist as e:
            return respond_error("AWB Does Not exist", status=404)
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def cronUpdateAwbs(request):
    try:
        shipping = ShippingDetails.objects.filter(deliveryAgent_id__isnull=True).exclude(status="DELIVERED").exclude(
            status="CANCELLED")
        for ship in shipping:
            print("Checking: ", ship.awbNumber)
            getShippingByAWB(None, ship.awbNumber)
        return respond_success("OK")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")
    pass


def createShipping(request):
    try:
        data = json.loads(request.body)
        orderId = data["orderId"]
        order = None
        try:
            order = Orders.objects.get(id=orderId)
        except Orders.DoesNotExist as e:
            return respond_error("OrderId does not exist")
        orderItems = data["orderItems"]
        payload = data["payload"]
        direction = data["direction"]
        if not (direction == "IN" or direction == "OUT"):
            print("Direction not supported")
            return respond_error("Direction not supported")

        warehouseId = order.warehouseId_id
        warehouseId = 1 if warehouseId is None else warehouseId
        warehouse = WarehouseMaster.objects.get(id=warehouseId)
        awbPayload = {
            "pickLocation": {
                "street": warehouse.address["address"],
                "street2": "",
                "state": warehouse.address["state"],
                "country": warehouse.address["country"],
                "zip": warehouse.address["zip"]
            },
            "dropLocation": {
                "street2": "",
                "country": payload["to"]["shipping_address"]["country"],
                "zip": payload["to"]["shipping_address"]["zip"]
            },
            "receiverDetails": {
                "name": order.customer["name"],
                "email": order.customer["contact"]["email"],
                "phone": order.customer["contact"]["phone"]
            },
            "receiverKey": order.customer["contact"]["email"],
            "payload": {
                "orderItems": orderItems,
                "referenceOrderId": order.id
            }
        }
        if awbPayload["receiverKey"] is None:
            awbPayload["receiverKey"] = order.customer["name"]
        if "addressline" in payload["to"]["shipping_address"]:
            awbPayload["dropLocation"]["street"] = payload["to"]["shipping_address"]["addressline"]
        else:
            awbPayload["dropLocation"]["street"] = payload["to"]["shipping_address"]["address1"]
            awbPayload["dropLocation"]["street2"] = payload["to"]["shipping_address"]["address2"]
        if "state" in payload["to"]["shipping_address"]:
            awbPayload["dropLocation"]["state"] = payload["to"]["shipping_address"]["state"]
        else:
            awbPayload["dropLocation"]["state"] = payload["to"]["shipping_address"]["province"]
        awbNumber, barcode = awb.getAwbNumber(awbPayload)
        print("*************")
        print(awbNumber, barcode)
        print("*************")
        payload["barcode"] = barcode

        shipping = ShippingDetails(
            orderId=order,
            awbNumber=awbNumber,
            orderItems=orderItems,
            direction=direction,
            payload=payload,
            status="CREATED"
        )
        shipping.save()

        return respond_success(shipping.asJson())

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def cancelOrderItems(request):
    try:
        user = request.META.get("auth").get("token").userId
        userId = request.META.get("auth").get("tokenObject")

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        data = json.loads(request.body)

        orderItems = data["orderItems"]
        orderId = data["orderId"]
        payload = data["payload"]
        exchange = data["exchange"] == "1"

        filters = {}
        if vendor is not None:
            filters["vendorId"] = vendor
        filters["id"] = orderId

        try:
            order = Orders.objects.filter(**filters)

            order = Orders.objects.get(id=orderId)

            for item in orderItems:
                filters = {
                    "orderId": orderId,
                    "id": item
                }
                # Create Shipping
                awbPayload = {
                    "pickLocation": {
                        "street": payload["from"]["shipping_address"]["addressline"],
                        "street2": "",
                        "state": payload["from"]["shipping_address"]["state"],
                        "country": payload["from"]["shipping_address"]["country"],
                        "zip": payload["from"]["shipping_address"]["zip"]
                    },
                    "dropLocation": {
                        "street": payload["to"]["shipping_address"]["addressline"],
                        "street2": "",
                        "state": payload["to"]["shipping_address"]["state"],
                        "country": payload["to"]["shipping_address"]["country"],
                        "zip": payload["to"]["shipping_address"]["zip"]
                    },
                    "receiverDetails": {
                        "name": order.customer["name"],
                        "email": order.customer["contact"]["email"],
                        "phone": order.customer["contact"]["phone"]
                    },
                    "receiverKey": order.customer["contact"]["email"],
                    "payload": {
                        "orderItems": [item],
                        "referenceOrderId": order.id
                    }

                }

                aw, barcode = awb.getAwbNumber(awbPayload)
                payload["barcode"] = barcode
                shipping = ShippingDetails(
                    orderId=order,
                    awbNumber=aw,
                    orderItems=orderItems,
                    direction="IN",
                    payload=payload,
                    status="CREATED"
                )
                shipping.save()
                try:
                    orderItemObj = OrderItems.objects.filter(**filters)[0]
                    # orderItemObj = OrderItems.objects.get(id=item)
                    orderItemObjStatus = "exchange" if exchange else "cancelled"
                    orderItemObj.itemStatus[orderItemObjStatus] = {
                        "flag": True,
                        "userId": userId,
                        "shipping": shipping.asJson()
                    }
                    orderItemObj.recentStatus = "cancelled"
                    orderItemObj.save()

                    # If exchange = Create a new row item
                    if exchange:
                        newOrderItem = OrderItems(
                            orderId=orderItemObj.orderId,
                            itemStatus={
                                "exchange": {
                                    "flag": True,
                                    "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"),
                                    "userId": userId
                                },

                                "created": {
                                    "flag": True,
                                    "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"),
                                    "userId": userId
                                }
                            },
                            recentStatus="created",
                            itemPayload=orderItemObj.itemPayload,
                            warehouseId=orderItemObj.warehouseId
                        )
                        newOrderItem.save()
                    return respond_success(shipping.asJson())
                except OrderItems.DoesNotExist as e:
                    pass
        except Orders.DoesNotExist as e:
            print("Order: {}, Vendor: {}, OrderItems: {} - combination does not exist".format(orderId, vendorId,
                                                                                              orderItems))
            return respond_error("You are not allowed this orderId")

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def createCustomOrder(request):
    try:
        data = json.loads(request.body)
        vendor = None

        try:
            vendor = Vendor.objects.get(id=data["vendorId"])
        except Vendor.DoesNotExist as e:
            vendor = None

        if vendor is None:
            return respond_error("VendorId does not exist")

        user = request.META.get("auth").get("token").userId
        userId = request.META.get("auth").get("tokenObject")

        billAmount = 0
        inventories = []
        orderItems = []
        for item in data["items"]:

            amount = int(item["quantity"]) * float(item["price"])
            billAmount += amount

            id = item["inventoryId"]
            try:
                inventory = Inventory.objects.get(id=id)

                orderItem = {
                    "item": item,
                    "inventory": inventory,
                    "quantity": item["quantity"]
                }
                orderItems.append(orderItem)

            except Inventory.DoesNotExist as e:
                return respond_error("SKU with Id: {} does not exist".format(id), status=404)

        order = Orders(
            vendorCreated=data["vendorCreated"],
            userId=userId,
            orderProgressStatus="CREATED",
            source="ORDER_FORM",
            externalDump=data,
            vendorId=vendor,
            externalOrderId=data["external"]["order_id_reference"],
            originalDate=data["external"]["order_date"],
            items=data["items"],
            customer=data["customer"],
            billingCurrency=data["billingCurrency"],
            billingAmount=billAmount,
        )
        order.save()

        warehouses = set()

        flag = False
        for it in orderItems:
            item = it["item"]
            inv = it["inventory"]

            orderItem = OrderItems(
                orderId=order,
                itemStatus={
                    "created": {
                        "flag": True,
                        "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"),
                        "userId": userId
                    }
                },
                recentStatus="created",
                itemPayload=item,
                warehouseId=inv.warehouseId
            )
            warehouses.add(inv.warehouseId)

            orderItem.save()

            quantity = it["quantity"]
            inv.currentQuantity -= quantity
            inv.save()
            respStatusCode = externalUpdate.updateExternalIntegrations(inv, -quantity)
            item["externalUpdateFlag"] = respStatusCode
            if respStatusCode != 200:
                flag = True

        if flag:  # This is a log storage for all missed external integrations due to API failure or other errors
            order.items = items
            order.save()

        # VENDOR NOTIFICATION
        notification.addNotification(
            {
                "category": {"type": "ORDER", "endpoint": ""},
                "payload": {
                    "title": "New Order: #{}".format(order.id),
                    "description": "New order found.",
                    "otherDetails": "",
                    "userId": userId
                },
                "emailContent": {
                    "subject": "New Order: #{}".format(order.id),
                    "body": "New order found to fullfill from your warehouse"},
                "vendorId": vendor,
                "warehouseId": None
            },
            False
        )
        # WAREHOUSE NOTIFICATION
        for item in warehouses:
            notification.addNotification(
                {
                    "category": {"type": "ORDER", "endpoint": ""},
                    "payload": {
                        "title": "New Order: #{}".format(order.id),
                        "description": "New order found to fullfill from your warehouse",
                        "otherDetails": "",
                        "userId": userId
                    },
                    "emailContent": {
                        "subject": "New Order: #{}".format(order.id),
                        "body": "New order found to fullfill from your warehouse"},
                    "vendorId": None,
                    "warehouseId": item
                },
                False
            )

        return respond_success("Order saved: #{}".format(order.id))

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getOrderItems(request):
    try:

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        request_data = request.GET
        page_seq = int(request_data.get("page_seq", default=0))
        page_size = int(
            request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))
        order_id = int(request_data.get("order_id", default=0))

        filters = {}
        if vendorId != "VENDOR_ALL":
            filters["vendorId"] = vendor

        if order_id != 0:
            filters["id"] = order_id

        items = Orders.objects.filter(**filters)
        count = items.count()

        startIndex = (max(0, page_seq - 1)) * page_size
        endIndex = min(startIndex + page_size, count)
        if startIndex > count:
            return respond_error({"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

        allObjects = items[startIndex:endIndex]
        retObjects = [x.asJson() for x in allObjects]
        print(retObjects)

        for order in retObjects:
            orderItems = OrderItems.objects.filter(orderId=order["id"])
            orderItems = [x.asJson() for x in orderItems]
            order["orderItems"] = orderItems

        def sortFuncOnId(x):
            return x["id"]

        retObjects.sort(key=sortFuncOnId, reverse=True)

        return respond_success({
            "totalCount": count,
            "pageNum": page_seq,
            "payloads": retObjects
        })
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def processOrdersShopify(request, vendorId):
    data = json.loads(request.body)
    vendor = None
    try:
        vendor = Vendor.objects.get(vendorId=vendorId)
    except Vendor.DoesNotExist as e:
        vendor = None

    if vendor is None:
        # Save it in a different table and return
        pass

    items = []
    billAmount = 0
    inventories = []
    orderItems = []
    for item in data["line_items"]:

        inventory = None
        itemInventories = []
        try:
            # TODO: Sort on the basis of arrival
            # TODO: filter out inventories that have 0 quantity
            allInventories = Inventory.objects.filter(skuNumber=item["sku"], variantId=item["variant_id"],
                                                      vendorId=vendor)
            traversedQuantity = 0
            batchCount = 0
            neededQuantity = item["quantity"]
            for x in allInventories:
                currentNeed = neededQuantity - traversedQuantity
                if currentNeed == 0:
                    break
                curQuantity = x.currentQuantity
                if curQuantity == 0:
                    continue
                if curQuantity >= currentNeed:
                    inv = {
                        "inventory": x,
                        "quantity": currentNeed
                    }
                    itemInventories.append(inv)
                    inventories.append(inv)
                    batchCount += 1
                    traversedQuantity += currentNeed
                    break
                elif curQuantity < currentNeed:
                    traversedQuantity += curQuantity
                    batchCount += 1
                    inv = {"inventory": x, "quantity": curQuantity}
                    itemInventories.append(inv)
                    inventories.append(inv)
        except Inventory.DoesNotExist as e:
            # TODO
            print("SKU: {}, Variant: {}, Vendor: {} does not exist".format(item["sku"], item["variant_id"],
                                                                           vendor.vendorId))
            return respond_error("SKU: {}, Variant: {}, Vendor: {} does not exist", status=404)

        for x in itemInventories:
            localItem = {
                "title": item["title"],
                "name": item["name"],
                "variantTitle": item["variant_title"],
                "quantity": x['quantity'],
                "inventoryId": x["inventory"].id,
                "sku": item["sku"],
                "price": item["price"],
                "variantId": item["variant_id"],
                "currentQuantity": x["inventory"].currentQuantity,
                "requiresShipping": item["requires_shipping"]
            }
            items.append(localItem)

            orderItem = {
                "item": localItem,
                "inventory": x["inventory"],
                "quantity": localItem["quantity"]
            }
            orderItems.append(orderItem)

        price = float(item["price"])
        quantity = item["quantity"]
        itemAmount = price * quantity
        billAmount = billAmount + itemAmount

    name = data["customer"]["first_name"]
    if name is None:
        name = ""
    name += data["customer"]["last_name"]
    if name is None:
        name = ""
    customer = {
        "name": name,
        "contact": {
            "email": data["customer"]["email"],
            "phone": data["customer"]["phone"]
        },
        "billing_address": data["billing_address"],
        "shipping_address": data["shipping_address"],
        "same_shipping_billing_address": False
    }

    order = Orders(
        vendorCreated=False,
        userId={},
        orderProgressStatus="CREATED",
        source="SHOPIFY",
        externalDump=data,
        vendorId=vendor,
        externalOrderId=str(data["order_number"]),
        originalDate=data["created_at"],
        items=items,
        customer=customer,
        billingCurrency=data["currency"],
        billingAmount=billAmount,
        warehouseId=None
    )

    # breakpoint()

    order.save()

    flag = False

    warehouses = set()

    for it in orderItems:
        item = it["item"]
        inv = it["inventory"]

        # breakpoint()
        orderItem = OrderItems(
            orderId=order,
            itemStatus={
                "created": {
                    "flag": True,
                    "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M")
                }
            },
            recentStatus="created",
            itemPayload=item,
            warehouseId=inv.warehouseId
        )
        warehouses.add(inv.warehouseId)

        orderItem.save()

        quantity = it["quantity"]
        inv.currentQuantity -= quantity
        inv.save()
        respStatusCode = externalUpdate.updateExternalIntegrations(inv, -quantity)
        item["externalUpdateFlag"] = respStatusCode
        if respStatusCode != 200:
            flag = True

    if flag:  # This is a log storage for all missed external integrations due to API failure or other errors
        print("Was not able to update external integration.")
        order.items = items
        order.save()
    else:
        # VENDOR NOTIFICATION
        notification.addNotification(
            {
                "category": {"type": "ORDER", "endpoint": ""},
                "payload": {
                    "title": "New Order: #{}".format(order.id),
                    "description": "New order found.",
                    "otherDetails": "",
                    "userId": "",
                    "source": "SHOPIFY"
                },
                "emailContent": {
                    "subject": "New Order: #{}".format(order.id),
                    "body": "New order found to fullfill from your warehouse"},
                "vendorId": vendor,
                "warehouseId": None
            },
            False
        )
        # WAREHOUSE NOTIFICATION
        notification.addNotification(
            {
                "category": {"type": "ORDER", "endpoint": ""},
                "payload": {
                    "title": "New Order: #{}".format(order.id),
                    "description": "New order found to fullfill from your warehouse",
                    "otherDetails": "",
                    "userId": "",
                    "source": "SHOPIFY"
                },
                "emailContent": {
                    "subject": "New Order: #{}".format(order.id),
                    "body": "New order found to fullfill from your warehouse"},
                "vendorId": None,
                "warehouseId": None
            },
            False
        )

    return respond_success("Ok")


def processOrdersGeneric(request):
    pass


def getVendorSkuFromInventory(request):
    try:
        vendorId = request.GET.get("vendorId")
        query = request.GET.get("query")
        inventoryId = request.GET.get("inventoryId", "")

        vendor = None

        try:
            vendor = Vendor.objects.get(id=vendorId)
        except Vendor.DoesNotExist as e:
            vendor = None

        if vendor is None:
            return respond_error(f"Error: VendorId is incorrect")

        if inventoryId.strip() != "":
            inventory = Inventory.objects.get(id=inventoryId)
            return respond_success([inventory.asJson()])

        objs = []
        inventories = Inventory.objects.filter(
            (Q(skuNumber__startswith=query) |
             Q(payload__packageName__icontains=query) |
             Q(skuReference__productName__icontains=query)) &
            Q(vendorId=vendor)
        )
        for inventory in inventories:
            objs.append(inventory.asJson())

        return respond_success(objs)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getOrderItemsByOrderId(request):
    try:
        userId = request.META.get("auth").get("token").userId
        if userId.warehouseId is None or userId.role.lower() == "admin":
            return respond_error("Only Warehouse Managers are allowed to stock In. You chill.", status=401)

        orderId = request.GET.get("orderId", "")
        orderStatus = request.GET.get("orderStatus", "")
        includeShippingDetails = request.GET.get("includeShippingDetails", default="false").lower()
        if includeShippingDetails == "true":
            includeShippingDetails = True
        else:
            includeShippingDetails = False

        if orderId == "":
            return respond_error("OrderId is missing", status=404)

        filters = {}
        filters["warehouseId"] = userId.warehouseId

        if orderStatus != "":
            filters = {"recentStatus": orderStatus}
        if orderId != "ALL":
            filters["orderId"] = orderId

        orderItems = None
        objs = []
        orderItems = OrderItems.objects.filter(**filters).order_by('orderId')

        shippingDetails = {}
        if orderItems is not None:
            for item in orderItems:
                inventoryId = item.itemPayload["inventoryId"]
                inventory = Inventory.objects.get(id=inventoryId)

                itemJson = item.asJson()
                itemJson["inventory"] = inventory.asJson()

                if includeShippingDetails:
                    orderId = item.orderId
                    shippingKey = "{}-{}".format(orderId.id, item.id)
                    if shippingKey in shippingDetails:
                        itemJson["shippingDetails"] = shippingDetails[shippingKey]
                    else:
                        try:
                            shipping = ShippingDetails.objects.filter(
                                Q(orderId=orderId) &
                                Q(orderItems__contains=item.id)
                            )
                            shipping = [x.asJson() for x in shipping]
                            if len(shipping) > 0:
                                obj = {"shipped": True, "details": shipping}
                            else:
                                obj = {"shipped": False}
                            shippingDetails[shippingKey] = obj
                            itemJson["shippingDetails"] = shippingDetails[shippingKey]
                        except ShippingDetails.DoesNotExist as e:
                            shippingDetails[orderId.id] = {"shipped": False}

                objs.append(itemJson)

        return respond_success(objs)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")

    return respond_success({})


def updateOrderItemByRowId(request):
    try:
        user = request.META.get("auth").get("token").userId
        userId = request.META.get("auth").get("tokenObject")
        if user.warehouseId is None or user.role.lower() == "admin":
            return respond_error("Only Warehouse Managers are allowed to stock In. You chill.", status=401)
        data = json.loads(request.body)

        orderItem = None
        try:
            orderItem = OrderItems.objects.get(id=data["rowId"], warehouseId=user.warehouseId)
            if orderItem.recentStatus == "cancelled" or orderItem.recentStatus == "returned":
                print("This item has either been cancelled or returned")
                return respond_error("This item has either been cancelled or returned")

            payload = {
                data["newStatus"]: {
                    "flag": True,
                    "timestamp": datetime.now().strftime("%d-%m-%Y %H:%M"),
                    "userId": userId,
                    "payload": data["payload"]
                }
            }
            orderItem.itemStatus.update(payload)
            orderItem.recentStatus = data["newStatus"]
            orderItem.save()

            return respond_success(orderItem.asJson())

        except OrderItems.DoesNotExist as e:
            return respond_error("Row Id does not exist", status=404)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")

    return respond_success({})


def readNotification(request):
    try:
        id = int(request.GET.get("id", ""))
        notification.toggleNotification(id)
        return respond_success("Done")
    except Exception as e:
        return respond_error(f"Error: {e.args}")


def getAllNotifications(request):
    try:
        user = request.META.get("auth").get("token").userId

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        warehouseId = request.META.get("auth").get("tokenObject").get("warehouseId")

        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        warehouse = None
        if warehouseId != "WAREHOUSE_ALL" and warehouseId != None:
            warehouse = WarehouseMaster.objects.get(id=warehouseId)

        userType = request.META.get("auth").get("authType")

        filters = {}

        if userType == "warehouseUser":
            ns = notification.getAllNotifications(
                Q(vendorId=None) & (Q(warehouseId=warehouse) | Q(warehouseId=None))
            )

        else:
            ns = notification.getAllNotifications(
                Q(vendorId=vendor)
            )

        objs = []
        for n in ns:
            objs.append(n.asJson())

        return respond_success(objs)

    except Exception as e:
        return respond_error(f"Error: {e.args}")
