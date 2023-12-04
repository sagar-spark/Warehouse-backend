# Author: CP

import json, requests, traceback

from infra.models import VendorExternalIntegration, Inventory

def updateExternalIntegrations(inventory, adjustment):

    if inventory.skuReference.source == "MANUAL":
        return

    try:
        vendorExternalValidation = VendorExternalIntegration.objects.get(vendorId=inventory.skuReference.vendorId)
        if vendorExternalValidation.shopify["success"] == False :
            print ("Skipping Inventory with ID: {} for Shopify as shopify Integration is not done for its vendor".format(inventory.id))
        else:
            url = "{}/admin/api/2022-10/inventory_levels/adjust.json".format(
                vendorExternalValidation.shopify["shopUrl"]
            )
            payload = {
                "location_id": inventory.skuReference.shopify["locationId"],
                "inventory_item_id": inventory.skuReference.shopify["variantDump"]["inventory_item_id"],
                "available_adjustment": adjustment
            }
            headers = {
                "X-Shopify-Access-Token": vendorExternalValidation.shopify["accessToken"],
                "Content-Type": "application/json"
            }

            response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
            print ("Inventory with ID: {} updated for Shopify with response: {}, Status: {}, URL: {}".format(inventory.id, response.text, response.status_code, url))
            return response.status_code
    except VendorExternalIntegration.DoesNotExist as e:
        pass


