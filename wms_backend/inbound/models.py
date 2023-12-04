from django.db import models

from infra.models import Vendor
from infra.models import VendorUsers
from infra.models import WarehouseMaster
from infra.models import WarehouseUsers

from utils import barcode
from utils import awss3

class ASN(models.Model):

    id          = models.AutoField(primary_key=True)
    asnId       = models.CharField(max_length=100)

    vendorId    = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    vendorUser  = models.ForeignKey(VendorUsers, on_delete=models.CASCADE)  # user if of person

    warehouseId = models.ForeignKey(                            # FK: to which warehouse this has been shipped
        WarehouseMaster,
        on_delete=models.CASCADE)
    warehouseIdHops = models.JSONField()                        # For ASN due for Transfer - the order in which
                                                                # the ASN pack will move to reach warehouseId
    warehouseIdHopsLogs = models.JSONField()                    # logs of user and handling details on hoping

    grnUpdated  = models.BooleanField(default=False)
    grnConfirmed= models.BooleanField(default=False)

    payload           = models.JSONField()  # Data payload in JSON from schema

    stageStockIn      = models.CharField(max_length=20, null=True, blank=True) # StockIn, Transport, Shelving, Live

    created_ts        = models.DateTimeField(auto_now_add=True)  # when object was created
    updated_ts        = models.DateTimeField(auto_now=True)  # when object was last updated

    class Meta:
        app_label = "inbound"
        ordering = ("-id",)

    def get_payload(self):
        return self.payload

    def asJson(self):
        obj = {
            "id":          self.id,
            "asnId":       self.asnId,
            "createddate": self.created_ts.strftime("%d-%m-%Y"),
            "createdtime": self.created_ts.strftime("%H:%M"),
            "vendorId"   : self.vendorId.vendorId,
            "vendorUser" : self.vendorUser.email,
            "grnUpdated" : self.grnUpdated,
            "grnConfirmed":self.grnConfirmed,
            "payload"    : self.payload,
            "stageStockIn": self.stageStockIn
        }

        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(ASN, self).save(*args, **kwargs)
        if self.asnId is None or self.asnId == '':
            asnId = "{}{}".format("ASN-",self.id)
            self.asnId = asnId
        if "barcode" not in self.payload:
            response = barcode.handleBarCode(self.asnId, self.__class__.__name__)
            if response["uploaded"]:
                self.payload["barcode"] = response["path"]
        return super(ASN, self).save(*args, **kwargs)


class GRN(models.Model):
    # override auto-id field
    # primary_key = True if you do not want to use default field "id" given by django to your model
    id = models.AutoField(primary_key=True)
    grnId = models.CharField(max_length=100)

    asnId = models.ForeignKey(ASN, on_delete=models.CASCADE)
    vendorId = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    warehouseId = models.ForeignKey(                            # FK: to which warehouse this has been shipped
        WarehouseMaster,
        on_delete=models.CASCADE)

    warehouseUser = models.ForeignKey(
        WarehouseUsers,
        on_delete=models.CASCADE)
    created_ts = models.DateTimeField(auto_now_add=True)  # when object was created
    updated_ts = models.DateTimeField(auto_now=True)  # when object was last updated
    payload = models.JSONField()  # Data payload in JSON from schema
    stageStockIn      = models.CharField(max_length=20, null=True, blank=True) # ToStock, StockIn, Transport, Shelving, Live
    confirmPayload = models.JSONField(null=True, blank=True)

    # https://www.codegrepper.com/code-examples/python/RuntimeError%3A+Model+class+doesn%27t+declare+an+explicit+app_label+and+isn%27t+in+an+application+in+INSTALLED_APPS.
    class Meta:
        app_label = "inbound"

    def get_payload(self):
        return self.payload

    def asJson(self):
        obj = {
            "id"            : self.id,
            "grnId"         : self.grnId,
            "asnId"         : self.asnId.asnId,
            "vendorId"      : self.vendorId.vendorId,
            "warehouseUser" : self.warehouseUser.email,
            "createddate"   : self.created_ts.strftime("%d-%m-%Y"),
            "createdtime"   : self.created_ts.strftime("%H:%M"),
            "payload"       : self.payload,
            "confirmPayload": self.confirmPayload,
            "stageStockIn"  : self.stageStockIn
        }

        return obj

    def save(self, *args, **kwargs):
        if self.id is None:
            super(GRN, self).save(*args, **kwargs)
        if self.grnId is None or self.grnId == '':
            self.grnId = "{}{}".format("GRN-", self.id)
        if "barcode" not in self.payload:
            response = barcode.handleBarCode(self.grnId, self.__class__.__name__)
            if response["uploaded"]:
                self.payload["barcode"] = response["path"]
        return super(GRN, self).save(*args, **kwargs)

class SKU(models.Model):
    
    id                  = models.AutoField(primary_key=True)
    productId           = models.CharField(max_length=100, null=True, blank=True)
    productName         = models.CharField(max_length=100)
    productCategory     = models.CharField(max_length=100, null=True, blank=True)
    variantId           = models.CharField(max_length=100, null=True, blank=True)
    variantName         = models.CharField(max_length=100, null=True, blank=True)
    skuNumber           = models.CharField(max_length=100)
    description         = models.CharField(max_length=2000, null=True, blank=True)
    packaging           = models.CharField(max_length=100, null=True, blank=True)
    composition         = models.CharField(max_length=200, null=True, blank=True)
    colour              = models.CharField(max_length=25, null=True, blank=True)
    shopify             = models.JSONField(null=True, blank=True)

    vendorId            = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    payload             = models.JSONField()
    source              = models.CharField(max_length=20)

    def save(self, *args, **kwargs):
        if "barcode" not in self.payload:
            barCodeHandle = "{}".format(self.skuNumber)
            response = barcode.handleBarCode(barCodeHandle, self.__class__.__name__)
            if response["uploaded"]:
                self.payload["barcode"] = response["path"]
        return super(SKU, self).save(*args, **kwargs)

    def asJson(self):
        obj = {
            "id":               self.id,
            "productId":        self.productId,
            "productName":      self.productName,
            "productCategory":  self.productCategory,
            "variantId":        self.variantId,
            "variantName":      self.variantName,
            "skuNumber":        self.skuNumber,
            "description":      self.description,
            "packaging":        self.packaging,
            "composition":      self.composition,
            "colour":           self.colour,
            "source":           self.source,
        }
        obj.update(self.payload)

        return obj

    class Meta:
        app_label="inbound"
        ordering = ("productName", "skuNumber")
        #unique_together = ('skuNumber', 'vendorId')
        constraints = [
            models.UniqueConstraint(
                fields=['skuNumber', 'vendorId', 'productId', 'variantId'],
                name='vendorSku'
            )
        ]

class Retailers(models.Model):

    id          = models.AutoField(primary_key=True)
    payload     = models.JSONField()
    active      = models.BooleanField(default=True)
    created_ts  = models.DateTimeField(auto_now_add=True)
    vendorId    = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    def asJson(self):
        obj = {
            "id": self.id,
            "payload": self.payload
        }
        return obj

    class Meta:
        app_label="inbound"

