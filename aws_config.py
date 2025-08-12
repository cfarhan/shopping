import boto3
import json
import os
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

class AWSSecretsManager:
    """AWS Secrets Manager utility class"""
    
    def __init__(self, region_name=None):
        self.region_name = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        try:
            self.client = boto3.client('secretsmanager', region_name=self.region_name)
        except NoCredentialsError:
            logger.warning("AWS credentials not found. Secrets Manager will not be available.")
            self.client = None
    
    def get_secret(self, secret_name):
        """Retrieve a secret from AWS Secrets Manager"""
        if not self.client:
            return None
            
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Parse JSON secrets
            if 'SecretString' in response:
                secret = response['SecretString']
                try:
                    return json.loads(secret)
                except json.JSONDecodeError:
                    return secret
            else:
                # Binary secrets
                return response['SecretBinary']
                
        except ClientError as e:
            logger.error(f"Error retrieving secret {secret_name}: {e}")
            return None
    
    def get_database_credentials(self, secret_name):
        """Get database credentials from secrets manager"""
        secret = self.get_secret(secret_name)
        if secret and isinstance(secret, dict):
            return {
                'username': secret.get('username'),
                'password': secret.get('password'),
                'host': secret.get('host'),
                'port': secret.get('port', 5432),
                'dbname': secret.get('dbname')
            }
        return None

class S3Manager:
    """S3 utility class for image storage"""
    
    def __init__(self, bucket_name=None, region_name=None):
        self.bucket_name = bucket_name or os.environ.get('S3_BUCKET_NAME')
        self.region_name = region_name or os.environ.get('AWS_REGION', 'us-east-1')
        
        try:
            self.client = boto3.client('s3', region_name=self.region_name)
            self.s3_resource = boto3.resource('s3', region_name=self.region_name)
        except NoCredentialsError:
            logger.warning("AWS credentials not found. S3 will not be available.")
            self.client = None
            self.s3_resource = None
    
    def upload_file(self, file_obj, object_name, content_type=None):
        """Upload a file to S3"""
        if not self.client or not self.bucket_name:
            return None
            
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
                
            self.client.upload_fileobj(file_obj, self.bucket_name, object_name, ExtraArgs=extra_args)
            
            # Return public URL
            return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{object_name}"
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return None
    
    def delete_file(self, object_name):
        """Delete a file from S3"""
        if not self.client or not self.bucket_name:
            return False
            
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def generate_presigned_url(self, object_name, expiration=3600):
        """Generate a presigned URL for private files"""
        if not self.client or not self.bucket_name:
            return None
            
        try:
            response = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

def get_aws_config():
    """Get AWS configuration from environment or defaults"""
    return {
        'region': os.environ.get('AWS_REGION', 'us-east-1'),
        'db_secret_name': os.environ.get('DB_SECRET_NAME', 'shopping-app/database'),
        's3_bucket': os.environ.get('S3_BUCKET_NAME'),
        'environment': os.environ.get('FLASK_ENV', 'development')
    } 