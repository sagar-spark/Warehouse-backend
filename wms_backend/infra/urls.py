from django.urls import path

from wms_backend.infra.views import forgotPassword, live_status, getVendorsInventoryItems, resetPassword
from wms_backend.infra.views import delete_expired_tokens
from wms_backend.infra.views import vendorLogin, vendorSignup, vendorUserSignup, validateAccessToken, getCurrentUserDetails, getCurrentVendorDetails, getAllVendors, vendorAddressAdd, getWarehouseDetails, vendorAddressDelete, getDynamicMenuVendor
from wms_backend.infra.views import warehouseUserSignup, warehouseUserAddition, warehouseLogin, adminLogin
from wms_backend.infra.views import setNewPassword
from wms_backend.infra.views import addWarehouse, getAllWarehouseObjects
from wms_backend.infra.views import addWarehouseZones, addWarehouseLocationsAndShelves, addWarehouseBinsAndTrolleys
from wms_backend.infra.views import vendorSignup, addShopifyForVendors, getAllWarehouseUsers, getAllVendorUsers

from wms_backend.infra.views import getShelvingShelves, addShelvingLog, getShelvingLog, getInventoryItems
from wms_backend.infra.views import orderNotificationShopify
from wms_backend.infra.views import getVendorSkuFromInventory
from wms_backend.infra.views import getOrderItems
from wms_backend.infra.views import createCustomOrder
from wms_backend.infra.views import getOrderItemsByOrderId, updateOrderItemByRowId, cancelOrderItems
from wms_backend.infra.views import readNotification, getAllNotifications
from wms_backend.infra.views import createShipping, getShippingByAWB, cronUpdateAwbs, markShippingAsDelivered, assignDeliveryAgentToShipping, getAllAWB

from wms_backend.infra.views import generateAlaCarteBill, generateDraftBill, approveBill, getAllBills, getSubscriptionModelForVendor

from wms_backend.infra.views import registerEmailBoxForAVendor, syncAllEmailsFromServer, getVendorOrderEmails, markVendorOrderEmailRead, getSpecificEmailFromId, parseEmailBodyContent

from wms_backend.infra.views import initiatePayment, executePayment, getTransactionsForABill, refreshTransactionsForBill, refreshTransactionForAllPendingBills

from wms_backend.infra.views import getAllQueries, addQuery, getAdminStats, setStatusQuery

from wms_backend.infra.views import getLogsStocksInMoveQ, putStocksInMoveQ, removeStocksInMoveQ

app_name = "infra"

urlpatterns = [
    path("live-status/", view=live_status, name="live_status"),
    path("delete-tokens/", view=delete_expired_tokens, name="delete_expired_tokens"),

    path("register-vendor/", view=vendorSignup, name="vendorSignup"),

    path("vendor-login/", view=vendorLogin, name="vendorLogin"),
    path("validate-access-token/", view=validateAccessToken, name="validateAccessToken"),

    path("vendor-signup/", view=vendorSignup, name="vendorSignup"),
    path("vendor-address-add/", view=vendorAddressAdd, name="vendorAddressAdd"),
    path("vendor-address-del/", view=vendorAddressDelete, name="vendorAddressDelete"),
    path("vendor-user-signup/", view=vendorUserSignup, name="vendorUserSignup"),
    path("addShopifyForVendors/", view=addShopifyForVendors, name="addShopifyForVendors"),

    path("warehouse-user-signup/", view=warehouseUserSignup, name="warehouseUserSignup"),
    path("setNewPassword/", view=setNewPassword, name="setNewPassword"),
    path("forgot-password-email/", view=forgotPassword, name="forgot_password_email"),
    path("reset-password/", view=resetPassword, name="forgot_password_email"),
    path("getAllVendorUsers/", view=getAllVendorUsers, name="getAllVendorUsers"),
    path("getAllWarehouseUsers/", view=getAllWarehouseUsers, name="getAllWarehouseUsers"),
    path("warehouse-user-addition/", view=warehouseUserAddition, name="warehouseUserAddition"),
    path("warehouse-add-managerUsers/", view=warehouseUserSignup, name="warehouseUserSignup"),
    path("warehouse-login/", view=warehouseLogin, name="warehouseLogin"),
    path("admin-login/", view=adminLogin, name="adminLogin"),

    path("get-vendor-user-details/", view=getCurrentUserDetails, name="getCurrentUserDetails"),
    path("get-vendor-details/", view=getCurrentVendorDetails, name="getCurrentVendorDetails"),

    path("get-warehouse-details/", view=getWarehouseDetails, name="getWarehouseDetails"),
    path("getAllVendors/", view=getAllVendors, name="getAllVendors"),
    path("get-all-warehouse-objects/", view=getAllWarehouseObjects, name="getAllWarehouseObjects"),

    path("add-warehouse-master/", view=addWarehouse, name="addWarehouse"),
    path("add-warehouse-zones/", view=addWarehouseZones, name="addWarehouseZones"),
    path("add-warehouse-locations-shelves/", view=addWarehouseLocationsAndShelves, name="addWarehouseLocationsAndShelves"),
    path("add-warehouse-bins-trolleys/", view=addWarehouseBinsAndTrolleys, name="addWarehouseBinsAndTrolleys"),

    path("get-dynamic-url-vendor/", view=getDynamicMenuVendor, name="getDynamicMenuVendor"),
    path("getShelvingShelves/", view=getShelvingShelves, name="getShelvingShelves"),
    path("addShelvingLog/", view=addShelvingLog, name="addShelvingLog"),
    path("getShelvingLog/", view=getShelvingLog, name="getShelvingLog"),
    path("getInventoryItems/", view=getInventoryItems, name="getInventoryItems"),
    path("getVendorInventoryItems/", view=getVendorsInventoryItems, name="getVendorsInventoryItems"),

    path("orderNotificationShopify/<str:vendorId>/", view=orderNotificationShopify, name="orderNotificationShopify/"),
    path("getVendorSkuFromInventory/", view=getVendorSkuFromInventory, name="getVendorSkuFromInventory"),
    path("getOrderItems/", view=getOrderItems, name="getOrderItems"),
    path("createCustomOrder/", view=createCustomOrder, name="createCustomOrder"),

    path("getOrderItemsByOrderId/", view=getOrderItemsByOrderId, name="getOrderItemsByOrderId"),
    path("updateOrderItemByRowId/", view=updateOrderItemByRowId, name="updateOrderItemByRowId"),
    path("cancelOrderItems/", view=cancelOrderItems, name="cancelOrderItems"),
    path("createShipping/", view=createShipping, name="createShipping"),
    path("getShippingByAWB/", view=getShippingByAWB, name="getShippingByAWB"),
    path("cronUpdateAwbs/", view=cronUpdateAwbs, name="cronUpdateAwbs"),
    path("assignDeliveryAgentToShipping/", view=assignDeliveryAgentToShipping, name="assignDeliveryAgentToShipping"),
    path("getAllAWB/", view=getAllAWB, name="getAllAWB"),

    path("readNotification/", view=readNotification, name="readNotification"),
    path("getAllNotifications/", view=getAllNotifications, name="getAllNotifications"),

    path("generateDraftBill/", view=generateDraftBill, name="generateDraftBill"),
    path("generateAlaCarteBill/", view=generateAlaCarteBill, name="generateAlaCarteBill"),
    path("approveBill/", view=approveBill, name="approveBill"),
    path("getAllBills/", view=getAllBills, name="getAllBills"),
    path("getSubscriptionModelForVendor/", view=getSubscriptionModelForVendor, name="getSubscriptionModelForVendor"),

    path("registerEmailBoxForAVendor/", view=registerEmailBoxForAVendor, name="registerEmailBoxForAVendor"),
    path("syncAllEmailsFromServer/", view=syncAllEmailsFromServer, name="syncAllEmailsFromServer"),
    path("getVendorOrderEmails/", view=getVendorOrderEmails, name="getVendorOrderEmails"),
    path("markVendorOrderEmailRead/", view=markVendorOrderEmailRead, name="markVendorOrderEmailRead"),
    path("getSpecificEmailFromId/", view=getSpecificEmailFromId, name="getSpecificEmailFromId"),
    path("parseEmailBodyContent/", view=parseEmailBodyContent, name="parseEmailBodyContent"),

    path("initiatePayment/", view=initiatePayment, name="initiatePayment"),
    path("executePayment/", view=executePayment, name="executePayment"),
    path("getTransactionsForABill/", view=getTransactionsForABill, name="getTransactionsForABill"),
    path("refreshTransactionsForBill/", view=refreshTransactionsForBill, name="refreshTransactionsForBill"),
    path("refreshTransactionForAllPendingBills/", view=refreshTransactionForAllPendingBills, name="refreshTransactionForAllPendingBills"),

    path("getAllQueries/", view=getAllQueries, name="getAllQueries"),
    path("addQuery/", view=addQuery, name="addQuery"),
    path("getAdminStats/", view=getAdminStats, name="getAdminStats"),
    path("setStatusQuery/", view=setStatusQuery, name="setStatusQuery"),

    path("getLogsStocksInMoveQ/", view=getLogsStocksInMoveQ, name="getLogsStocksInMoveQ"),
    path("putStocksInMoveQ/", view=putStocksInMoveQ, name="putStocksInMoveQ"),
    path("removeStocksInMoveQ/", view=removeStocksInMoveQ, name="removeStocksInMoveQ"),

]
