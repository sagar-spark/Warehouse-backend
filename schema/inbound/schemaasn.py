asn = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "schemaVersion": {"type": "string"}
            },
            "required": ["schemaVersion"]
        },
        "shipmentDetails": {
            "type": "object",
            "properties": {
                "shipmentDate": {"type": "string", "format": "date-time"},
                "shipmentSalesOrderId": {"type": "string"},
                "shipmentOrderDate": {"type": "string", "format": "date-time"},
                "shipmentOrderEmail": {"type": "string", "format": "email"},
                "shipmentPO": {"type": "string"},
                "shipmentCarrier": {"type": "string"},
                "shipmentTrackingNum": {"type": "string"}
            },
            "required": [
                "shipmentDate", "shipmentSalesOrderId", "shipmentOrderDate", "shipmentOrderEmail",
                "shipmentPO", "shipmentCarrier", "shipmentTrackingNum"
            ]
        },
        "shipmentFromDetails": {
            "type": "object",
            "properties": {
                "vendorId": {"type": "string"},
                "vendorUserId": {"type": "string"},
                "vendorWarehouseId": {"type": "string"},
                "vendorCompanyName": {"type": "string"},
                "vendorAddress": {"type": "string"},
                "vendorCity": {"type": "string"},
                "vendorState": {"type": "string"},
                "vendorZip": {"type": "string"},
                "vendorPhone": {"type": "string"},
                "vendorEmail": {"type": "string", "format": "email"}
            },
            "required": [
                "vendorId", "vendorUserId", "vendorWarehouseId", "vendorCompanyName", "vendorAddress",
                "vendorCity", "vendorState", "vendorZip", "vendorPhone", "vendorEmail"
            ]
        },
        "destinationDetails": {
            "type": "object",
            "properties": {
                "destinationName": {"type": "string"},
                "destinationCompanyName": {"type": "string"},
                "destinationAddress": {"type": "string"},
                "destinationCity": {"type": "string"},
                "destinationState": {"type": "string"},
                "destinationZip": {"type": "string"},
                "destinationPhone": {"type": "string"},
                "destinationEmail": {"type": "string", "format": "email"}
            },
            "required": [
                "destinationName", "destinationCompanyName", "destinationAddress",
                "destinationCity", "destinationState", "destinationZip", "destinationPhone",
                "destinationEmail"
            ]
        },
        "billingDetails": {
            "type": "object",
            "properties": {
                "billingName": {"type": "string"},
                "billingCompanyName": {"type": "string"},
                "billingAddress": {"type": "string"},
                "billingCity": {"type": "string"},
                "billingState": {"type": "string"},
                "billingZip": {"type": "string"},
                "billingPhone": {"type": "string"},
                "billingEmail": {"type": "string", "format": "email"}
            },
            "required": [
                "billingName", "billingCompanyName", "billingAddress",
                "billingCity", "billingState", "billingZip",
                "billingPhone", "billingEmail"
            ]
        },
        "palletDetails": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "palletNumber": {"type": "string"},
                    "palletContents": {"type": "string"},
                    "palletWeight": {"type": "number", "minimum": 0},
                    "palletLength": {"type": "number", "minimum": 0},
                    "palletWidth": {"type": "number", "minimum": 0},
                    "palletHeight": {"type": "number", "minimum": 0}
                },
                "required": [
                    "palletNumber", "palletContents", "palletWeight",
                    "palletLength", "palletWidth", "palletHeight"
                ]
            }
        },
        "packageDetails": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "packageNumber": {"type": "string"},
                    "packageDescription": {"type": "string"},
                    "packageSKU": {"type": "string"},
                    "packageQuantity": {"type": "int", "minimum": 0},
                    "packageWeight": {"type": "number", "minimum": 0},
                    "packageDimensions": {"type": "string"}
                },
                "required": [
                    "packageNumber", "packageDescription", "packageSKU",
                    "packageQuantity", "packageWeight", "packageDimensions"
                ]
            }
        },
        "shippingInstructions": {"type": "string"},
        "receiverDetails": {
            "type": "object",
            "properties": {
                "employeeId": {"type": "string"}
            },
            "required": [
                "employeeId"
            ]
        }
    },
    "required": [
        "meta", "shipmentDetails", "shipmentFromDetails", "destinationDetails",
        "billingDetails", "palletDetails", "packageDetails", "shippingInstructions",
        "receiverDetails"
    ]
}

