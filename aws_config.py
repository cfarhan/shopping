import boto3
import os
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

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
        's3_bucket': os.environ.get('S3_BUCKET_NAME'),
        'environment': os.environ.get('FLASK_ENV', 'development')
    } 