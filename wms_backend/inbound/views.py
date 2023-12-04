import json
import traceback
import os
import csv
import time

from jsonschema import validate as schemaValidator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.conf import settings
from django.db.models import Sum
from wms_backend.utils.http_responses import respond_success, respond_error
from datetime import datetime, timedelta
import datetime as dt

from django.db import connection


from schema.inbound import schemagrn

# Import models
from inbound.models import ASN
from inbound.models import GRN
from inbound.models import SKU
from inbound.models import Retailers

from infra.models import Vendor
from infra.models import VendorUsers
from infra.models import WarehouseMaster
from infra.models import WarehouseUsers
from infra.models import VendorExternalIntegration
from infra.models import Orders

from inbound import requestschema
import requests
# why main project name is not specified in the above import:
# https://stackoverflow.com/questions/26591399/django-1-7-conflicting-models


@csrf_exempt
@require_http_methods(["GET"])
def buildSKUsFromShopify(request):

    try:

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        try:
            vendorExternalValidation = VendorExternalIntegration.objects.get(vendorId=vendor)
            if vendorExternalValidation.shopify["success"] == False :
                return respond_error("The external Shopify integration is yet not finished. Please contact the system adminitrator.")

        except VendorExternalIntegration.DoesNotExist as e:
            return respond_error("The external Shopify integration is yet not started. Please contact the system adminitrator.")

        shopify = vendorExternalValidation.shopify

        location = None
        # Step 1: Get All Locations
        url = "{}/admin/api/2022-10/locations.json".format(shopify["shopUrl"])
        headers = {"X-Shopify-Access-Token": shopify["accessToken"]}
        response = requests.request("GET", url, headers=headers)
        locResp = response.json()
        # For now we will consider only single location mapping
        if "locations" in locResp and len(locResp["locations"]) > 0:
            location = locResp["locations"][0]

        inventoryLevels = {}
        # Step 2: Get All InventoryLevel
        if location is None:
            return respond_error("Please configure locations in Shopify and get back to us on linking them.")

        url = "{}/admin/api/2022-10/inventory_levels.json?location_ids={}".format(shopify["shopUrl"], location["id"])
        response = requests.request("GET", url, headers=headers)
        if "inventory_levels" not in response.json() and len(response.json()["inventory_levels"]) > 0:
            return respond_error("Please configure inventory Levels at Shopify and get back to us on linking them.")
        inventoryLevelItems = response.json()["inventory_levels"]
        for inventory in inventoryLevelItems:
            id = inventory["inventory_item_id"]
            inventoryLevels[id] = inventory

        products = []
        # Step 3: Get All Products
        url = "{}/admin/api/2022-10/products.json".format(shopify["shopUrl"])
        response = requests.request("GET", url, headers=headers)
        if "products" not in response.json() and len(response.json()["products"]) > 0:
            return respond_error("Please configure products at shopify and get back to us on linking them.")
        products = response.json()["products"]

        # Step 4: Link Products to Inventory Levels and Variants and save it in Local Inventory Table
        skuItems = []
        for product in products:
            for variant in product["variants"]:
                skuNumber = variant["sku"]
                if skuNumber.strip() == "":
                    print ("A Variant found with no SKU Number. Skipping it. ", variant, '\n', product)
                    continue
                colour = ""
                composition = ""
                description = product["body_html"]
                productId = product["id"]
                productName = product["title"]
                variantId = variant["id"]
                variantName = variant["title"]
                shopify = {
                    "locationId": location["id"],
                    "inteventoryLevel": variant["inventory_item_id"],
                    "productDump": product,
                    "variantDump": variant
                }
                shopify["productDump"]["variants"] = None

                images = []
                for image in product["images"]:
                    images.append(image['src'])

                try:
                    item = SKU.objects.get(
                        skuNumber=skuNumber,
                        vendorId=vendor,
                        productId=productId,
                        variantId=variantId
                    )
                    # Item exist.
                    item.shopify=shopify
                    item.save()
                    continue

                except SKU.DoesNotExist as e:
                    pass

                skuObject = SKU(
                    productId=productId,
                    productName=productName,
                    variantId=variantId,
                    variantName=variantName,
                    skuNumber=skuNumber,
                    description=description,
                    vendorId=vendor,
                    payload={"images":images},
                    shopify=shopify,
                    source="SHOPIFY"
                )
                skuObject.save()

        return respond_success(skuItems)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

@csrf_exempt
@require_http_methods(["POST"])
def uploadSkus(request):

    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        fileName = request.FILES.get("uploadFile")
        if fileName is None:
            return respond_error("Not a proper file", status=400)

        outFileName = "/tmp/{}-{}-{}".format(vendorId, int(time.time()), fileName)
        with open(outFileName, "wb") as outFile:
            if fileName.multiple_chunks:
                for c in fileName.chunks():
                    outFile.write(c)
            else:
                outFile.write(fileName.read())


        error = False

        allowedKeys = settings.TENANT_SETTINGS["appSettings"]["SKU"]["ALLOWED_KEYS"]

        with open(outFileName, mode='r', encoding='utf-8-sig') as inFile:

            #objects = SKU.objects.filter(vendorId=vendor)
            #for obj in objects:
            #    obj.delete()

            reader = csv.DictReader(inFile)
            for r in reader:
                sku     = r.get("sku")
                payload = { k: r.get(k) for k in allowedKeys }

                try:
                    with transaction.atomic():
                        skuObject = SKU(
                            productId=r.get("productId"),
                            productName=r.get("productName"),
                            productCategory=r.get("productCategory"),
                            variantId=r.get("variantId"),
                            variantName=r.get("variantName"),
                            skuNumber=r.get("skuNumber"),
                            description=r.get("description"),
                            packaging=r.get("packaging"),
                            composition=r.get("composition"),
                            colour=r.get("colour"),

                            vendorId=vendor,
                            payload=payload,
                            source="MANUAL"
                        )
                        skuObject.save()
                except Exception as e:
                    print (traceback.format_exc())

        return respond_success("Okay")
    
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")


@csrf_exempt
@require_http_methods(["GET"])
def getVendorSkuById(request):
    try:

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        skuNumber = request.GET.get("skuNumber")

        try:
            objs = []
            skus = SKU.objects.filter(skuNumber__startswith=skuNumber, vendorId=vendor)
            for sku in skus:
                objs.append(sku.asJson())
            skus = SKU.objects.filter(productName__icontains=skuNumber, vendorId=vendor)
            for sku in skus:
                objs.append(sku.asJson())
            return respond_success(objs)
        except Exception as e:
            print (traceback.format_exc())
            return respond_error(f"Error: {e.args}")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")


@csrf_exempt
@require_http_methods(["POST"])
def vendorRetailerAdd(request):
    try:
        request_data = json.loads(request.body)

        payload = request_data.get("payload")

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        retailer = Retailers(
            payload=payload,
            vendorId=vendor,
            active=True
        )
        update = retailer.save()
        return respond_success(update)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def vendorRetailerToggleActive(request):
    try:
        request_data = json.loads(request.body)

        active = request_data.get("active")
        retailerId = request_data.get("retailerId")

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        retailer = Retailers.objects.get(id=retailerId, vendorId=vendor)
        retailer.active = active

        update = retailer.save()
        return respond_success(update)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["GET"])
def vendorAllRetailers(request):

    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        retailers = Retailers.objects.filter(vendorId=vendor, active=True)
        obj = []

        for retailer in retailers:
            obj.append(retailer.asJson())

        return respond_success(obj)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


@csrf_exempt
@require_http_methods(["GET"])
def getAllVendorSKUs(request):
    try:
        request_data = request.GET
        page_seq  = int(request_data.get("page_seq", default=0))
        page_size = int(request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        try:
            filters = {}
            if vendorId != "VENDOR_ALL":
                filters["vendorId"] = vendor

            items = SKU.objects.filter(**filters)
            count = items.count()

            startIndex = (max(0,page_seq - 1)) * page_size
            endIndex = min(startIndex + page_size, count)
            if startIndex > count:
                return respond_error({"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

            allObjects = items[startIndex:endIndex]
            retObjects = [x.asJson() for x in allObjects]

            return respond_success({
                "totalCount": count,
                "pageNum": page_seq,
                "payloads": retObjects
            })
 
        except Exception as e:
            print (traceback.format_exc())
            return respond_error(f"Error: {e.args}")

       
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")

def getOrderItemStats(vId):
    query = """
    SELECT
    B."vendorId_id" AS vendorId,
    COUNT(DISTINCT B."id") AS total_orders,
    COUNT(A."id") AS total_order_items,
    COUNT(CASE WHEN "recentStatus" = 'created' THEN 1 ELSE NULL END) AS count_created,
    COUNT(CASE WHEN "recentStatus" = 'picked' THEN 1 ELSE NULL END) AS count_picked,
    COUNT(CASE WHEN "recentStatus" = 'sortdrop' THEN 1 ELSE NULL END) AS count_sortdrop,
    COUNT(CASE WHEN "recentStatus" = 'packed' THEN 1 ELSE NULL END) AS count_packed,
    COUNT(CASE WHEN "recentStatus" IN ('created', 'picked', 'sortdrop', 'packed') THEN 1 ELSE NULL END) AS count_processing,
    COUNT(CASE WHEN "recentStatus" = 'shipped' THEN 1 ELSE NULL END) AS count_shipped,
    COUNT(CASE WHEN "recentStatus" = 'delivered' THEN 1 ELSE NULL END) AS count_delivered,
    COUNT(CASE WHEN "recentStatus" = 'cancelled' THEN 1 ELSE NULL END) AS count_cancelled
    FROM public.infra_orderitems AS A
    JOIN public.infra_orders AS B
    ON A."orderId_id" = B.id
    WHERE B."vendorId_id" = {}
    GROUP BY 1
    LIMIT 5;
    """.format(vId)
    cursor = connection.cursor()
    cursor.execute(query)
    columns = cursor.description
    results = [{columns[index][0]:column for index, column in enumerate(value)} for value in cursor.fetchall    ()]
    return results

def getItemsSellTop(vId):
    query = """
    SELECT
    B."vendorId_id" AS vendorId,
    A."itemPayload"->>'sku' AS item_sku,
    A."itemPayload"->>'name' AS item_name,
    A."itemPayload"->>'price' AS item_price,
    A."itemPayload"->>'title' AS item_title,
    A."itemPayload"->>'variantTitle' AS item_variantTitle,
    SUM(CAST(A."itemPayload"->>'quantity' AS INTEGER)) AS total_item_quantity
    FROM public.infra_orderitems AS A
    JOIN public.infra_orders AS B
    ON A."orderId_id" = B.id
    WHERE B."vendorId_id" = {}
    GROUP BY 1,2,3,4,5,6
    ORDER BY total_item_quantity DESC
    LIMIT 5;
    """.format(vId)
    cursor = connection.cursor()
    cursor.execute(query)
    columns = cursor.description
    results = [{columns[index][0]:column for index, column in enumerate(value)} for value in cursor.fetchall()]
    return results

def getItemsStockLow(vId):
    query = """
    SELECT
    A."skuNumber",
    A."variantId",
    A."vendorId_id",
    A."warehouseId_id",
    B."productName",
    B."variantName",
    B."description",
    C."qualifiedName",
    C."name",
    CAST(SUM(A."currentQuantity") AS INT) AS total_quantity
    FROM public.infra_inventory AS A
    JOIN public.inbound_sku AS B
    ON A."skuNumber" = B."skuNumber" AND A."variantId" = B."variantId" AND A."vendorId_id" = B."vendorId_id"

    JOIN public.infra_warehousemaster AS C
    ON A."warehouseId_id" = C.id

    WHERE A."vendorId_id" = {}
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
    HAVING SUM(A."currentQuantity") < 200
    ORDER BY total_quantity ASC
    ;
    """.format(vId)
    cursor = connection.cursor()
    cursor.execute(query)
    columns = cursor.description
    results = [{columns[index][0]:column for index, column in enumerate(value)} for value in cursor.fetchall    ()]
    return results

def getItemsStockLowSoon(vId):
    query = """
    SELECT
    G."skuNumber",
    G."variantId",
    G."vendorId_id",
    I."productName",
    I."variantName",
    I."description",
    J."qualifiedName",
    J."name",
    G."currentQuantity",
    CAST(H.items_order_per_day AS INT),
    CAST(ROUND(G."currentQuantity" / H.items_order_per_day::INT, 0) AS INT) AS stock_available_for_days
    FROM public.infra_inventory AS G
    JOIN (SELECT A."itemPayload" ->> 'sku' AS skuNumber,
    A."itemPayload" ->> 'variantId' AS variantId,
    B."vendorId_id",
    A."warehouseId_id",
    5*CEIL(SUM(CAST(A."itemPayload" ->> 'quantity' AS INTEGER))/30::FLOAT) AS items_order_per_day
    FROM public.infra_orderitems AS A
    JOIN public.infra_orders AS B
    ON A."orderId_id" = B.id
    -- DATE FILTER below to be put later (dut to thin test data)
    -- WHERE CURRENT_TIMESTAMP::DATE - B."createdDate"::DATE BETWEEN 0 AND 60
    GROUP BY 1, 2, 3, 4
    HAVING CEIL(SUM(CAST(A."itemPayload" ->> 'quantity' AS INTEGER))/30::FLOAT) > 0) AS H
    ON G."skuNumber" = H.skuNumber AND G."variantId" = H.variantId AND G."vendorId_id" = H."vendorId_id" AND G."warehouseId_id" = H."warehouseId_id"

    JOIN public.inbound_sku AS I
    ON G."skuNumber" = I."skuNumber" AND G."variantId" = I."variantId" AND G."vendorId_id" = I."vendorId_id"

    JOIN public.infra_warehousemaster AS J
    ON G."warehouseId_id" = J.id

    WHERE G."vendorId_id" = {}
    ORDER BY stock_available_for_days ASC
    LIMIT 10;
    """.format(vId)
    cursor = connection.cursor()
    cursor.execute(query)
    columns = cursor.description
    results = [{columns[index][0]:column for index, column in enumerate(value)} for value in cursor.fetchall    ()]
    return results

@csrf_exempt
@require_http_methods(["GET"])
def get_stats(request):

    vendorId = request.META.get("auth").get("tokenObject").get("vendorId")

    request_data = request.GET
    requestVendorId = request_data.get("vendorId", None)

    vendor = None
    if requestVendorId is not None:
        try:
            vendor = Vendor.objects.get(vendorId=requestVendorId)
        except Vendor.DoesNotExist as e:
            print (traceback.format_exc())
            return respond_error("Vendor Does not exist.")

    elif vendorId != "VENDOR_ALL":
        try:
            vendor = Vendor.objects.get(id=vendorId)
        except Vendor.DoesNotExist as e:
            print (traceback.format_exc())
            return respond_error("Vendor Does not exist.")


    filterVendor = {}
    if vendor is not None:
        filterVendor["vendorId"] = vendor

    filterGrnUpdated = { "grnUpdated": True }
    if vendor is not None:
        filterGrnUpdated["vendorId"] = vendor

    filterGrnConfirmed = { "grnConfirmed": True }
    if vendor is not None:
        filterGrnConfirmed["vendorId"] = vendor

    totalAsn             = ASN.objects.filter(**filterVendor).count()
    totalAsnGrnUpdated   = ASN.objects.filter(**filterGrnUpdated).count()
    totalAsnGrnConfirmed = ASN.objects.filter(**filterGrnConfirmed).count()

    start = datetime.now()
    ordersLabels = []
    ordersDatesFilters = []
    for i in range(0,30):
        day = start-timedelta(days=i)
        ordersDatesFilters.append(day)
        ordersLabels.append(day.strftime("%d-%m-%Y"))

    fullfilledCounts = []
    fullfilledAmounts = []
    cancelledCounts = []
    cancelledAmounts = []
    for day in ordersDatesFilters:
        #dayObj = datetime(day.year, day.month, day.day)
        filterFullfilledCount = {
            "createdDate__range": [
                datetime.combine(day, dt.time.min),
                datetime.combine(day, dt.time.max)
            ],
            "orderProgressStatus": "CREATED" # TODO: Change it to FULLFILLED
        }
        if vendor is not None:
            filterFullfilledCount["vendorId"] = vendor
        num = Orders.objects.filter(**filterFullfilledCount).count()
        fullfilledCounts.append(num)

        value = Orders.objects.filter(**filterFullfilledCount).aggregate(Sum('billingAmount'))["billingAmount__sum"]
        if value is None:
            fullfilledAmounts.append(0)
        else:
            fullfilledAmounts.append(value)

        filterCancelledCount = {
            "createdDate__range": [
                datetime.combine(day, dt.time.min),
                datetime.combine(day, dt.time.max)
            ],
            "orderProgressStatus": "HOLD" # TODO: Change it to CANCELLED
        }
        if vendor is not None:
            filterCancelledCount["vendorId"] = vendor
        num = Orders.objects.filter(**filterCancelledCount).count()
        cancelledCounts.append(num)

        value = Orders.objects.filter(**filterCancelledCount).aggregate(Sum('billingAmount'))["billingAmount__sum"]
        if value is None:
            cancelledAmounts.append(0)
        else:
            cancelledAmounts.append(value)
    inventory = {}
    if vendorId != "VENDOR_ALL":
        inventory = {
            "itemsSellTop": getItemsSellTop(vendorId),
            "itemsStockLow": getItemsStockLow(vendorId),
            "itemsStockLowSoon": getItemsStockLowSoon(vendorId),
            "itemsOrderStat": getOrderItemStats(vendorId),
        }
    retObj = {
        "asn": {
            "totalCount": totalAsn,
            "grnCreated": totalAsnGrnUpdated,
            "grnConfirmed": totalAsnGrnConfirmed
        },
        "orders": {
            "labels": ordersLabels,
            "data": {
                "fullfilledCounts": fullfilledCounts,
                "fullfilledAmounts": fullfilledAmounts,
                "cancelledCounts": cancelledCounts,
                "cancelledAmounts": cancelledAmounts
            }
        },
        "inventory": inventory
    }

    return respond_success(retObj)


# Create your views here.
@csrf_exempt
@require_http_methods(["GET"])
def get_asn(request):

    try:
        # Collate request data
        request_data = request.GET
        asn_id = request_data.get("id")

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)
        
        # Fetch details
        try:
            if vendor:
                asn = ASN.objects.filter(vendorId=vendor).get(asnId=asn_id)
            else:
                asn = ASN.objects.get(asnId=asn_id)

            obj = asn.asJson()
            # Append GRN details
            try:
                grndetail = GRN.objects.get(asnId_id=asn.id)
                obj["grn"] = grndetail.asJson()
            except GRN.DoesNotExist as e:
                pass

            return respond_success(obj)
        except ASN.DoesNotExist:
            # https://stackoverflow.com/questions/5508888/matching-query-does-not-exist-error-in-django
            return respond_error("ASN not present", status=404)

    except Exception as Ex:
        print (traceback.format_exc())
        return respond_error(f"Error: {Ex.args}")


@csrf_exempt
@require_http_methods(["GET"])
def get_all_asn(request):
    try:
        request_data = request.GET
        page_seq  = int(request_data.get("page_seq", default=0))
        page_size = int(request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        grnUpdated = request_data.get("grnUpdated", default=None)
        grnConfirm = request_data.get("grnConfirmed", default=None)

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        userId = request.META.get("auth").get("tokenObject")
        allowedWarehouse = userId["warehouseId"] if "warehouseId" in userId else None

        try:
            filters = {}
            if grnUpdated is not None:
                grnUpdated = grnUpdated.lower()
                grnUpdated = grnUpdated == "true"
                filters["grnUpdated"] = grnUpdated

            if not (allowedWarehouse is None or allowedWarehouse == "WAREHOUSE_ALL"):
                try:
                    warehouse = WarehouseMaster.objects.get(id=allowedWarehouse)
                    filters["warehouseId"] = warehouse
                except WarehouseMaster.DoesNotExist as e:
                    return respond_error("Warehouse Id does not exist")

            if grnConfirm is not None:
                grnConfirm = grnConfirm.lower()
                grnConfirm = grnConfirm == "true"
                filters["grnConfirmed"] = grnConfirm
            if vendor is not None:
                filters["vendorId"] = vendor

            items = ASN.objects.filter(**filters)
            count = items.count()

            startIndex = (max(0,page_seq - 1)) * page_size
            endIndex = min(startIndex + page_size, count)
            if startIndex > count:
                return respond_error({"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

            allObjects = items[startIndex:endIndex]
            retObjects = [x.asJson() for x in allObjects]

            # Append GRN details
            for obj in retObjects:
                try:
                    grndetail = GRN.objects.get(asnId_id=obj["id"])
                    obj["grn"] = grndetail.asJson()
                except GRN.DoesNotExist as e:
                    pass

            def sortFuncOnId(x):
                return x["id"]

            #retObjects.sort(key=sortFuncOnId)

            return respond_success({
                "totalCount": count,
                "pageNum": page_seq,
                "payloads": retObjects
            })
        except Exception as e:
            print (traceback.format_exc())
            return respond_error(f"Error: {e.args}")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")


@csrf_exempt
@require_http_methods(["POST"])
def add_asn(request):
    try:
        # Collate request data
        request_data = json.loads(request.body)

        payload = request_data["payload"]
        warehouseId = payload["warehouseId"]

        try:
            schemaValidator(instance=request_data, schema=requestschema.schemaAddASN)
        except Exception as e:
            return respond_error(e.args[0] if len(e.args) > 0 else e.args)

       # try:
       #     schemaValidator(instance=payload, schema=schemaasn.asn)
       # except Exception as e:
       #     return respond_error(e.args[0] if len(e.args) > 0 else e.args)

        # Save to DB
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        userId = request.META.get("auth").get("tokenObject").get("userId")
        user = VendorUsers.objects.get(email=userId)

        try:
            warehouse = WarehouseMaster.objects.get(id=warehouseId)
        except WarehouseMaster.DoesNotExist as e:
            return respond_error("Warehouse Id does not exist")

        asn = ASN(
            vendorUser=user,
            payload=payload,
            vendorId=vendor,
            warehouseId=warehouse,
            warehouseIdHops=[],
            warehouseIdHopsLogs=[]
        )
        asn.save()
        return respond_success(f"ASN added # {asn.id}")

    except Exception as Ex:
        print (traceback.format_exc())
        return respond_error(f"Error: {Ex.args}")


@csrf_exempt
@require_http_methods(["POST"])
def confirm_grn(request):
    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = Vendor.objects.get(id=vendorId)

        request_data = json.loads(request.body)

        try:
            schemaValidator(instance=request_data, schema=requestschema.schemaConfirmASN)
        except Exception as e:
            return respond_error(e.args[0] if len(e.args) > 0 else e.args)

        payload = request_data["payload"]

        asnIdInput = payload["asnNumber"]
        grnId = payload["grnNumber"]
        confirm = payload["confirm"]
        grnPayload = payload["grnPayload"]

        grn = GRN.objects.get(grnId=grnId, vendorId=vendor)
        if grn.asnId.asnId != asnIdInput:
            return respond_error("Input AsnId does not match with internal GRN to ASN mapping")

        asn = ASN.objects.get(asnId=asnIdInput)
        if asn.grnUpdated == False:
            return respond_error(f"ASN Could not be confirmed as QC is not yet completed.")

        if asn.grnConfirmed == False:
            asn.grnConfirmed = confirm
            asn.save()

            grn.confirmPayload = grnPayload
            grn.stageStockIn = "ToStock"
            grn.save()

            return respond_success(f"ASN confirmed as {confirm}")
            
        else:
            return respond_error(f"ASN already confirmed by both parties")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error {e.args}")


@csrf_exempt
@require_http_methods(["GET"])
def get_all_grn(request):
    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        request_data = request.GET
        page_seq  = int(request_data.get("page_seq", default=0))
        page_size = int(request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        grnConfirm = request_data.get("grnConfirmed", default=None)
        stageStockIn = request_data.get("stageStockIn", default=None)
        grnObjects = None

        userId = request.META.get("auth").get("tokenObject")
        allowedWarehouse = userId["warehouseId"] if "warehouseId" in userId else None

        try:
            filters = {}
            if vendor is not None:
                filters["vendorId"] = vendor

            if stageStockIn is not None:
                filters["stageStockIn"] = stageStockIn

            if not (allowedWarehouse is None or allowedWarehouse == "WAREHOUSE_ALL"):
                try:
                    warehouse = WarehouseMaster.objects.get(id=allowedWarehouse)
                    filters["warehouseId"] = warehouse
                except WarehouseMaster.DoesNotExist as e:
                    return respond_error("Warehouse Id does not exist")

            if grnConfirm is not None:
                grnConfirm = grnConfirm.lower()
                grnConfirm = grnConfirm == "true"
                if not grnConfirm:
                    print ("GRN CONFIRM: ", grnConfirm)
                    grnObjects = GRN.objects.exclude(confirmPayload__isnull=False).exclude(confirmPayload__exact='')

            if grnObjects is None:
                grnObjectsFiltered = GRN.objects.filter(**filters)
            else:
                grnObjectsFiltered = grnObjects.filter(**filters)

            count = grnObjectsFiltered.count()

            startIndex = (max(0,page_seq - 1)) * page_size
            endIndex = min(startIndex + page_size, count)

            if startIndex > count:
                return respond_error({"totalCount": count, "payloads": None, "reason": "startIndex more than total count"})

            allObjects = grnObjectsFiltered[startIndex:endIndex]
            retObjects = [x.asJson() for x in allObjects]

            def sortFuncOnId(x):
                return x["id"]

            retObjects.sort(key=sortFuncOnId)

            return respond_success({
                "totalCount": count,
                "pageNum": page_seq,
                "payloads": retObjects
            })
        except Exception as e:
            print (traceback.format_exc())
            return respond_error(f"Error: {e.args}")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error: {e.args}")



@csrf_exempt
@require_http_methods(["POST"])
def add_grn(request):
    try:
        request_data = json.loads(request.body)

        payload = request_data["payload"]

        try:
            schemaValidator(instance=request_data, schema=requestschema.schemaAddGRN)
        except Exception as e:
            return respond_error(e.args[0] if len(e.args) > 0 else e.args)

       # try:
       #     schemaValidator(instance=payload, schema=schemagrn.grn)
       # except Exception as e:
       #     return respond_error(e.args[0] if len(e.args) > 0 else e.args)

        userId = request.META.get("auth").get("tokenObject").get("userId")
        user = WarehouseUsers.objects.get(email=userId)

        asnId = payload["asnNumber"]
        asn = ASN.objects.get(asnId=asnId)
        if asn.grnUpdated == False:
            
            grn = GRN(
                warehouseUser=user,
                payload=payload,
                asnId=asn,
                vendorId=asn.vendorId,
                warehouseId=asn.warehouseId
            )
            grn.save()

            asn.grnUpdated = True
            asn.save()

            return respond_success(f"GRN Created: # {grn.id}")

        else:
            return respond_error(f"QC Already processed")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error {e.args}")

@csrf_exempt
@require_http_methods(["GET"])
def get_grn(request):
    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        vendor = None
        if vendorId != "VENDOR_ALL":
            vendor = Vendor.objects.get(id=vendorId)

        request_data = request.GET
        grn_id = request_data.get("id")

        try:
            filters = {}
            if vendor is not None:
                filters["vendorId"] = vendor
            grn = GRN.objects.filter(**filters).get(grnId=grn_id)
            asnId = grn.asnId
            retObject = {
                "grn": grn.asJson(),
                "asn": asnId.asJson()
            }
            return respond_success(retObject)

        except Exception as e:
            print (traceback.format_exc())
            return respond_error("GRN not present", status=404)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(f"Error {e.args}")

