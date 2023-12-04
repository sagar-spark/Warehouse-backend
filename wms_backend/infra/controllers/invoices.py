# Author: CP

import json
from datetime import date
from uuid import uuid4

from wms_backend.utils.http_responses import respond_success, respond_error
from django.conf import settings
import traceback

from infra.models import Vendor, Invoices


def getSubscriptionModelForVendor(request):
    try:
        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        print(vendorId)
        if vendorId != "VENDOR_ALL":
            try:
                vendor = Vendor.objects.get(id=vendorId)
                return respond_success(vendor.billing)
            except Vendor.DoesNotExist as e:
                return respond_error("VendorId does not exist")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getAllBills(request):
    try:
        request_data = request.GET
        page_seq = int(request_data.get("page_seq", default=0))
        page_size = int(
            request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))
        vendorIdRequest = request_data.get("vendorId", default="")

        vendorId = request.META.get("auth").get("tokenObject").get("vendorId")
        if vendorIdRequest is not None and vendorIdRequest != "":
            vendorId = vendorIdRequest
        vendor = None
        if vendorId != "VENDOR_ALL":
            try:
                vendor = Vendor.objects.get(vendorId=vendorId)
            except Vendor.DoesNotExist as e:
                return respond_error("VendorId does not exist")
        filters = {}
        if vendor is not None:
            filters["vendorId"] = vendor

        invoices = Invoices.objects.filter(**filters)
        count = invoices.count()

        startIndex = (max(0, page_seq - 1)) * page_size
        endIndex = min(startIndex + page_size, count)
        if startIndex > count:
            return respond_error(
                {"totalCount": count, "payloads": None, "reason": "startIndex more than total count"}
            )
        objs = invoices[startIndex:endIndex]
        objs = [x.asJson() for x in objs]

        return respond_success({
            "totalCount": count,
            "pageNum": page_seq,
            "payloads": objs
        })
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def approveBill(request):
    try:
        requestData = request.GET
        billId = requestData.get("billId", default=None)
        status = requestData.get("status", default="")
        if status not in ["APPROVE", "CANCEL"]:
            return respond_error("Status not allowed")
        try:
            bill = Invoices.objects.get(billId=billId)
            bill.status = status
            bill.save()
            return respond_success("Done")
        except Invoices.DoesNotExist as e:
            return respond_error("BillId does not exist")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def generateAlaCarteBill(request):
    try:
        data = json.loads(request.body)
        vendorId = data["vendorId"]
        if vendorId is None:
            return respond_error("VendorId cannot be null")
        today = date.today()
        month = data["month"]
        year = data["year"]
        if (year > today.year) or (year == today.year and month > today.month):
            return respond_error("Cannot create bill for future. Let the aliens come to earth first")

        try:
            vendor = Vendor.objects.get(vendorId=vendorId)
            generateInvoice = False
            try:
                invoices = Invoices.objects.filter(vendorId=vendor, month=month, year=year)
                invoices = [invoice.asJson() for invoice in invoices]
                if len(invoices) > 0:
                    invoice = invoices[-1]
                else:
                    invoice = None
                if invoice is None:
                    generateInvoice = True
                elif invoice["status"] == "CANCEL":
                    generateInvoice = True
            except Invoices.DoesNotExist as e:
                print("Invoice does not exist for vendorId: {}, proceeding to generate one.")
                generateInvoice = True
            if generateInvoice == False:
                return respond_error("Invoice already generated for the given vendor, month and year")

            lineItems = data["lineItems"];
            total = 0
            for lineItem in lineItems:
                lineItem["totalLinePrice"] = lineItem["price"] * lineItem["quantity"]
                lineItem["totalTax"] = lineItem["totalLinePrice"] * lineItem["tax"]
                lineItem["totalPrice"] = lineItem["totalLinePrice"] + lineItem["totalTax"] - lineItem["discount"]
                total += lineItem["totalPrice"]

            invoice = Invoices(
                status="APPROVE",
                vendorId=vendor,
                month=month,
                year=year,
                billId=str(uuid4()),
                lineItems=lineItems,
                billTotal={"total": total},
                billTo=vendor.address[0],
                shipTo=vendor.address[0],
            )
            invoice.save()

            return respond_success("Ok")

        except Vendor.DoesNotExist as e:
            return respond_error("Vendor does not exist")

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def generateDraftBill(request):
    try:
        requestData = request.GET
        vendorId = requestData.get("vendorId", default=None)
        overrideDate = requestData.get("overrideDate", default="0")  # "1" or "0"
        overrideDate = True if overrideDate == "1" else False
        # if None - it will mostly come from Cron job and will run for all the vendors
        vendorIds = None
        if vendorId == None:
            vendors = Vendor.objects.all()
            vendorIds = [vendor.vendorId for vendor in vendors]
        else:
            vendorIds = [vendorId]

        today = date.today()
        month = int(requestData.get("month", default=0))
        # if month is 0 - it will run for the current month as per system date
        if month == 0:
            month = today.month

        year = int(requestData.get("year", default=0))
        # if year is 0 - it will run for the current year as per system date
        if year == 0:
            year = today.year

        if (year > today.year) or (year == today.year and month > today.month):
            return respond_error("Provided date is in future. Go do timetravel and come back to me.")

        # Generate Invoice for each vendors
        print(vendorIds)
        for vendor in vendorIds:
            # Step1: Find if the invoice is generated and approved -
            # if not generated - proceed to step 2
            # if generated and cancelled - proceed to step 2
            # else continue to the next vendor
            try:
                vendor = Vendor.objects.get(vendorId=vendor)
            except Vendor.DoesNotExist as e:
                print("Vendor Id: {} does not exist for Invoice generation".format(vendorId))

            generateInvoice = False
            try:
                invoices = Invoices.objects.filter(vendorId=vendor, month=month, year=year)
                invoices = [invoice.asJson() for invoice in invoices]
                if len(invoices) > 0:
                    invoice = invoices[-1]
                else:
                    invoice = None
                if invoice is None:
                    generateInvoice = True
                elif invoice["status"] == "CANCEL":
                    generateInvoice = True

                if not overrideDate and vendor.billing["start"] != today.day:
                    generateInvoice = False

            except Invoices.DoesNotExist as e:
                print("Invoice does not exist for vendorId: {}, proceeding to generate one.")
                generateInvoice = True

            if generateInvoice == False:
                continue
            # Considering that this is to generate the bill

            # Step 2: Find the model of billing: Subs / Alacarte -- currently procceed with only subscription
            # Step 3: Find the frequency of the billing - and see if the frequency matches the current month / year
            model = vendor.billing["model"]
            if model == "ALACARTE":
                continue

            frequency = vendor.billing["frequency"]
            if frequency != "MONTHLY":
                continue

            # Step 4: Take model from vendor table, take price from tenant json - add line items to the invoice and generate
            billPackage = vendor.billing["billPackage"]
            packageSettings = settings.TENANT_SETTINGS["appSettings"]["BILLING"]["SUBSCRIPTION"][billPackage]
            lineItem = {
                "item": billPackage,
                "price": packageSettings["price"],
                "discount": packageSettings["discount"],
                "tax": packageSettings["tax"],
                "quantity": 1
            }
            lineItem["totalLinePrice"] = lineItem["price"] * lineItem["quantity"]
            lineItem["totalTax"] = lineItem["totalLinePrice"] * lineItem["tax"]
            lineItem["totalPrice"] = lineItem["totalLinePrice"] + lineItem["totalTax"] - lineItem["discount"]
            items = [lineItem]
            total = 0
            for item in items:
                total += item["totalPrice"]

            invoice = Invoices(
                status="DRAFT",
                vendorId=vendor,
                month=month,
                year=year,
                billId=str(uuid4()),
                lineItems=items,
                billTotal={"total": total},
                billTo=vendor.address[0],
                shipTo=vendor.address[0],
            )
            invoice.save()

            # Step 5: Generate PDF and upload to S3
            pass
        return respond_success("Ok")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")
