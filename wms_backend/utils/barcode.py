from barcode import EAN13, Code128
from barcode.writer import ImageWriter
from barcode.writer import SVGWriter

import base64

import os

from utils import awss3

from django.conf import settings

def getBarCode(str):
    outFileName = "/tmp/{}".format(str)
    with open(outFileName, "wb") as f:
        Code128(str, writer=ImageWriter()).write(f)
    with open(outFileName, 'rb') as f:
        b64String = base64.b64encode(f.read())
    
    return b64String.decode('UTF-8')

def saveBarcodeToPngFile(text, outFile):
    with open(outFile, "wb") as f:
        Code128(text, writer=ImageWriter()).write(f)

def saveBarcodeToSVGFile(text, outFile):
    with open (outFile, "wb") as fd:
        Code128(text, writer=SVGWriter()).write(fd)


def handleBarCode(text, s3Folder):

    fileName = "{}.png".format(text)
    tempPath = os.path.join("/tmp", fileName)

    saveBarcodeToPngFile(text, tempPath)

    bucketName = settings.TENANT_SETTINGS["appSettings"]["S3_BUCKETS"]["BARCODE"]
    remoteFilePath = os.path.join(s3Folder, fileName)

    response =awss3.uploadFile(
        bucketName=bucketName,
        localFile=tempPath,
        remoteFileWithFolder=remoteFilePath
    )

    return response

