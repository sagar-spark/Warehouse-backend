from django.urls import path

from inbound.views import get_stats, uploadSkus, getVendorSkuById, getAllVendorSKUs
from wms_backend.inbound.views import get_all_asn, get_asn, add_asn, confirm_grn
from wms_backend.inbound.views import get_all_grn, get_grn, add_grn
from wms_backend.inbound.views import vendorRetailerAdd, vendorRetailerToggleActive, vendorAllRetailers
from wms_backend.inbound.views import buildSKUsFromShopify

app_name = "inbound"

urlpatterns = [
    path("uploadSkus/", view=uploadSkus, name="uploadSkus"),
    path("buildSKUsFromShopify/", view=buildSKUsFromShopify, name="buildSKUsFromShopify"),
    path("getVendorSkuById/", view=getVendorSkuById, name="getSkuById"),
    path("getAllVendorSKUs/", view=getAllVendorSKUs, name="getAllVendorSKUs"),
    path("get-stats/", view=get_stats, name="get_stats"),
    path("get-asn/", view=get_asn, name="get_asn"),
    path("add-asn/", view=add_asn, name="add_asn"),
    path("confirm-grn/", view=confirm_grn, name="confirm_grn"),
    path("get-all-grn/", view=get_all_grn, name="get_all_grn"),
    path("get-all-asn/", view=get_all_asn, name="get_all_asn"),
    path("add-grn/", view=add_grn, name="add_grn"),
    path("get-grn/", view=get_grn, name="get_grn"),
    path("add-retailer/", view=vendorRetailerAdd, name="vendorRetailerAdd"),
    path("toggle-retailer/", view=vendorRetailerToggleActive, name=" vendorRetailerToggleActive"),
    path("get-all-retailers/", view=vendorAllRetailers, name="vendorAllRetailers")

]
