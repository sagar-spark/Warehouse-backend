# Author: CP

schemaGetASN = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}
    },
    "required": ["id"]
}

schemaGetAllASN = {
    "type": "object",
    "properties": {
        "page_seq": {"type": "string"},
        "page_size": {"type": "string"}
    }
}

schemaAddASN = {
    "type": "object",
    "properties": {
        "access_token": {"type": "string"},
        "payload": {"type": "object"}
    },
    "required": ["payload"]
}

schemaConfirmASN = {
    "type": "object",
    "properties": {
        "access_token": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "asnNumber": {"type": "string"},
                "confirm": {"enum": [ True, False]}
            }
        }
    },
}

schemaGetAllGRN = {
    "type": "object",
    "properties": {
        "page_seq": {"type": "string"},
        "page_size": {"type": "string"}
    }
}

schemaAddGRN = {
    "type": "object",
    "properties": {
        "access_token": {"type": "string"},
        "payload": {"type": "object"}
    },
    "required": ["payload"]
}

schemaGetGRN = {
    "type": "object",
    "properties": {
        "id": {"type": "string"}        
    },
    "required": ["id"]
}

