import boto3
from boto3 import resource as connection

class S3(object):
    """Class to Download/upload files to/from s3
    The key and secret must be in your ~/.aws configuration files, or provided in a credentials dictionary
    """


    def __init__(self, credentials=None, logger=None):
        """
        :param credentials: dict    optional credentials file
        :param logger: object    optional logger class
        :return:
        """
        self.s3_client = boto3.client('s3')
        if not credentials:
            self.s3 = connection('s3')
            self.s3_client = boto3.client('s3')
        else:
            aws_access_key_id = credentials["aws_access_key_id"]
            aws_secret_access_key = credentials['aws_secret_access_key']
            region_name = credentials['region_name']
            self.s3 = connection('s3', aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key,
                                 region_name=region_name)
            self.s3_client = boto3.client('s3', **credentials)
        self._logger = logger

    def generate_presigned_url(self, bucket, key, client_method='get_object', expires_in=31536000, content_type=None):
        params = {'Bucket': bucket, 'Key': key}
        if content_type is not None:
            params['ContentType'] = content_type
        try:
            presigned_url = self.s3_client.generate_presigned_url(client_method, Params=params, ExpiresIn=expires_in)
        except Exception as e:
            self._logger.error(e)
        else:
            if presigned_url:
                return presigned_url
            else:
                self._logger.error("Failed to obtain pre-signed_url")
                return False

    def upload(self, bucket_name, key, data):
        """Upload a file to S3.
        :param bucket_name: bucket name
        :param key: string
        :param data: file data
        :rtype bool
        :return: sucess of failure
        """
        try:
            bucket = self.s3.Bucket(bucket_name)
            bucket.put_object(Key=key, Body=data, ACL='authenticated-read')  # public-read
        except Exception as e:
            if self._logger:
                self._logger.error(e)
            else:
                print(e)
            return False
        else:
            return self.generate_presigned_url(bucket_name, key)

    def upload_file(self, bucket_name, key, data):
        try:
            self.s3.upload_fileobj(data, bucket_name, key)
        except Exception as e:
            if self._logger:
                self._logger.error(e)
            else:
                print(e)
            return False
        else:
            return self.generate_presigned_url(bucket_name, key)