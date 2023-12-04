# Author: CP

import boto3

s3_client = boto3.client('s3')

def uploadFile(bucketName, localFile, remoteFileWithFolder):
    
    with open(localFile, 'rb') as fd:
        result = s3_client.put_object(
            Bucket=bucketName,
            Key=remoteFileWithFolder,
            Body=fd,
            ContentType="image/png",
            ACL='public-read-write'
        )

        if result['ResponseMetadata']['HTTPStatusCode'] == 200:
            response = {
                "path": "https://{}.s3.ap-south-1.amazonaws.com/{}".format(
                    bucketName, remoteFileWithFolder),
                "uploaded": True
            }

        else:
            response = {
                "uploaded": False
            }

        return response

