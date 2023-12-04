# Author: CP

import json, requests, traceback

from wms_backend.utils.http_responses import respond_success, respond_error

from infra.models import WarehouseMaster, WarehouseZones, WarehouseLocations, WarehouseShelves, WarehouseBinsAndTrolley
from infra.models import WarehouseUsers, ShelvingLogs, Vendor, VendorExternalIntegration, Inventory
from inbound.models import GRN, ASN, SKU
from utils import shopify as externalUpdate

from datetime import datetime

from django.conf import settings

import shopify


def getInventoryItems(request):
    try:

        request_data = request.GET
        page_seq = int(request_data.get("page_seq", default=0))
        page_size = int(
            request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        vendorId = request_data.get("vendorId", default=None)
        skuNumber = request_data.get("skuNumber", default=None)
        if vendorId is None and skuNumber is None:
            return respond_error("both VendorId and skuNumber are missing", status=404)

        vendor = None
        if vendorId is not None:
            try:
                vendor = Vendor.objects.get(vendorId=vendorId);
            except Vendor.DoesNotExist as e:
                return respond_error("Vendor does not exist", status=404)

        filters = {}
        if vendorId is not None:
            filters["vendorId"] = vendor
        if skuNumber is not None:
            filters["skuNumber"] = skuNumber
        items = Inventory.objects.filter(**filters)
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
        return respond_error(e.args, status=404)


def addShopifyForVendors(request):
    try:
        request_data = json.loads(request.body)

        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.role.lower() != "admin":
            return respond_error("Forbidden", status=403)

        vendorId = request_data["vendorId"]
        shopUrl = request_data["shopUrl"]
        accessToken = request_data["accessToken"]
        apiKey = request_data["apiKey"]
        apiSecret = request_data["apiSecret"]

        vendor = None
        try:
            vendor = Vendor.objects.get(vendorId=vendorId)
        except Vendor.DoesNotExist as e:
            return respond_error("VendorId is invalid", status=404)

        webhookUrl = "{}{}{}/".format(
            settings.TENANT_SETTINGS["orders"]["SHOPIFY"]["CALLBACK_RECEIVE_ORDERS_BASE"],
            settings.TENANT_SETTINGS["orders"]["SHOPIFY"]["CALLBACK_RECEIVE_ORDERS_PATH"],
            vendorId
        )

        obj = {
            "type": "ecommerce",
            "name": "shopify",
            "shopUrl": shopUrl,
            "accessToken": accessToken,
            "apiKey": apiKey,
            "apiSecret": apiSecret,
            "webhook": {
                "orders/create": {
                    "request": {
                        "webhook": {
                            "address": webhookUrl,
                            "topic": "orders/create",
                            "format": "json"
                        }
                    }
                },
                #                "orders/cancelled": {
                #                    "request": {
                #                        "webhook": {
                #                            "address": webhookUrl,
                #                            "topic": "orders/cancelled",
                #                            "format": "json"
                #                        }
                #                    }
                #                }
            },
            "success": False
        }

        externalIntegration = None
        try:
            externalIntegration = VendorExternalIntegration.objects.get(vendorId=vendor)
        except VendorExternalIntegration.DoesNotExist as e:
            externalIntegration = VendorExternalIntegration()

        externalIntegration.vendorId = vendor
        externalIntegration.shopify = obj
        externalIntegration.save()

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": accessToken
        }

        stutuses = set()
        for key in obj["webhook"].keys():
            payload = obj["webhook"][key]["request"]
            res = requests.request(
                "POST",
                "{}/admin/api/2022-10/webhooks.json".format(shopUrl),
                headers=headers,
                data=json.dumps(payload)
            )

            stutuses.add(res.status_code)
            obj["webhook"][key]["status"] = res.status_code
            obj["webhook"][key]["response"] = res.json()
            externalIntegration.shopify = obj
            externalIntegration.save()

        if len(list(stutuses)) == 1:
            obj["success"] = True
            externalIntegration.shopify = obj
            externalIntegration.save()
            return respond_success("Integration Successfully")
        else:
            return respond_error("Some error happened: {}".format(res.text), status=404)
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def getShelvingLog(request):
    try:
        request_data = json.loads(request.body)

        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)
        warehouseId = user.warehouseId
        if warehouseId is None or user.role.lower() == "admin":
            return respond_error("User not allowed", status=404)

        filters = {}
        filters["warehouseId"] = warehouseId

        steps = None
        if "steps" in request_data:
            steps = request_data["steps"]
            if type(steps) is not list:
                steps = None

        if "id" in request_data:
            id = request_data["id"]
            filters["id"] = id

        logs = None

        try:
            logs = ShelvingLogs.objects.filter(**filters)
            if steps is not None:
                logs = logs.filter(step__in=steps)

            obj = []
            for log in logs:
                obj.append(log.asJson())

            return respond_success(obj)

        except ShelvingLogs.DoesNotExist as e:
            print(traceback.format_exc())
            return respond_error(e.args, status=404)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def addInventoryFromLog(log, locationType):
    # ADD to SQS, below code to lambda
    inventory = None
    try:
        inventory = Inventory.objects.get(vendorId=log.vendorId, skuNumber=log.skuNumber, batchNumber=log.batchNumber)
    except Inventory.DoesNotExist as e:
        pass

    if inventory is None:
        inventory = Inventory()

    inventory.warehouseId = log.warehouseId
    inventory.live = True
    inventory.vendorId = log.vendorId
    inventory.skuNumber = log.skuNumber
    inventory.variantId = log.variantId
    inventory.skuReference = log.skuReference
    inventory.batchNumber = log.batchNumber
    if inventory.currentQuantity is None:
        inventory.currentQuantity = log.currentQuantity
    else:
        inventory.currentQuantity = inventory.currentQuantity + log.currentQuantity

    inventory.payload = log.payload
    inventory.locationType = locationType
    if inventory.stepLive is None:
        inventory.stepLive = datetime.now()

    inventory.allocatedShelfId = log.confirmedShelfId
    inventory.allocatedBinId = log.confirmedBinId

    inventory.save()

    externalUpdate.updateExternalIntegrations(inventory, log.currentQuantity)


def addShelvingLog(request):
    try:
        request_data = json.loads(request.body)

        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)
        if user.warehouseId is None or user.role.lower() == "admin":
            return respond_error("User not allowed", status=404)

        step = request_data["step"]
        if step not in ["Created", "StockIn", "Transport", "Shelving"]:
            return respond_error("Not an allowed step.", status=404)

        vendorId = request_data["vendorId"]
        try:
            vendor = Vendor.objects.get(vendorId=vendorId)
        except Vendor.DoesNotExist as e:
            return respond_error(e.args, status=404)

        grnId = request_data["grnId"]
        try:
            grn = GRN.objects.get(grnId=grnId)
        except GRN.DoesNotExist as e:
            return respond_error(e.args, status=404)

        asnId = request_data["asnId"]
        try:
            asn = ASN.objects.get(asnId=asnId)
        except ASN.DoesNotExist as e:
            return respond_error(e.args, status=404)

        items = request_data["items"]

        for item in items:

            skuDetails = {}
            try:
                skuItem = SKU.objects.get(skuNumber=item["skuNumber"], variantId=item["variantId"])
                skuDetails['error'] = False
                skuDetails['sku'] = skuItem
                item["skuDetails"] = skuDetails
            except SKU.DoesNotExist as e:
                skuDetails['error'] = True
                return respond_error(
                    "SKU Id: {}, VariantId: {} does not exist.".format(item["skuNumber"], item["variantId"]),
                    status=404)

            item['log'] = None

            if step in ["StockIn", "Transport", "Shelving"]:
                logId = item["logId"]
                try:
                    log = ShelvingLogs.objects.get(id=logId)
                    item['log'] = log
                    if log.step == step or log.step == "Shelving":
                        return respond_error("Duplicate entry for adding shelving log. Returning", status=404)
                except ShelvingLogs.DoesNotExist as e:
                    print("Log Id does not exist")
                    return respond_error("Log Id does not exist", status=404)

            if step == "Created":
                item["aShelf"] = None
                item["aBin"] = None

            elif step == "StockIn":

                item["aShelf"] = None
                item["aBin"] = None

                allocatedShelfId = item["allocatedShelfId"]
                if allocatedShelfId is not None:
                    try:
                        shelf = WarehouseShelves.objects.get(qualifiedName=allocatedShelfId)
                        item["aShelf"] = shelf
                    except WarehouseShelves.DoesNotExist as e:
                        print("Shelf does not exist", type(allocatedShelfId), allocatedShelfId)
                        return respond_error("Warehouse Shelf {} does not exist".format(allocatedShelfId), status=404)

                allocatedBinId = item["allocatedBinId"]
                if allocatedBinId is not None:
                    try:
                        bin = WarehouseBinsAndTrolley.objects.get(binId=allocatedBinId)
                        item["aBin"] = bin
                    except WarehouseBinsAndTrolley.DoesNotExist as e:
                        print("Shelf does not exist")
                        return respond_error("Warehouse Bin with ID: {} does not exist".format(allocatedBinId),
                                             status=404)

            elif step == "Transport":
                item["tTrolley"] = None
                item["tBin"] = None

                transportTrolleyId = item["transportTrolleyId"]
                if transportTrolleyId is not None:
                    try:
                        trolley = WarehouseBinsAndTrolley.objects.get(qualifiedName=transportTrolleyId)
                        item["tTrolley"] = trolley
                    except WarehouseBinsAndTrolley.DoesNotExist as e:
                        print("Shelf does not exist")
                        return respond_error("Trolley with ID: {} does not exist".format(transportTrolleyId),
                                             status=404)

                transportBinId = item["transportBinId"]
                if transportBinId is not None:
                    try:
                        bin = WarehouseBinsAndTrolley.objects.get(qualifiedName=transportBinId)
                        item["tBin"] = bin
                    except WarehouseBinsAndTrolley.DoesNotExist as e:
                        print("Shelf does not exist")
                        return respond_error("Bin Id with {} does not exist.".format(transportBinId), status=404)

            elif step == "Shelving":
                item["sShelf"] = None
                item["sBin"] = None

                confirmedShelfId = item["confirmedShelfId"]
                if confirmedShelfId is not None:
                    try:
                        shelf = WarehouseShelves.objects.get(qualifiedName=confirmedShelfId)
                        item["sShelf"] = shelf
                    except WarehouseBinsAndTrolley.DoesNotExist as e:
                        print("Shelf does not exist")
                        return respond_error("Shelf ID: {} does not exist.".format(confirmedShelfId), status=404)

                confirmedBinId = item["confirmedBinId"]
                if confirmedBinId is not None:
                    try:
                        bin = WarehouseBinsAndTrolley.objects.get(qualifiedName=confirmedBinId)
                        item["sBin"] = bin
                    except WarehouseBinsAndTrolley.DoesNotExist as e:
                        print("Shelf does not exist")
                        return respond_error("Bin Id: {} does not exist".format(confirmedBinId), status=404)

        asn.stageStockIn = step
        asn.save()

        grn.stageStockIn = step
        grn.save()

        for item in items:

            log = item['log']
            boxSeq = item['boxSeq'] if 'boxSeq' in item else None
            if log is None:
                log = ShelvingLogs()
            log.warehouseId = user.warehouseId
            log.step = step
            log.vendorId = vendor
            log.grn = grnId
            log.asn = asnId
            log.skuNumber = item["skuNumber"]
            log.variantId = item["variantId"]
            log.skuReference = item['skuDetails']['sku']
            log.currentQuantity = item["currentQuantity"]
            log.batchNumber = item["batchNumber"]
            if step != "Created":
                log.locationType = item["locationType"]
            log.payload = item["payload"]

            if boxSeq is not None:
                log.boxSeq = boxSeq

            if step == "StockIn":
                log.stepStockIn_ts = datetime.now()
                log.allocatedShelfId = item["aShelf"]
                log.allocatedBinId = item["aBin"]

            elif step == "Transport":
                log.stepTransport_ts = datetime.now()
                log.transportTrolleyId = item["tTrolley"]
                log.transportBinId = item["tBin"]

            elif step == "Shelving":
                log.stepShelving = datetime.now()
                log.confirmedShelfId = item["sShelf"]
                log.confirmedBinId = item["sBin"]

            log.save()

            if step == "Shelving":
                addInventoryFromLog(log, item["locationType"])

        return respond_success("Success")

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def getShelvingShelves(request):
    try:
        request_data = json.loads(request.body)

        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.warehouseId is None or user.role.lower() == "admin":
            return respond_error("Only Warehouse Managers are allowed to stock In. You chill.", status=401)

        storageType = request_data["storageType"]
        grnId = request_data["grnId"]
        skuId = request_data["skuId"]

        grn = GRN.objects.get(grnId=grnId)
        warehouseId = grn.warehouseId.id
        warehouse = grn.warehouseId
        vendorId = grn.vendorId.id

        shelvesList = set()

        # First Level Filter: Same SKU

        sameSkuLocations = []
        inventories = Inventory.objects.filter(
            skuNumber=skuId,
            vendorId=grn.vendorId,
            warehouseId=warehouse,
            locationType=storageType
        )
        for inv in inventories:
            shelf = inv.allocatedShelfId
            if shelf.id in shelvesList:
                continue
            obj = {
                "id": shelf.id,
                "shelfId": shelf.shelfId,
                "qualifiedName": shelf.qualifiedName
            }
            shelvesList.add(shelf.id)
            sameSkuLocations.append(obj)

        # Second Level Filter: Same Vendor

        sameVendorLocations = []
        inventories = Inventory.objects.filter(
            vendorId=grn.vendorId,
            warehouseId=warehouse,
            locationType=storageType
        )
        for inv in inventories:
            shelf = inv.allocatedShelfId
            if shelf.id in shelvesList:
                continue
            obj = {
                "id": shelf.id,
                "shelfId": shelf.shelfId,
                "qualifiedName": shelf.qualifiedName,
                "storedItemName": inv.skuReference.productName
            }
            shelvesList.add(shelf.id)
            sameVendorLocations.append(obj)

        # Third Level Filter: Empty Locations

        emptyLocations = []

        allShelves = WarehouseShelves.objects.filter(
            locationId__type__contains=storageType,
            qualifiedName__startswith="W{}".format(warehouseId)
        )

        for shelf in allShelves:
            if shelf.id in shelvesList:
                continue
            obj = {
                "id": shelf.id,
                "shelfId": shelf.shelfId,
                "qualifiedName": shelf.qualifiedName
            }
            shelvesList.add(shelf.id)
            emptyLocations.append(obj)

        # Fourth Level Filter: Non Full Locations

        partialOccupiedLcoations = []

        response = {
            "sameSkuLocations": sameSkuLocations,
            "sameVendorLocations": sameVendorLocations,
            "emptyLocations": emptyLocations,
            "partialOccupiedLcoations": partialOccupiedLcoations
        }

        return respond_success(response)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def addWarehouseBinsAndTrolley(request):
    try:
        request_data = json.loads(request.body)
        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.role.lower() != "admin":
            return respond_error("Forbidden resource", status=403)

        warehouseId = request_data["warehouseId"]
        master = None
        try:
            master = WarehouseMaster.objects.get(id=warehouseId)
        except WarehouseMaster.DoesNotExist as e:
            print("Warehouse does not exist")
            return respond_error(f"warehouse Id: {warehouseId} does not eist", status=404)

        numberOfBins = int(request_data["number"])
        type = request_data["type"]

        print("Type: ", type)
        if type != "Bin" and type != "Trolley":
            return respond_error(f"Unsupported Type: {type}", status=404)

        createdCount = 0
        for i in range(numberOfBins):
            bin = WarehouseBinsAndTrolley(
                warehouseId=master,
                type=type,
                vendorIds=[],
                skuIds=[],
                userId=user
            )
            bin.save()
            createdCount += 1

        retObjects = {}
        retObjects[f"{type}sCounts"] = createdCount

        return respond_success(retObjects)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def addWarehouseLocationsAndShelves(request):
    try:

        request_data = json.loads(request.body)
        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.role.lower() != "admin":
            return respond_error("Forbidden resource", status=403)

        zoneId = request_data["zoneId"]
        zone = None
        try:
            zone = WarehouseZones.objects.get(id=zoneId)
        except WarehouseZones.DoesNotExist as e:
            print("Warehouse does not exist")
            return respond_error(f"warehouse zone: {zoneId} does not eist", status=404)

        type = request_data["type"]
        description = request_data["description"]
        name = request_data["name"]
        group = request_data["group"]

        counts = request_data["counts"]

        countAisle = int(counts["aisle"])
        countRack = int(counts["rack"])
        countShelf = int(counts["shelf"])

        assert countAisle > 0
        assert countRack > 0
        assert countShelf > 0

        location = WarehouseLocations(
            zoneId=zone,
            type=type,
            description=description,
            group=group,
            name=name,
            counts=counts,
            userId=user
        )

        retObjects = {}

        save = location.save()
        retObjects["location"] = location.qualifiedName

        totalShelvesToCreate = countAisle * countRack * countShelf

        createdshelfCount = 0
        for i in range(countAisle):
            for j in range(countRack):
                for k in range(countShelf):
                    shelf = WarehouseShelves(
                        locationId=location,
                        internalAisleId=i + 1,
                        internalRackId=j + 1,
                        internalShelfId=k + 1,
                        vendorIds=[],
                        skuIds=[],
                        binIds=[],
                        userId=user
                    )

                    shelf.save()
                    createdshelfCount += 1

        retObjects["shelvesCounts"] = createdshelfCount

        return respond_success(retObjects)


    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def addWarehouseZones(request):
    try:
        request_data = json.loads(request.body)

        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.role.lower() != "admin":
            return respond_error("Forbidden resource", status=403)

        warehouseId = request_data["warehouseId"]
        master = None
        try:
            master = WarehouseMaster.objects.get(id=warehouseId)
        except WarehouseMaster.DoesNotExist as e:
            print("Warehouse does not exist")
            return respond_error(f"warehouse Id: {warehouseId} does not eist", status=404)

        name = request_data["name"]
        description = request_data["description"]
        floor = request_data["floor"]
        mezzanine = bool(request_data["mezzanine"])

        zone = WarehouseZones(
            warehouseId=master,
            zoneName=name,
            description=description,
            floor=floor,
            mezzanine=mezzanine,
            userId=user
        )

        save = zone.save()
        return respond_success(f"Zone Created: #{zone.qualifiedName}")

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def addWarehouse(request):
    try:
        request_data = json.loads(request.body)
        print(request.META)
        userId = request.META.get("auth").get("token").userId
        user = WarehouseUsers.objects.get(email=userId.email)

        if user.role.lower() != "admin":
            return respond_error("Forbidden resource", status=403)

        whName = request_data["name"]

        whAddress = request_data["address"]
        whContact = request_data["contact"]

        whObject = WarehouseMaster(
            name=whName,
            address=whAddress,
            contactDetails=whContact,
            managers=[],
            userId=userId
        )

        save = whObject.save()
        return respond_success(f"Warehouse Created: #{whObject.qualifiedName}")

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)


def getAllWarehouseObjects(request):
    typeMapping = {
        "Master": WarehouseMaster,
        "Zones": WarehouseZones,
        "Locations": WarehouseLocations,
        "Shelves": WarehouseShelves,
        "Bin": WarehouseBinsAndTrolley,
        "Trolley": WarehouseBinsAndTrolley
    }

    typeFilter = {
        "Bin": "Bin",
        "Trolley": "Trolley"
    }

    type = request.GET.get("type")
    if type not in typeMapping.keys():
        return respond_error("Invalid request / type", status=404)

    filters = None
    if type in typeFilter:
        filters = {}
        filters["type"] = typeFilter[type]

    try:
        if filters is not None:
            objs = typeMapping[type].objects.filter(**filters)
        else:
            objs = typeMapping[type].objects.all()

        returnObjects = [
            x.asJson() for x in objs
        ]

        return respond_success(returnObjects)

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(e.args, status=404)
