import boto3
from botocore.exceptions import ClientError

# AWS S3 client
s3 = boto3.client('s3')

# 使用者輸入桶名與檔案名
bucket_name = input("Enter bucket name: ")
file_name = input("Enter the file name to upload: ")
object_name = file_name  # 上傳後在桶裡的名稱，可自訂

# 檢查桶是否存在
def bucket_exists(bucket):
    try:
        s3.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        return False

# 建立桶
def create_bucket(bucket):
    try:
        # 預設使用 AWS CLI 設定的區域
        region = boto3.session.Session().region_name
        if region is None:
            region = 'us-east-1'  # 預設區域
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={'LocationConstraint': region} if region != 'us-east-1' else {}
        )
        print(f"Bucket '{bucket}' created in region '{region}'.")
    except ClientError as e:
        print(f"Failed to create bucket: {e}")
        exit(1)

# 上傳檔案
def upload_file(bucket, file, object_name):
    try:
        s3.upload_file(file, bucket, object_name)
        print(f"File '{file}' uploaded to bucket '{bucket}' as '{object_name}'.")
    except ClientError as e:
        print(f"Error uploading file: {e}")

# 主流程
if not bucket_exists(bucket_name):
    print(f"Bucket '{bucket_name}' does not exist. Creating it...")
    create_bucket(bucket_name)

upload_file(bucket_name, file_name, object_name)
