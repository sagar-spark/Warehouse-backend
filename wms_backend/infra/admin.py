from django.contrib import admin

from .models import (Vendor, VendorUsers, WarehouseUsers, WarehouseMaster, Orders, OrderItems, Inventory,
                     VendorUserToken, EmailDump, VendorExternalIntegration, ResetPasswordEmailLink)

admin.site.register(WarehouseUsers)
admin.site.register(WarehouseMaster)
admin.site.register(VendorUsers)
admin.site.register(Vendor)
admin.site.register(Orders)
admin.site.register(OrderItems)
admin.site.register(Inventory)
admin.site.register(VendorUserToken)
admin.site.register(EmailDump)
admin.site.register(VendorExternalIntegration)
admin.site.register(ResetPasswordEmailLink)
