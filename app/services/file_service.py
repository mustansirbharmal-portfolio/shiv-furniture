from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
import os
import uuid
from datetime import datetime, timedelta

class FileService:
    _blob_service_client = None
    _container_client = None
    
    @classmethod
    def _get_container_client(cls):
        if cls._container_client is None:
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'files')
            
            if not connection_string:
                raise ValueError("Azure Storage connection string not configured")
            
            cls._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            cls._container_client = cls._blob_service_client.get_container_client(container_name)
            
            try:
                cls._container_client.create_container()
            except Exception:
                pass
        
        return cls._container_client
    
    @staticmethod
    def upload_file(file_data, filename, folder='documents', content_type='application/octet-stream'):
        try:
            container_client = FileService._get_container_client()
            
            ext = os.path.splitext(filename)[1]
            unique_filename = f"{folder}/{datetime.utcnow().strftime('%Y/%m')}/{uuid.uuid4().hex}{ext}"
            
            blob_client = container_client.get_blob_client(unique_filename)
            
            content_settings = ContentSettings(content_type=content_type)
            blob_client.upload_blob(file_data, content_settings=content_settings, overwrite=True)
            
            return {
                'success': True,
                'url': blob_client.url,
                'blob_name': unique_filename,
                'original_filename': filename
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def download_file(blob_name):
        try:
            container_client = FileService._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            
            download_stream = blob_client.download_blob()
            return {
                'success': True,
                'content': download_stream.readall(),
                'content_type': blob_client.get_blob_properties().content_settings.content_type
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def delete_file(blob_name):
        try:
            container_client = FileService._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return {'success': True}
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_file_url(blob_name):
        try:
            container_client = FileService._get_container_client()
            blob_client = container_client.get_blob_client(blob_name)
            return blob_client.url
        except Exception:
            return None
    
    @staticmethod
    def get_file_url_with_sas(blob_name, expiry_hours=1):
        """Generate a URL with SAS token for secure access to private blobs"""
        try:
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'files')
            
            # Parse account name and key from connection string
            parts = dict(part.split('=', 1) for part in connection_string.split(';') if '=' in part)
            account_name = parts.get('AccountName')
            account_key = parts.get('AccountKey')
            
            if not account_name or not account_key:
                return None
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Construct URL with SAS token
            blob_url = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
            return blob_url
        except Exception as e:
            print(f"Error generating SAS URL: {e}")
            return None
    
    @staticmethod
    def upload_file_with_sas_url(file_data, filename, folder='documents', content_type='application/octet-stream'):
        """Upload file and return URL with SAS token for immediate access"""
        try:
            container_client = FileService._get_container_client()
            
            ext = os.path.splitext(filename)[1]
            unique_filename = f"{folder}/{datetime.utcnow().strftime('%Y/%m')}/{uuid.uuid4().hex}{ext}"
            
            blob_client = container_client.get_blob_client(unique_filename)
            
            content_settings = ContentSettings(content_type=content_type)
            blob_client.upload_blob(file_data, content_settings=content_settings, overwrite=True)
            
            # Get URL with SAS token
            sas_url = FileService.get_file_url_with_sas(unique_filename)
            
            return {
                'success': True,
                'url': sas_url or blob_client.url,
                'blob_name': unique_filename,
                'original_filename': filename
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
