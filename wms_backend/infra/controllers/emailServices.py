# Author: CP

import json
from datetime import datetime, timedelta
from uuid import uuid4

from django.utils import timezone
from wms_backend.utils.send_email import send_email

from wms_backend.utils.http_responses import get_frontend_domain, respond_success, respond_error
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
import traceback

import imaplib, email, msal

from infra.models import Vendor, VendorExternalIntegration, EmailDump, WarehouseUsers, VendorUsers, ResetPasswordEmailLink
from utils import notification


def registerEmailBoxForAVendor(request):
    try:
        data = json.loads(request.body)
        vendorId = data["vendorId"]
        mailbox = data["mailbox"]
        username = "orders@connectco.me"
        if vendorId is None or mailbox is None or username is None:
            return respond_error("VendorId or Mailbox cannot be null")
        try:
            vendor = Vendor.objects.get(vendorId=vendorId)
        except Vendor.DoesNotExist as e:
            return respond_error("VendorId does not exist")

        vendorIntegration = None
        try:
            vendorIntegration = VendorExternalIntegration.objects.get(vendorId=vendor)
        except VendorExternalIntegration.DoesNotExist as e:
            pass
        email = {
            "mailbox": mailbox,
            "username": username,
            "created": str(datetime.now())
        }
        if vendorIntegration is None:
            vendorIntegration = VendorExternalIntegration(
                vendorId=vendor,
                email=email
            )
        else:
            vendorIntegration.email = email

        vendorIntegration.save()
        return respond_success(vendorIntegration.asJson())
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def extract_body(payload):
    """
    returns the email body from the payload
    """
    if isinstance(payload, str):
        # payload = payload.decode('utf-8', 'ignore')
        return payload
    else:
        payload = '\n'.join([extract_body(part.get_payload()) for part in payload])
        # payload = payload.decode('utf-8', 'ignore')
        return payload


def create_connection(userName):
    app = msal.ConfidentialClientApplication(
        'fe2f872f-f06c-43d2-bea2-44a19be3f950',
        authority='https://login.microsoftonline.com/a1a293cb-6c0b-478a-ae1a-1ecaf49adc05',
        client_credential='4zF8Q~j7PoydZQei~ZKS_e1d54T-QAy63nTGhdeQ'
    )
    result = app.acquire_token_for_client(scopes=['https://outlook.office365.com/.default'])

    def generate_auth_string(user, token):
        return 'user=%s\1auth=Bearer %s\1\1' % (user, token)

    conn = imaplib.IMAP4_SSL("outlook.office365.com", 993)
    try:
        conn.authenticate('XOAUTH2', lambda x: generate_auth_string(userName, result['access_token']))
    except Exception as e:
        print("Could not login", e)
    return conn


def select_mailbox(conn, mailbox):
    conn.select(mailbox)


def get_emails(conn, search_param):
    typ, data = conn.search(None, search_param)
    emails = {}
    try:
        for num in data[0].split():
            emailNumber = int(num.decode())
            print(emailNumber)
            try:
                _, msg_data = conn.fetch(num, '(RFC822)')
                item = msg_data[0][0].decode('utf-8')
                mUid = item.split(" {")[1].split('}')[0]
                mail = {
                    "mUid": mUid,
                    "emailNumber": emailNumber
                }
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_string(response_part[1].decode("utf-8"))
                        mail["subject"] = msg['subject']
                        payload = msg.get_payload()
                        mail["emailBody"] = extract_body(payload)
                emails[mUid] = mail
            except Exception as e:
                print("Couldnt Parse message:", num, e)
                pass
        print(emails.keys())
        return emails
    except Exception as e:
        print("EXCEPTION OCCURED:", e)


def syncEmailsWithLocalDb(emails, vendor, folder):
    try:
        filters = {
            "folderName": folder
        }
        emailDumps = EmailDump.objects.filter(**filters)
        emailDumps = [x.asJson() for x in emailDumps]
        emailNumbers = [x["emailNum"] for x in emailDumps]
        totalEmailRead = len(emailDumps)

        print("Existing emails count in local DB: {}".format(totalEmailRead))
        print("Existing emails emailNumbers: {}".format(emailNumbers))

        receivedIndexFromServer = emails.keys()

        emailsIndexToWrite = [x for x in receivedIndexFromServer if x not in emailNumbers]
        print("Index To write to DB: ", emailsIndexToWrite, len(emailsIndexToWrite))
        for idx in emailsIndexToWrite:
            email = EmailDump(
                vendorId=vendor,
                folderName=folder,
                status="NEW",
                subject={
                    "subject": emails[idx]["subject"]
                },
                emailBody={
                    "body": emails[idx]["emailBody"],
                    "emailNum": emails[idx]["emailNumber"]
                },
                emailNum=idx,
                bsContent={}

            )
            email.save()
            """
            notification.addNotification(
                {
                    "category": {"type": "EMAIL", "endpoint": ""},
                    "payload": {
                        "title": "New order email found.",
                        "description": "{}".format(email.subject["subject"]),
                        "otherDetails": "",

                    },
                    "emailContent": {},
                    "vendorId": None,
                    "warehouseId": None,
                    "warehouseAll": True
                },
                False
            )
            """

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def syncAllEmailsFromServer(request):
    try:
        vendorIntegrations = VendorExternalIntegration.objects.exclude(email__isnull=True)
        email = ""
        for vi in vendorIntegrations:
            mailbox = vi.email["mailbox"]
            email = vi.email["username"]

            conn = create_connection(email)
            select_mailbox(conn, mailbox)
            emails = get_emails(conn, "ALL")
            print("Read {} emails from Folder: {}".format(len(emails.keys()), mailbox))
            syncEmailsWithLocalDb(emails, vi.vendorId, mailbox)
        conn.close()
        return respond_success("Ok")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getVendorOrderEmails(request):
    try:

        request_data = request.GET
        page_seq = int(request_data.get("page_seq", default=0))
        page_size = int(
            request_data.get("page_size", default=settings.TENANT_SETTINGS["appSettings"]["PAGINATION"]["PAGE_SIZE"]))

        status = request_data.get("status", "NEW")
        filters = {
            "status": status
        }
        emailDumps = EmailDump.objects.filter(**filters)
        count = emailDumps.count()
        startIndex = (max(0, page_seq - 1)) * page_size
        endIndex = min(startIndex + page_size, count)
        if startIndex > count:
            return respond_error(
                {"totalCount": count, "payloads": None, "reason": "startIndex more than total count"}
            )
        objs = emailDumps[startIndex:endIndex]
        objs = [x.asJson() for x in objs]

        return respond_success({
            "totalCount": count,
            "pageNum": page_seq,
            "payloads": objs
        })

    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def markVendorOrderEmailRead(request):
    try:

        request_data = request.GET
        emailId = int(request_data.get("emailId", default=0))
        status = request_data.get("status", "READ")
        if status not in ["NEW", "READ", "PARSED"]:
            return respond_error("Given Status not allowed")
        try:
            email = EmailDump.objects.get(id=emailId)
            email.status = status
            email.save()
            return respond_success("Ok")
        except EmailDump.DoesNotExist as e:
            return respond_error("Email Id does not exist")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def getSpecificEmailFromId(request):
    try:
        request_data = request.GET
        emailId = int(request_data.get("emailId", default=0))
        try:
            email = EmailDump.objects.get(id=emailId)
            return respond_success(email.asJson())
        except EmailDump.DoesNotExist as e:
            return respond_error("Email Id does not exist")
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def parseEmailBodyContent(request):
    try:
        pass
    except Exception as e:
        print(traceback.format_exc())
        return respond_error(f"Error: {e.args}")


def resetPasswordEmailLink(request):
    try:
        body = request.body
        request_data = json.loads(body)
        user = None
        portal = None
        user_email = request_data.get("email")
        portal = request_data.get("portal")
        user = WarehouseUsers.objects.get(email=user_email)

        if portal == 'warehouse' or portal == 'admin':
            pass
        elif portal == 'vendor':
            user = VendorUsers.objects.get(email=user_email)
        if user:
            token = str(uuid4())
            # Set expiration time
            reset_link_created_at = timezone.now()
            setExpiryTimeForEmail(reset_link_created_at, user, portal, token)

            # Send password reset email
            reset_url = f'{get_frontend_domain(request)}/reset-password/{token}'
            
            send_link = send_email(request, user, reset_url)
            if send_link:
                message = 'Password reset link sent'
            else:
                message = "Could not send email."    
            return respond_success({'message': message})

        else:
            return respond_error({'message': 'User not found with the provided email.'}, status=400)
    except Exception as e:
        return respond_error(f"Error: {e.args}")
    

def resetPassword(request):
    try:
        body = request.body
        request_data = json.loads(body)
        user = None
        new_password = request_data.get('password')
        token = request_data.get('token')
        portal = request_data.get('portal')
        # check if token is not expired
        expired = ResetPasswordEmailLink.objects.filter(
            token=token,
            expired_at__lt=timezone.now()
        ).first()

        if expired:
            return respond_error({'message': 'Link is expired. Please resend the mail.'}, status=400)
        else:
            reset_obj = ResetPasswordEmailLink.objects.filter(
                    token=token,
                ).first()
            if portal == 'warehouse' or portal == 'admin':
                
                user = WarehouseUsers.objects.get(email=reset_obj.warehouse_user.email)
            elif portal == 'vendor':
                user = VendorUsers.objects.get(email=reset_obj.vendor_user.email)

        if user:
            user.passw = new_password
            user.save()
            return respond_success({'message': 'Password changed successfully.'})    

    except Exception as e:
        return respond_error(f"Error: {e.args}")


def setExpiryTimeForEmail(reset_link_created_at, user, portal, token):
    default_time_limit = 24

    expired_at = timezone.now() + timedelta(hours=default_time_limit)

    # Check the portal whether it is warehouse, admin, or vendor
    if portal == 'warehouse' or portal == 'admin':
        try:
            existing_link = ResetPasswordEmailLink.objects.get(warehouse_user=user)
            existing_link.delete()
        except ResetPasswordEmailLink.DoesNotExist:
            pass

        ResetPasswordEmailLink.objects.create(
            warehouse_user=user,
            created_at=reset_link_created_at,
            expired_at=expired_at,
            token=token
        )
    elif portal == 'vendor':
        try:
            existing_link = ResetPasswordEmailLink.objects.get(vendor_user=user)
            existing_link.delete()
        except ResetPasswordEmailLink.DoesNotExist:
            pass

        ResetPasswordEmailLink.objects.create(
            vendor_user=user,
            created_at=reset_link_created_at,
            expired_at=expired_at,
            token=token
        )
