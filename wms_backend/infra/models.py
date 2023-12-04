from django.db import models

import datetime
from uuid import uuid4
from django.utils import timezone
from django.core import serializers

from utils import barcode

class Vendor(models.Model):

    id = models.AutoField(primary_key=True)
    vendorId = models.CharField(max_length=100)

    created_ts = models.DateTimeField(auto_now_add=True)  # when object was created
    updated_ts = models.DateTimeField(auto_now=True)  # when object was last updated

    payload = models.JSONField()  # Data payload in JSON from schema
    address = models.JSONField()  # Multiple Addresses should be kept here

    billing = models.JSONField()

    warehouseId = models.ForeignKey(
        "WarehouseMaster",
        on_delete=models.CASCADE,
        blank=True,
        null=True)

    class Meta:
        app_label = "infra"
        ordering = ("payload__name",)

    def get_payload(self):
        return self.payload

    def appendAddress(self, address):
        self.address.append(address)
        self.save()

    def deleteAddress(self, addressId):
        allAdd = self.address
        if addressId in self.address:
            del(self.address[addressId])
        self.save()

    def asJson(self):
        obj = {
            "id":         self.id,
            "vendorId":   self.vendorId,
            "createddate":self.created_ts.strftime("%d-%m-%Y"),
            "createdtime":self.created_ts.strftime("%H:%M"),
            "payload":    self.payload,
            "address":    self.address,
            "billing":    self.billing
        }

        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(Vendor, self).save(*args, **kwargs)
        if self.vendorId is None or self.vendorId == '':
            vendorId = "{}{}".format("VEN-",self.id)
            self.vendorId = vendorId
        return super(Vendor, self).save(*args, **kwargs)


class VendorExternalIntegration(models.Model):

    class Meta:
        app_label = "infra"

    id = models.AutoField(primary_key=True)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    shopify = models.JSONField(null=True, blank=True)
    email = models.JSONField(null=True, blank=True)

    def asJson(self):
        obj = {
            "shopify": {
                "success": False
            },
            "email": self.email
        }
        if self.shopify is not None and self.shopify["success"]:
            obj["shopify"]["success"] = self.shopify["success"]
            obj["shopify"]["shopUrl"] = self.shopify["shopUrl"]
            obj["shopify"]["date"] = self.shopify["webhook"]["orders/create"]["response"]["webhook"]["created_at"]
        return obj

class VendorUsers(models.Model):

    email   = models.CharField(primary_key=True, max_length=100)
    name    = models.CharField(max_length=100)
    passw   = models.CharField(max_length=100)
    phone   = models.CharField(max_length=100)

    created_ts = models.DateTimeField(auto_now_add=True)
    updated_ts = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "infra"

    def asJson(self):
        js = {
            "email"      : self.email,
            "name"       : self.name,
            "phone"      : self.phone,
            "createddate": self.created_ts.strftime("%d-%m-%Y"),
            "createdtime": self.created_ts.strftime("%H:%M"),
        }
        return js

    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)


class VendorUserToken(models.Model):

    id          = models.CharField(primary_key=True, max_length=100)
    userId      = models.ForeignKey(VendorUsers, on_delete=models.CASCADE)
    vendorId    = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    created     = models.DateTimeField(auto_now_add=True)


    class Meta:
        app_label = "infra"

    def createToken(self):
        self.id = str(uuid4())

    def update(self):
        self.created = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.id is None or self.id == "":
            self.createToken()
        return super(VendorUserToken, self).save(*args, **kwargs)

    def asJson(self, update=False):
        js = {
            "userId": self.userId.email,
            "vendorId": self.vendorId.id
        }
        if update:
            self.update()
        return js


    @classmethod
    def delete_old_records(cls, minutes=1440):
        cut_off = timezone.now() - datetime.timedelta(minutes=minutes)
        cls.objects.filter(created__lt=cut_off).delete()


class WarehouseUsers(models.Model):

    email   = models.CharField(primary_key=True, max_length=100)
    name    = models.CharField(max_length=100)
    passw   = models.CharField(max_length=100)
    phone   = models.CharField(max_length=100)
    role    = models.CharField(max_length=50)

    warehouseId = models.ForeignKey("WarehouseMaster", blank=True, null=True, on_delete=models.SET_NULL)

    created_ts = models.DateTimeField(auto_now_add=True)
    updated_ts = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "infra"

    def asJson(self):
        js = {
            "email"      : self.email,
            "name"       : self.name,
            "phone"      : self.phone,
            "role"       : self.role,
            "createddate": self.created_ts.strftime("%d-%m-%Y"),
            "createdtime": self.created_ts.strftime("%H:%M"),
        }
        if self.warehouseId is not None:
            js["wId"] = self.warehouseId.qualifiedName
        return js


class WarehouseUserToken(models.Model):

    class Meta:
        app_label = "infra"

    id          = models.CharField(primary_key=True, max_length=100)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    created     = models.DateTimeField(auto_now_add=True)

    def createToken(self):
        self.id = str(uuid4())

    def update(self):
        self.created = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.id is None or self.id == "":
            self.createToken()
        return super(WarehouseUserToken, self).save(*args, **kwargs)

    def asJson(self, update=False):
        js = {
            "userId": self.userId.email,
            "vendorId": "VENDOR_ALL",
        }

        js["warehouseId"] = "WAREHOUSE_ALL" if self.userId.warehouseId is None else self.userId.warehouseId.id

        if update:
            self.update()
        return js


    @classmethod
    def delete_old_records(cls, minutes=1440):
        cut_off = timezone.now() - datetime.timedelta(minutes=minutes)
        cls.objects.filter(created__lt=cut_off).delete()



class WarehouseMaster(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id = models.AutoField(primary_key=True)             # 1
    warehouseId = models.CharField(max_length=100)      # W1
    type = models.CharField(                            # For Future
        max_length=100,
        blank=True,
        null=True)
    qualifiedName = models.CharField(max_length=100)    # W1
    name = models.CharField(max_length=100)             # Sherlock : Friendly Name
    address = models.JSONField()                        # Some address JSON
    contactDetails = models.JSONField()                 # Some warehouse related contact details only
    managers = models.JSONField()                       # link to warehouse users table

    barcode = models.CharField(max_length=200,
        null=True,
        blank=True)          # Path to barcode file in S3

    created     = models.DateTimeField(auto_now_add=True)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)

    def asJson(self):
        obj = {
            "id": self.id,
            "qualifiedName": self.qualifiedName,
            "address": self.address,
            "contact": self.contactDetails,
            "name": self.name,
            "managers": self.managers,
            "user": self.userId.email,
            "type": self.type,
            "created": str(self.created),
            "barcode": self.barcode
        }
        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(WarehouseMaster, self).save(*args, **kwargs)
        if self.warehouseId is None or self.warehouseId == "" or self.qualifiedName is None or self.qualifiedName == "":
                self.warehouseId = "W{}".format(self.id)
                self.qualifiedName = self.warehouseId
        if self.barcode is None:
            response = barcode.handleBarCode(self.qualifiedName, "WH")
            if response["uploaded"]:
                self.barcode = response["path"]
        return super(WarehouseMaster, self).save(*args, **kwargs)


class WarehouseZones(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id = models.AutoField(primary_key=True)             # 1

    warehouseId = models.ForeignKey(                    # FK: W1(1)
        WarehouseMaster,
        on_delete=models.CASCADE
    )
    zoneId = models.CharField(max_length=100)           # 0F
    type = models.CharField(max_length=100,             # If there are any categories that has to be specified
        blank=True,
        null=True)
    qualifiedName = models.CharField(max_length=100)    # W1|2F
    zoneName = models.CharField(max_length=100)         # Some friendly Name
    description = models.CharField(max_length=100)      # Some friendly descriptions
    floor = models.CharField(max_length=50)             # 2
    mezzanine = models.BooleanField(default=False)      # If the zone is a mezzanine

    barcode = models.CharField(max_length=200,
        null=True,
        blank=True)          # Path to barcode file in S3

    created     = models.DateTimeField(auto_now_add=True)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)


    def asJson(self):
        obj = {
            "id": self.id,
            "warehouseId": self.warehouseId.id,
            "zoneId": self.zoneId,
            "type": self.type,
            "qualifiedName": self.qualifiedName,
            "name": self.zoneName,
            "description": self.description,
            "floor": self.floor,
            "mezzanine": self.mezzanine,
            "created": str(self.created),
            "user": self.userId.email,
            "barcode": self.barcode
        }

        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(WarehouseZones, self).save(*args, **kwargs)
        if self.zoneId is None or self.zoneId == "" or self.qualifiedName is None or self.qualifiedName == "":
                self.zoneId = "{}".format(self.floor)
                if self.mezzanine:
                    self.zoneId = "{}-{}".format(self.zoneId, "MZ")
                self.qualifiedName = "{}.{}".format(
                    self.warehouseId.qualifiedName,
                    self.zoneId
                )
        if self.barcode is None:
            response = barcode.handleBarCode(self.qualifiedName, "WH")
            if response["uploaded"]:
                self.barcode = response["path"]
        return super(WarehouseZones, self).save(*args, **kwargs)


class WarehouseLocations(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id = models.AutoField(primary_key=True)             # 1
    zoneId = models.ForeignKey(
        WarehouseZones,
        on_delete=models.CASCADE
    )
    locationId = models.CharField(max_length=100)       # L1
    type = models.CharField(max_length=100)             # If there are any categories that has to be specified
    qualifiedName = models.CharField(max_length=100)    # W1|2F|L1-GNRL
    name = models.CharField(max_length=100)             # Some friendly name
    description = models.CharField(max_length=100)      # Some friendly descriptions
    group = models.CharField(max_length=100)            # Useless Location Group: "chatri"
    counts = models.JSONField()                         # Counts of Aisle, Rack, Shelf and Bins

    barcode = models.CharField(max_length=200,
        null=True,
        blank=True)          # Path to barcode file in S3

    created     = models.DateTimeField(auto_now_add=True)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)

    def asJson(self):
        obj = {
            "id": self.id,
            "zoneId": self.zoneId.id,
            "locationId": self.locationId,
            "type": self.type,
            "qualifiedName": self.qualifiedName,
            "name": self.name,
            "description": self.description,
            "group": self.group,
            "counts": self.counts,
            "user": self.userId.email,
            "created": str(self.created),
            "active": self.active,
            "barcode": self.barcode
        }
        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(WarehouseLocations, self).save(*args, **kwargs)

        if self.locationId is None or self.locationId == "" or self.qualifiedName is None or self.qualifiedName == "":
            self.locationId = "L{}-{}".format(self.id, self.type)
            self.qualifiedName = "{}.{}".format(
                self.zoneId.qualifiedName,
                self.locationId
            )
        if self.barcode is None:
            response = barcode.handleBarCode(self.qualifiedName, "WH")
            if response["uploaded"]:
                self.barcode = response["path"]
        return super(WarehouseLocations, self).save(*args, **kwargs)

class WarehouseShelves(models.Model):

    # 2rows:
    # Row1: Id:1, name: W1|2F|GNRL|L1|A1|R1|S1|B1
    # Row2: Id:2, name: W1|2F|GNRL|A1|R1|S1|B2


    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id = models.AutoField(primary_key=True)             # 1
    locationId = models.ForeignKey(                     # FK: 0F
        WarehouseLocations,
        on_delete=models.CASCADE
    )
    shelfId = models.CharField(max_length=100)          # A1|R1|S1
    internalAisleId = models.CharField(max_length=100)  # Aisle Id
    internalRackId = models.CharField(max_length=100)   # Rack Id
    internalShelfId = models.CharField(max_length=100)  # Shelf Id
    qualifiedName = models.CharField(max_length=100)    # W1|2F|L1-GNRL|A1|R1|S1

    shelfName = models.CharField(max_length=100,        # Some friendly Name
        null=True,
        blank=True)

    optionalBin = models.BooleanField(default=False)    # If cartoon can be placed in place of Bin
    binIds = models.JSONField()                         # List of Bins attached to this shelf
    binCapacity = models.IntegerField(default=10)

    vendorBlocked = models.BooleanField(default=False)  # If this location is completely booked by a vendor
    vendorIds = models.JSONField()                      # Store of current list of vendors using this location
    skuIds = models.JSONField()                         # Store of current list of SKUs using this location

    full = models.BooleanField(default=False)           # If the bin is full
    _occupied = models.BooleanField(default=False)      # To be set True / False at the time of saving

    barcode = models.CharField(max_length=200,
        null=True,
        blank=True)          # Path to barcode file in S3

    created     = models.DateTimeField(auto_now_add=True)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)


    def asJson(self, storage=False):
        obj = {
            "id": self.id,
            "locationId": self.locationId.id,
            "shelfId": self.shelfId,
            "internalAisleId": self.internalAisleId,
            "internalRackId": self.internalRackId,
            "internalShelfId": self.internalShelfId,
            "qualifiedName": self.qualifiedName,
            "shelfName": self.shelfName,
            "optionalBin": self.optionalBin,
            "binIds": self.binIds,
            "binCapacity": self.binCapacity,
            "created": str(self.created),
            "user": self.userId.email,
            "active": self.active,
            "barcode": self.barcode
        }

        if storage:
            obj["vendorBlocked"] = self.vendorBlocked
            obj["vendorIds"] = self.vendorIds
            obj["skuIds"] = self.skuIds
            obj["full"] = self.full

        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(WarehouseShelves, self).save(*args, **kwargs)

        if self.shelfId is None or self.shelfId == "" or self.qualifiedName is None or self.qualifiedName == "":
            self.shelfId = "A{}-R{}-S{}".format(
                self.internalAisleId,
                self.internalRackId,
                self.internalShelfId
            )
            self.qualifiedName = "{}.{}".format(
                self.locationId.qualifiedName,
                self.shelfId
            )
        if self.barcode is None:
            response = barcode.handleBarCode(self.qualifiedName, "WH")
            if response["uploaded"]:
                self.barcode = response["path"]
        return super(WarehouseShelves, self).save(*args, **kwargs)


class WarehouseBinsAndTrolley(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id = models.AutoField(primary_key=True)             # 1
    warehouseId = models.ForeignKey(                    # FK: WarehouseMaster
        WarehouseMaster,
        on_delete=models.CASCADE)

    binId = models.CharField(max_length=100)            # Bin Id: B1 or T1
    qualifiedName = models.CharField(max_length=100)    # W1|B1
    type = models.CharField(max_length=100)             # One of Bins And Trolley

    full = models.BooleanField(default=False)           # If the bin is full
    _occupied = models.BooleanField(default=False)      # To be set True / False at the time of saving

    vendorIds = models.JSONField()                      # Store of current list of vendors using this location
    skuIds = models.JSONField()                         # Store of current list of SKUs using this location

    barcode = models.CharField(max_length=200,
        null=True,
        blank=True)                                     # Path to barcode file in S3

    created     = models.DateTimeField(auto_now_add=True)
    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)

    def asJson(self, storage=False):
        js = {
            "id": self.id,
            "warehouseId": self.warehouseId.id,
            "binId": self.binId,
            "qualifiedName": self.qualifiedName,
            "type": self.type,
            "barcode": self.barcode
        }
        if storage:
            js["full"] = self.full
            js["occupied"] = self._occupied
            js["vendorIds"] = self.vendorIds
            js["skuIds"] = self.skuIds

        return js

    def save(self, *args, **kwargs):
        if self.id is None:
            super(WarehouseBinsAndTrolley, self).save(*args, **kwargs)

        if self.binId is None or self.binId == "" or self.qualifiedName is None or self.qualifiedName == "":
            type = self.type[0]
            self.binId = "{}-{}".format(type, self.id)
            self.qualifiedName = "{}.{}".format(
                self.warehouseId.qualifiedName,
                self.binId
            )

        if self.barcode is None:
            response = barcode.handleBarCode(self.qualifiedName, "WH")
            if response["uploaded"]:
                self.barcode = response["path"]

        return super(WarehouseBinsAndTrolley, self).save(*args, **kwargs)


class WarehouseLocationLogs(models.Model):

    class Meta:
        app_label = "infra"

    id = models.AutoField(primary_key=True)             # 1
    logId = models.CharField(max_length=100)            # Some UUID

    created_ts = models.DateTimeField(auto_now_add=True)
    updated_ts = models.DateTimeField(auto_now=True)

    vendorId = models.ForeignKey(                       # FK: VendorId
        Vendor,
        on_delete=models.CASCADE)
    shelfId = models.ForeignKey(                        # FK: ShelfId
        WarehouseShelves,
        on_delete=models.CASCADE)
    locationId = models.ForeignKey(                     # FK: LocationId
        WarehouseLocations,
        on_delete=models.CASCADE)
    zoneId = models.ForeignKey(                         # FK: ZoneId
        WarehouseZones,
        on_delete=models.CASCADE)
    warehouseId = models.ForeignKey(                    # FK: WarehouseId
        WarehouseMaster,
        on_delete=models.CASCADE)

    direction = models.CharField(max_length=100)        # "In" / "Out" of Bin
    timeOfIncident = models.DateTimeField()             # Time of incident

    balanceItemsBeforeIncident = models.JSONField()     # skuIds from WarehouseBins before Incident
    balanceItemsAfterIncident  = models.JSONField()     # skuIds from WarehouseBins after Incident

    vendorIdsBeforeIncident = models.JSONField()        # vendorIds from WarehouseBins before Incident
    vendorIdsAfterIncident = models.JSONField()         # vendorIds from WarehouseBins after Incident
    vendorBlocked = models.BooleanField(default=False)  # vendorBlocked from WarehouseBins

    userId      = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    active      = models.BooleanField(default=True)


    def asJson(self, full=False):
        obj = {
            "logId": self.logId,
            "created_ts": self.created_ts,
            "updated_ts": self.updated_ts,
            "vendorId": self.vendorId,
            "locationId": self.locationId,
            "zoneId": self.zoneId,
            "warehouseId": self.warehouseId,
            "direction": self.direction,
            "timeOfIncident": self.timeOfIncident
        }

        if full:
            obj["balanceItemsBeforeIncident"] = self.balanceItemsBeforeIncident
            obj["balanceItemsAfterIncident"] = self.balanceItemsAfterIncident
            obj["vendorIdsBeforeIncident"] = self.vendorIdsBeforeIncident
            obj["vendorIdsAfterIncident"] = self.vendorIdsAfterIncident
            obj["vendorBlocked"] = self.vendorBlocked

        return obj

class Inventory(models.Model):

    class Meta:
        app_label = "infra"
        constraints = [
            models.UniqueConstraint(
                fields=["vendorId", "skuNumber", "variantId", "batchNumber"],
                name="vendorSkuInventory"
            )
        ]
        ordering = ("payload__packageDescription", "skuNumber")

    id = models.AutoField(primary_key=True)             # 1
    warehouseId = models.ForeignKey(
        WarehouseMaster, on_delete=models.CASCADE
    )
    live = models.BooleanField(default=True)            # if an item has to be parked - this can be False
    created_ts = models.DateTimeField(auto_now_add=True)
    updated_ts = models.DateTimeField(auto_now=True)

    vendorId = models.ForeignKey(
        Vendor, on_delete=models.CASCADE
    )
    skuNumber = models.CharField(max_length=100)
    variantId = models.CharField(max_length=100)
    skuReference = models.ForeignKey(
        "inbound.SKU", on_delete=models.PROTECT, null=False, blank=False
    )
    currentQuantity = models.BigIntegerField()
    batchNumber = models.CharField(max_length=100)
    payload = models.JSONField()

    locationType = models.CharField(max_length=10)

    stepLive = models.DateTimeField()
    allocatedShelfId = models.ForeignKey(
        WarehouseShelves, on_delete=models.CASCADE
    )
    allocatedBinId = models.ForeignKey(
        WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True
    )

    moveQInitiated   = models.BooleanField(default=False)
    finishedQMove    = models.BooleanField(default=False)
    alteredWithMoveQ = models.BooleanField(default=False)

    def asJson(self):
        obj = {
            "id": self.id,
            "warehouseId": self.warehouseId.id,
            "live": self.live,
            "vendorId": self.vendorId.id,
            "skuNumber": self.skuNumber,
            "currentQuantity": self.currentQuantity,
            "batchNumber": self.batchNumber,
            "payload": self.payload,
            "payloadSku": self.skuReference.asJson(),
            "locationType": self.locationType,
            "alteredWithMoveQ": self.alteredWithMoveQ,
            "moveQInitiated": self.moveQInitiated,
            "finishedQMove": self.finishedQMove
        }
        if self.allocatedShelfId is not None:
            obj["shelfId"] = self.allocatedShelfId.asJson()
        else:
            obj["shelfId"] = None
        if self.allocatedBinId is not None:
            obj["binId"] =  self.allocatedBinId.asJson()
        else:
            obj["binId"] = None

        return obj

class ShelvingLogs(models.Model):

    id = models.AutoField(primary_key=True)
    warehouseId = models.ForeignKey(
        WarehouseMaster, on_delete=models.CASCADE
    )

    created_ts = models.DateTimeField(auto_now_add=True)
    updated_ts = models.DateTimeField(auto_now=True)

    step = models.CharField(max_length=20)
        # StockIn, Transport, Shelving, DELETE(when entry could be twice and has to be deleted)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    asn = models.CharField(max_length=100)
    grn = models.CharField(max_length=100)
    boxSeq = models.CharField(max_length=20, null=True, blank=True)
    skuNumber = models.CharField(max_length=100)
    variantId = models.CharField(max_length=100)
    skuReference = models.ForeignKey(
        "inbound.SKU", on_delete=models.PROTECT, null=False, blank=False
    )
    currentQuantity = models.BigIntegerField()
    batchNumber = models.CharField(max_length=100)
    payload = models.JSONField()
    locationType = models.CharField(max_length=10)

    stepStockIn_ts = models.DateTimeField(null=True, blank=True)
    allocatedShelfId = models.ForeignKey(
        WarehouseShelves, on_delete=models.CASCADE, null=True, blank=True, related_name="allocatedShelfId"
    )
    allocatedBinId = models.ForeignKey(
        WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True, related_name="allocatedBinId"
    )

    stepTransport_ts = models.DateTimeField(null=True, blank=True)
    transportTrolleyId = models.ForeignKey(
        WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True, related_name="transportTrolleyId"
    )
    transportBinId = models.ForeignKey(
        WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True, related_name="transportBinId"
    )
    stepShelving = models.DateTimeField(null=True, blank=True)
    confirmedShelfId = models.ForeignKey(
        WarehouseShelves, on_delete=models.CASCADE, null=True, blank=True, related_name="confirmedShelfId"
    )
    confirmedBinId = models.ForeignKey(
        WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True, related_name="confirmedBinId"
    )

    class Meta:
        app_label = "infra"
        constraints = [
            models.UniqueConstraint(
                fields=['skuNumber', 'variantId', 'asn', 'grn', 'boxSeq'],
                name="shelvingUniqueReference"
            )
        ]

    def asJson(self):

        obj = {
            "id": self.id,
            "warehouseId": self.warehouseId.id,
            "created_ts": self.created_ts.strftime("%d-%m-%Y %H:%M"),
            "updated_ts": self.updated_ts.strftime("%d-%m-%Y %H:%M"),
            "step": self.step,
            "boxSeq": self.boxSeq,
            "vendorId": self.vendorId.vendorId,
            "asnId": self.asn,
            "grnId": self.grn,
            "skuNumber": self.skuNumber,
            "locationType": self.locationType,
            "variantId": self.variantId,
            "currentQuantity": self.currentQuantity,
            "batchNumber": self.batchNumber,
            "payload": self.payload,
            "payloadSku": self.skuReference.payload,
            "stepStockIn_ts": self.stepStockIn_ts.strftime("%d-%m-%Y %H:%M") if self.stepStockIn_ts is not None else None,
            "stepTransport_ts": self.stepTransport_ts.strftime("%d-%m-%Y %H:%M") if self.stepTransport_ts is not None else None,
            "stepShelving": self.stepShelving.strftime("%d-%m-%Y %H:%M") if self.stepShelving is not None else None,
        }

        obj["allocatedShelfId"] = self.allocatedShelfId.id if self.allocatedShelfId is not None else None
        obj["allocatedBinId"] = self.allocatedBinId.id if self.allocatedBinId is not None else None
        obj["allocatedShelfName"] = self.allocatedShelfId.qualifiedName if self.allocatedShelfId is not None else None
        obj["allocatedBinName"] = self.allocatedBinId.qualifiedName if self.allocatedBinId is not None else None
        obj["transportTrolleyId"] = self.transportTrolleyId.id if self.transportTrolleyId is not None else None
        obj["transportBinId"] = self.transportBinId.id if self.transportBinId is not None else None
        obj["confirmedShelfId"] = self.confirmedShelfId.id if self.confirmedShelfId is not None else None
        obj["confirmedBinId"] = self.confirmedBinId.id if self.confirmedBinId is not None else None

        return obj

class StockMoveQ(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("-id",)


    id              = models.AutoField(primary_key=True)

    createdDate     = models.DateTimeField(auto_now_add=True)
    updatedDate     = models.DateTimeField(auto_now=True)

    inventoryId     = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    userId          = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE)
    movePayload     = models.JSONField(null=True, blank=True) # To store movement trolley and binId as multiple Foreign Key not possible

    targetShelfId   = models.ForeignKey(WarehouseShelves, on_delete=models.CASCADE, null=True, blank=True)
    targetBinId     = models.ForeignKey(WarehouseBinsAndTrolley, on_delete=models.CASCADE, null=True, blank=True)

    quantity        = models.BigIntegerField() # Quantity being moved - in case when support is enabled for multiple shelf - then this might be less otherwise this value is always be the currentQuantity of the inventory log
    shelvedBack     = models.BooleanField(default=False)

    def asJson(self):
        obj = {
            "id": self.id,
            "createdDate": self.createdDate.strftime("%d-%m-%Y %H:%M") if self.createdDate is not None else None,
            "updatedDate": self.updatedDate.strftime("%d-%m-%Y %H:%M") if self.createdDate is not None else None,
            "inventoryId": self.inventoryId.asJson(),
            "userId": self.userId.asJson(),
            "movePayload": self.movePayload,
            "targetShelfId": self.targetShelfId.asJson() if self.targetShelfId is not None else None,
            "targetBinId": self.targetBinId.asJson() if self.targetBinId is not None else None,
            "quantity": self.quantity,
            "shelvedBack": self.shelvedBack
        }

        return obj


class Orders(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("-id",)

    id              = models.AutoField(primary_key=True)
    vendorCreated   = models.BooleanField()
    vendorUserId    = models.ForeignKey(VendorUsers, on_delete=models.CASCADE, null=True, blank=True)
    warehouseUserId = models.ForeignKey(WarehouseUsers, on_delete=models.CASCADE, null=True, blank=True)
    userId          = models.JSONField() # To be always used - could be either of vendorUser or warehouseUser - asJSON

    orderProgressStatus = models.CharField(max_length=50)
    # CREATED, PICKED, SORTDROP, QC, PACKED, SHIPPED, DELIVERED
    # RETURNED, CANCELLED

    source          = models.CharField(max_length=25)       # ORDER FORM, SOHPIFY etc
    externalDump    = models.JSONField(null=True, blank=True)   # Full dump of Shopify or other webhook response

    vendorId        = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    externalOrderId = models.CharField(max_length=100, null=True, blank=True)
    originalDate    = models.DateTimeField(null=True, blank=True)
    createdDate     = models.DateTimeField(auto_now_add=True)
    updatedDate     = models.DateTimeField(auto_now=True)

    items           = models.JSONField()
    customer        = models.JSONField()
    billingCurrency = models.CharField(max_length=10)
    billingAmount   = models.BigIntegerField()
    warehouseId     = models.ForeignKey(WarehouseMaster, on_delete=models.CASCADE, null=True, blank=True)

    def asJson(self):
        obj = {
            "id": self.id,
            "vendorCreated": self.vendorCreated,
            "vendorUserId": self.vendorUserId.asJson() if self.vendorUserId is not None else None,
            "warehouseUserId": self.warehouseUserId.asJson() if self.warehouseUserId is not None else None,
            "userId": self.userId,
            "orderProgressStatus": self.orderProgressStatus,
            "source": self.source,
            #"externalDump": self.externalDump if self.externalDump is not None else None,
            "vendorId": self.vendorId.payload,
            "externalOrderId": self.externalOrderId if self.externalOrderId is not None else None,
            "originalDate": self.originalDate.strftime("%d-%m-%Y %H:%M") if self.originalDate is not None else None,
            "createdDate": self.createdDate.strftime("%d-%m-%Y %H:%M") if self.createdDate is not None else None,
            "items": self.items,
            "customer": self.customer,
            "billingCurrency": self.billingCurrency,
            "billingAmount": self.billingAmount,
            "warehouseId": self.warehouseId.asJson() if self.warehouseId is not None else None
        }

        return obj

class OrderItems(models.Model):

    id              = models.AutoField(primary_key=True)
    orderId         = models.ForeignKey(Orders, on_delete=models.PROTECT, null=False, blank=False)
    itemStatus      = models.JSONField() # {"created:": { "flag": True, "timestamp": "", "userId":  }}
    recentStatus    = models.CharField(max_length=20)
    itemPayload     = models.JSONField()
    warehouseId     = models.ForeignKey(WarehouseMaster, on_delete=models.PROTECT)
    shippingNumber  = models.ForeignKey("ShippingDetails", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        app_label = "infra"

    def asJson(self):

        obj = {
            "id": self.id,
            "orderId": self.orderId.id,
            "itemStatus": self.itemStatus,
            "recentStatus": self.recentStatus,
            "itemPayload": self.itemPayload,
        }

        return obj

class ShippingDetails(models.Model):

    class Meta:
        app_label = "infra"

    id = models.AutoField(primary_key=True)
    orderId = models.ForeignKey(Orders, on_delete=models.PROTECT, null=True, blank=True)
    orderItems = models.JSONField()
    asn = models.ForeignKey("inbound.asn", on_delete=models.PROTECT, null=True, blank=True)
    awbNumber = models.CharField(max_length=50)
    direction = models.CharField(max_length=5) # OUT: To Customer, IN: To Warehouse
    payload = models.JSONField() # Contains shipping details
    deliveryAgent = models.ForeignKey(WarehouseUsers, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=25, null=True, blank=True) # CREATED, IN-TRANSIT, DELIVERED, CANCELLED

    def asJson(self):

        obj = {
            "id": self.id,
            "orderItems": self.orderItems,
            "awbNumber": self.awbNumber,
            "direction": self.direction,
            "payload": self.payload,
            "status": self.status
        }
        if self.orderId is not None:
            obj["orderId"] = self.orderId.id
        if self.asn is not None:
            obj["asn"] = self.asn.id
        if self.deliveryAgent is not None:
            obj["deliveryAgent"] = self.deliveryAgent.asJson()

        return obj

class Invoices(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("-created_ts",)

        constraints = [
            models.UniqueConstraint(
                fields=['billId'],
                name="uniqueInternalBillIdInternal"
            )
        ]

    id              = models.AutoField(primary_key=True)
    status          = models.CharField(max_length=50)
    created_ts      = models.DateTimeField(auto_now_add=True)
    updated_ts      = models.DateTimeField(auto_now=True)
    vendorId        = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, null=False, blank=False
    )
    month           = models.BigIntegerField()
    year            = models.BigIntegerField()
    billId          = models.CharField(max_length=50)
    lineItems       = models.JSONField()
    billTotal       = models.JSONField()
    billTo          = models.JSONField()
    shipTo          = models.JSONField()

    def asJson(self):
        obj = {
            "id": self.id,
            "status": self.status,
            "createddate":self.created_ts.strftime("%d-%m-%Y"),
            "createdtime":self.created_ts.strftime("%H:%M"),
            "vendorId": self.vendorId.asJson(),
            "month": self.month,
            "year": self.year,
            "billId": self.billId,
            "lineItems": self.lineItems,
            "billTotal": self.billTotal,
            "billTo": self.billTo,
            "shipTo": self.shipTo
        }
        return obj

class Notifications(models.Model):

    id              = models.AutoField(primary_key=True)
    statusNew       = models.BooleanField(default=True)
    category        = models.JSONField()    # type, endpoint;; Example: ASN:endpoint, GRN:endpoint, ORDER:endpoint
    payload         = models.JSONField()    # title, description, otherDetails, userId (who created it)
    emailContent    = models.JSONField()    # subject, body
    created         = models.DateTimeField(auto_now_add=True)
    readAt          = models.DateTimeField(auto_now=True)
    vendorId        = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, null=True, blank=True)
    vendorAll       = models.BooleanField(default=False)
    warehouseId     = models.ForeignKey(
        WarehouseMaster, on_delete=models.CASCADE, null=True, blank=True)
    warehouseAll    = models.BooleanField(default=False)
    emailSent       = models.BooleanField(default=False)

    class Meta:
        app_label = "infra"
        ordering = ("-id",)

    def asJson(self):

        obj = {
            "id": self.id,
            "statusNew": self.statusNew,
            "payload": self.payload,
            "created": self.created.strftime("%m-%d-%Y %H:%M"),
            "readAt": self.readAt.strftime("%m-%d-%Y %H:%M")
        }

        return obj

class EmailDump(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

    id              = models.AutoField(primary_key=True)
    created_ts      = models.DateTimeField(auto_now_add=True)
    updated_ts      = models.DateTimeField(auto_now=True)
    vendorId        = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    folderName      = models.CharField(max_length=100)
    status          = models.CharField(max_length=50)   # NEW, READ, PARSED
    subject         = models.JSONField()                # Stored as {"subject": ""}
    emailBody       = models.JSONField()                # Stored as {"body": ""}
    emailNum        = models.CharField(max_length=10)   # Email Number from the mailbox
    bsContent       = models.JSONField()                # Beautiful Soup Parsed Content

    def asJson(self):
        obj = {
            "id": self.id,
            "vendorId": self.vendorId.asJson(),
            "status": self.status,
            "subject": self.subject,
            "emailBody": self.emailBody,
            "emailNum": self.emailNum,
            "created": self.created_ts.strftime("%m-%d-%Y %H:%M"),
        }
        return obj

class Transactions(models.Model):

    class Meta:
        app_label = "infra"
        ordering = ("id",)

        constraints = [
            models.UniqueConstraint(
                fields=['transactionId', 'invoiceIdInternal'],
                name="uniqueTransactionIdPaymentGateway"
            )
        ]

    id                      = models.AutoField(primary_key=True)
    transactionId           = models.CharField(max_length=100)
    invoiceIdInternal       = models.ForeignKey(Invoices, on_delete=models.CASCADE)
    invoiceIdExternal       = models.CharField(max_length=100)
    status                  = models.CharField(max_length=100)
    payload                 = models.JSONField()
    dump                    = models.JSONField()


    def asJson(self, includeInvoice=False):
        obj = {
            "id": self.id,
            "transactionId": self.transactionId,
            "status": self.status,
            "payload": self.payload,
            "dump": self.dump
        }
        if includeInvoice:
            obj["invoice"] = self.invoiceIdInternal.asJson()
        return obj


class SQLQueries(models.Model):

    class Meta:
        app_label="infra"
    id = models.AutoField(primary_key=True)
    payload = models.JSONField()
    active = models.BooleanField()

    def asJson(self):
        obj = {
            "id": self.id,
            "payload": self.payload,
            "active": self.active
        }
        return obj


class ResetPasswordEmailLink(models.Model):
    warehouse_user = models.OneToOneField(WarehouseUsers, on_delete=models.CASCADE, blank=True, null=True)
    vendor_user = models.OneToOneField(VendorUsers, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=False)
    expired_at = models.DateTimeField(auto_now_add=False)
    token = models.TextField()

    def __str__(self):
        return self.warehouse_user.name if self.warehouse_user else self.vendor_user.name
