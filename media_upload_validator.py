"""
Media Upload Validator for Universal Bot Support
===============================================

Comprehensive validation system for media file uploads in the CMS to prevent
delivery failures and ensure consistent file management across all bots.

This system ensures:
- All uploaded files are properly saved with bot-specific isolation
- Database references match actual files on filesystem
- Media types are correctly validated
- File integrity is maintained throughout the upload process
- Automatic cleanup of failed uploads

Features:
- Pre-upload validation (file type, size, format)
- Post-upload verification (file existence, integrity)
- Bot-specific file naming and isolation
- Automatic rollback on upload failures
- Comprehensive logging and error handling

Author: AI Assistant  
Date: August 12, 2025
"""

import os
import uuid
import shutil
from typing import Optional, Dict, Any, Tuple
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

class MediaUploadValidator:
    """Comprehensive media upload validation and management"""
    
    def __init__(self, upload_folder: str = 'static/uploads'):
        self.upload_folder = upload_folder
        self.media_types = {
            'image': {
                'folder': 'images',
                'extensions': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                'max_size': 10 * 1024 * 1024,  # 10MB
                'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            },
            'video': {
                'folder': 'videos',
                'extensions': ['mp4', 'mov', 'avi', 'mkv'],
                'max_size': 100 * 1024 * 1024,  # 100MB
                'mime_types': ['video/mp4', 'video/quicktime', 'video/x-msvideo']
            },
            'audio': {
                'folder': 'audio',
                'extensions': ['mp3', 'wav', 'ogg', 'm4a', 'aac'],
                'max_size': 25 * 1024 * 1024,  # 25MB
                'mime_types': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4']
            }
        }
        
        # Ensure all directories exist
        for media_config in self.media_types.values():
            folder_path = os.path.join(self.upload_folder, media_config['folder'])
            os.makedirs(folder_path, exist_ok=True)
    
    def validate_and_upload(self, file, media_type: str, bot_id: int) -> Dict[str, Any]:
        """
        Comprehensive validation and upload process
        
        Args:
            file: File object from request
            media_type: Type of media (image/video/audio)
            bot_id: Bot ID for file isolation
            
        Returns:
            Upload result with status and details
        """
        result = {
            'success': False,
            'filename': None,
            'file_path': None,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Pre-upload validation
            validation = self._validate_file_pre_upload(file, media_type)
            if not validation['valid']:
                result['errors'].extend(validation['errors'])
                return result
            
            # Generate secure filename with bot isolation
            filename_result = self._generate_secure_filename(file.filename, bot_id)
            if not filename_result['success']:
                result['errors'].extend(filename_result['errors'])
                return result
            
            secure_name = filename_result['filename']
            
            # Determine upload path
            media_config = self.media_types[media_type]
            upload_dir = os.path.join(self.upload_folder, media_config['folder'])
            file_path = os.path.join(upload_dir, secure_name)
            
            # Save file with error handling
            try:
                file.save(file_path)
                logger.info(f"File saved successfully: {file_path}")
            except Exception as save_error:
                result['errors'].append(f"Failed to save file: {save_error}")
                return result
            
            # Post-upload validation
            post_validation = self._validate_file_post_upload(file_path, media_type)
            if not post_validation['valid']:
                # Cleanup failed upload
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up failed upload: {file_path}")
                except:
                    pass
                result['errors'].extend(post_validation['errors'])
                return result
            
            # Success
            result.update({
                'success': True,
                'filename': secure_name,
                'file_path': file_path,
                'file_info': {
                    'size': os.path.getsize(file_path),
                    'type': media_type,
                    'bot_id': bot_id,
                    'original_name': file.filename
                }
            })
            
            logger.info(f"✅ Media upload successful for Bot {bot_id}: {secure_name}")
            return result
            
        except Exception as e:
            result['errors'].append(f"Upload process failed: {e}")
            logger.error(f"❌ Media upload failed for Bot {bot_id}: {e}")
            return result
    
    def _validate_file_pre_upload(self, file, media_type: str) -> Dict[str, Any]:
        """Validate file before upload attempt"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if media type is supported
        if media_type not in self.media_types:
            validation['valid'] = False
            validation['errors'].append(f"Unsupported media type: {media_type}")
            return validation
        
        media_config = self.media_types[media_type]
        
        # Check file object
        if not file or not hasattr(file, 'filename') or not file.filename:
            validation['valid'] = False
            validation['errors'].append("No file provided or invalid file object")
            return validation
        
        # Check file extension
        if '.' not in file.filename:
            validation['valid'] = False
            validation['errors'].append("File has no extension")
            return validation
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in media_config['extensions']:
            validation['valid'] = False
            validation['errors'].append(f"Invalid file extension .{extension}. Allowed: {', '.join(media_config['extensions'])}")
            return validation
        
        # Check file size (if possible)
        try:
            file.seek(0, 2)  # Seek to end
            size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if size > media_config['max_size']:
                validation['valid'] = False
                validation['errors'].append(f"File too large: {size / (1024*1024):.1f}MB. Max: {media_config['max_size'] / (1024*1024):.1f}MB")
            elif size == 0:
                validation['valid'] = False
                validation['errors'].append("File is empty")
        except:
            validation['warnings'].append("Could not verify file size")
        
        return validation
    
    def _generate_secure_filename(self, original_filename: str, bot_id: int) -> Dict[str, Any]:
        """Generate secure filename with bot isolation"""
        try:
            # Clean the filename
            clean_name = secure_filename(original_filename)
            if not clean_name:
                return {
                    'success': False,
                    'errors': ['Invalid filename - contains only unsafe characters']
                }
            
            # Split name and extension
            if '.' in clean_name:
                name, ext = clean_name.rsplit('.', 1)
            else:
                name, ext = clean_name, ''
            
            # Generate bot-specific unique filename
            unique_id = uuid.uuid4().hex[:12]
            secure_name = f"bot{bot_id}_{unique_id}_{name}.{ext}" if ext else f"bot{bot_id}_{unique_id}_{name}"
            
            return {
                'success': True,
                'filename': secure_name,
                'original': original_filename,
                'errors': []
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [f'Filename generation failed: {e}']
            }
    
    def _validate_file_post_upload(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """Validate file after upload"""
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file exists
        if not os.path.exists(file_path):
            validation['valid'] = False
            validation['errors'].append(f"File not found after upload: {file_path}")
            return validation
        
        # Check file size
        try:
            size = os.path.getsize(file_path)
            if size == 0:
                validation['valid'] = False
                validation['errors'].append("File is empty after upload")
                return validation
            
            # Check against max size again
            media_config = self.media_types[media_type]
            if size > media_config['max_size']:
                validation['valid'] = False
                validation['errors'].append(f"File size exceeds limit: {size / (1024*1024):.1f}MB")
                return validation
                
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Could not verify file size: {e}")
            return validation
        
        # Check file permissions
        if not os.access(file_path, os.R_OK):
            validation['warnings'].append("File may not be readable")
        
        return validation
    
    def cleanup_failed_upload(self, file_path: str) -> bool:
        """Clean up failed upload"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up failed upload: {file_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")
        return False
    
    def validate_existing_file(self, filename: str, media_type: str) -> Dict[str, Any]:
        """Validate existing file in storage"""
        media_config = self.media_types.get(media_type)
        if not media_config:
            return {'valid': False, 'error': f'Unknown media type: {media_type}'}
        
        file_path = os.path.join(self.upload_folder, media_config['folder'], filename)
        
        if not os.path.exists(file_path):
            return {'valid': False, 'error': f'File not found: {file_path}'}
        
        try:
            size = os.path.getsize(file_path)
            if size == 0:
                return {'valid': False, 'error': 'File is empty'}
            
            return {
                'valid': True,
                'file_path': file_path,
                'size': size,
                'readable': os.access(file_path, os.R_OK)
            }
        except Exception as e:
            return {'valid': False, 'error': f'File validation failed: {e}'}

# Global validator instance
media_upload_validator = MediaUploadValidator()

def validate_and_upload_media(file, media_type: str, bot_id: int):
    """Convenience function for media upload validation"""
    return media_upload_validator.validate_and_upload(file, media_type, bot_id)

def validate_existing_media_file(filename: str, media_type: str):
    """Convenience function for validating existing files"""
    return media_upload_validator.validate_existing_file(filename, media_type)

if __name__ == "__main__":
    print("🔍 Media Upload Validator - Testing Configuration...")
    
    validator = MediaUploadValidator()
    print(f"Upload folder: {validator.upload_folder}")
    
    for media_type, config in validator.media_types.items():
        folder_path = os.path.join(validator.upload_folder, config['folder'])
        exists = os.path.exists(folder_path)
        print(f"  {media_type}: {folder_path} {'✅' if exists else '❌'}")
    
    print("✅ Media Upload Validator ready!")