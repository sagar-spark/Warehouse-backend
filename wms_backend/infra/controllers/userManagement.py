# Author: CP

import json, traceback

from wms_backend.utils.http_responses import respond_success, respond_error

from infra.models import VendorUserToken, Vendor, VendorUsers
from infra.models import WarehouseUsers, WarehouseUserToken
from infra.models import WarehouseMaster

db = {
    "vendor": VendorUsers,
    "warehouse": WarehouseUsers
}

dbTokens = {
    "vendor": VendorUserToken,
    "warehouse": WarehouseUserToken
}

tokenSuffix = {
    "vendor": "-v",
    "warehouse": "-w"
}

def getAllUsers(request, type):
    try:
        if type == "warehouse":
            request_data = request.GET
            role = request_data.get("role", default="ALL")

            filters = {}
            if role != "ALL":
                filters["role"] = role
            allObjs = WarehouseUsers.objects.filter(**filters).exclude(role="Admin")
        elif type == "vendor":
            filters = {}
            user = request.META.get("auth")
            if user["authType"] == "vendorUser":
                vendorId = user["tokenObject"]["vendorId"]
                filters["vendorId_id"] = vendorId
            elif user["authType"] == "warehouseUser":
                requestData = json.loads(request.body) if request.body is not None else {}
                filters = requestData

            allObjs = VendorUsers.objects.filter(**filters)
        allObjs = [x.asJson() for x in allObjs]
        return respond_success(allObjs)
    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

def setNewPassword(request):
    reqData = json.loads(request.body)

    # warehouse, vendor
    type = reqData["type"]
    email = reqData["email"]
    newPassword = reqData["newPassword"]

    existUser = None
    try:
        if type == "warehouse":
            existUser = WarehouseUsers.objects.get(email=email)
        else:
            existUser = VendorUsers.objects.get(email=email)
    except WarehouseUsers.DoesNotExist as e:
        existUser = None
    except VendorUsers.DoesNotExist as e:
        existUser = None

    if existUser is not None:
        existUser.passw = newPassword
        existUser.save()
    return respond_success("Ok")

def validateLoginToken(request):

    try:
        request_data = json.loads(request.body)

        accessToken = request_data["accessToken"]

        v = accessToken[-1] == "v"
        w = accessToken[-1] == "w"

        if v:
            type = "vendor"
        elif w:
            type = "warehouse"
        else:
            return respond_error("Token does not exist", status=404)

        try:
            token = dbTokens[type].objects.get(id=accessToken[:-2])
            return respond_success(True)
        except dbTokens[type].DoesNotExist as e:
            print (traceback.format_exc())
            return respond_error("Token does not exist", status=404)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


def userLogin(request, type, admin=False):

    try:
        request_data = json.loads(request.body)

        email = request_data["email"]
        passw = request_data["passw"]

        if email is None or passw is None:
            return respond_error("Fields needed", status=404)

        user = None
        try:
            user = db[type].objects.get(email=email)
            if admin and type == "warehouse" and not user.role == "Admin":
                return respond_error("Admin User not found", status=404)
        except db[type].DoesNotExist as e:
            user = None
        if user is None:
            return respond_error("User not found", status=404)

        if user.passw == passw:
            # TODO: Check for existing token and expire them.

            token = dbTokens[type](userId=user)

            if type == "vendor":
                token.vendorId=user.vendorId

            token.save()

            return respond_success(f"{token.id}{tokenSuffix[type]}")

        else:
            return respond_error("Incorrect password", status=404)

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)


def userSignup(request, type):
    try:
        request_data = json.loads(request.body)

        email    = request_data["email"]
        name     = request_data["name"]
        passw    = request_data["passw"]
        phone    = request_data["phone"]

        # TODO Data Validation through Json schema validator

        try:
            user = db[type].objects.get(email=email)
            return respond_error("User already created with this email ID", status=404)
        except db[type].DoesNotExist as e:
            print ("Email does not exist yet with: ", email)


        vendor = None
        if type == "vendor":
            vendorId = request_data["vendorId"]
            try:
                vendor = Vendor.objects.get(vendorId=vendorId)
            except Vendor.DoesNotExist as e:
                print ("Matching query to Vendor Model does not exist: ", vendorId)
                return respond_error("Vendor Id does not exist", status=404)

        if type == "vendor" and vendor is None:
            return respond_error("Vendor Id does not exist", status=404)

        user = db[type](
            email=email,
            name=name,
            passw=passw,
            phone=phone
        )

        if type == "vendor":
            user.vendorId = vendor
        elif type == "warehouse":
            role=request_data["role"]
            user.role = role
            if role not in ["Admin", "Manager", "User", "Delivery"]:
                return respond_error("Invalid user role", status=404)

            if role != "Admin":

                warehouseId = request_data['warehouseId']

                if warehouseId is None or warehouseId == "":
                    return respond_error("Warehouse you are trying to assign does not exist", status=404)

                try:
                    warehouseMasterObject = WarehouseMaster.objects.get(id=warehouseId)
                except WarehouseMaster.DoesNotExist as e:
                    return respond_error("Warehouse you are trying to assign does not exist", status=404)

                user.warehouseId = warehouseMasterObject

        userId = user.save()

        return respond_success("User created successfully")

    except Exception as e:
        print (traceback.format_exc())
        return respond_error(e.args, status=404)

