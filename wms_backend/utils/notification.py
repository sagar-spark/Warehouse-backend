# Author: CP

from infra.models import Notifications


def createNotificationBody(payload):
    pass


def getAllNotifications(filters):
    n = Notifications.objects.filter(filters)
    return n


def addNotification(data, sendEmail=False):
    n = Notifications(
        category=data["category"],
        payload=data["payload"],
        emailContent=data["emailContent"],
        vendorId=data["vendorId"],
        vendorAll=data["vendorAll"] if "vendorAll" in data else False,
        warehouseId=data["warehouseId"],
        warehouseAll=data["warehouseAll"] if "warehouseAll" in data else False
    )
    n.save()

    if sendEmail:
        print("Attempting to send email")
        n.emailSent = True
        n.save()


def toggleNotification(id):
    n = Notifications.objects.get(id=id)
    n.statusNew = False
    n.save()
