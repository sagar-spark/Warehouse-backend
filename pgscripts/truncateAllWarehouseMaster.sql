// Author: CP

TRUNCATE TABLE "public".infra_warehousemaster, "public".inbound_asn, "public".inbound_grn,
    "public".infra_vendor, "public".infra_warehouseusers, "public".infra_warehouseusers,
    "public".infra_warehousezones, "public".infra_warehouselocationlogs, "public".infra_warehousebinsandtrolley,
    "public".infra_shelvinglogs, "public".infra_orders, "public".infra_orderitems, "public".infra_notifications,
    "public".infra_inventory, "public".inbound_retailers, "public".inbound_sku, "public".infra_vendorusers,
    "public".infra_vendorusertoken, "public".infra_vendorexternalintegration, "public".infra_warehouselocations,
    "public".infra_warehouseusertoken, "public".infra_warehouseshelves RESTART IDENTITY;
