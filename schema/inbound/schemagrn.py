grn = {
    "type": "object",
    "properties": {
        "meta": {
            "type": "object",
            "properties": {
                "schemaVersion": {"type": "string"}
            },
            "required": ["schemaVersion"]
        },
        "vendorId": {"type": "string"},
        "asnNumber": {"type": "int", "minimum": 0},
        "grnAccept": {
            "type": "object",
            "properties": {
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
                            "packageDimensions": {"type": "string"},
                            "actionQC": {
                                "type": "string",
                                "enum": [
                                    "Accept complete package",
                                    "Reject complete package",
                                    "Partial accept"
                                ]
                            },
                            "remarksQC": {"type": "string"},
                            "acceptQuantity": {"type": "int", "minimum": 0},
                        },
                        "required": [
                            "packageNumber", "packageDescription", "packageSKU",
                            "packageQuantity", "packageWeight", "packageDimensions",
                            "actionQC", "remarksQC", "acceptQuantity"
                        ]
                    }
                }
            },
            "required": [
                "packageDetails"
            ]
        },
        "grnReturn": {
            "type": "object",
            "properties": {
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
                            "packageDimensions": {"type": "string"},
                            "actionQC": {
                                "type": "string",
                                "enum": [
                                    "Items damaged",
                                    "Incorrect items"
                                ]
                            },
                            "remarksQC": {"type": "string"},
                            "rejectQuantity": {"type": "int", "minimum": 0},
                        },
                        "required": [
                            "packageNumber", "packageDescription", "packageSKU",
                            "packageQuantity", "packageWeight", "packageDimensions",
                            "actionQC", "remarksQC", "rejectQuantity"
                        ]
                    }
                }
            },
            "required": [
                "packageDetails"
            ]
        }
    },
    "required": [
        "meta", "vendorId", "asnNumber", "grn-accept", "grn-return"
    ]
}

