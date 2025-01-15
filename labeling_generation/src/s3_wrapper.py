from typing import List

import boto3
from dotenv import load_dotenv


class S3BucketWrapper:
    def __init__(self, bucket_name: str):
        load_dotenv()
        self.bucket_name = bucket_name
        self.session = boto3.session.Session()
        self.s3 = self.session.client("s3")

    def list_objects(self) -> List[str]:
        objects = self.s3.list_objects(Bucket=self.bucket_name)["Contents"]
        object_keys = [obj["Key"] for obj in objects]
        return object_keys

    def put_string(self, object_key: str, body: str) -> None:
        self.s3.put_object(Bucket=self.bucket_name, Key=object_key, Body=body)

    def get_object(self, object_: str) -> str:
        response = self.s3.get_object(Bucket=self.bucket_name, Key=object_)
        content = response["Body"].read().decode("utf-8")
        return content

    def delete_object(self, object_: str):
        response = self.s3.delete_object(Bucket=self.bucket_name, Key=object_)
        return response
