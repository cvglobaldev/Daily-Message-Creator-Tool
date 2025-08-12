"""
Universal Media Prevention System for Multi-Bot WhatsApp Platform
===============================================================

Comprehensive prevention system that ensures media file integrity across all current 
and future bots in the Faith Journey Drip Content system. This system proactively 
prevents media delivery failures by implementing multiple layers of validation,
monitoring, and automatic repair.

Key Features:
- Real-time media validation during uploads
- Proactive integrity monitoring with scheduled checks  
- Automatic repair of broken media references
- Bot-specific file isolation and naming
- Comprehensive logging and alerting
- Universal application to all existing and future bots

Author: AI Assistant
Date: August 12, 2025
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class UniversalMediaPreventionSystem:
    """Comprehensive media prevention system for all bots"""
    
    def __init__(self, app=None):
        self.app = app
        self.upload_folder = 'static/uploads'
        self.monitoring_active = False
        self.monitor_thread = None
        self.last_check = None
        
        # Media type configurations
        self.media_configs = {
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
        
        # Ensure directories exist
        self._ensure_upload_directories()
        
    def _ensure_upload_directories(self):
        """Ensure all upload directories exist"""
        for config in self.media_configs.values():
            folder_path = os.path.join(self.upload_folder, config['folder'])
            os.makedirs(folder_path, exist_ok=True)
    
    def validate_upload_integrity(self, file, media_type: str, bot_id: int) -> Dict[str, Any]:
        """
        Comprehensive upload validation with bot isolation
        
        Returns:
            Dict with success status, filename, errors, and file info
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
            pre_validation = self._validate_pre_upload(file, media_type, bot_id)
            if not pre_validation['valid']:
                result['errors'].extend(pre_validation['errors'])
                return result
            
            # Generate bot-specific secure filename
            secure_name = self._generate_bot_specific_filename(file.filename, bot_id)
            if not secure_name:
                result['errors'].append("Failed to generate secure filename")
                return result
            
            # Save file with validation
            config = self.media_configs[media_type]
            file_path = os.path.join(self.upload_folder, config['folder'], secure_name)
            
            # Save with error handling
            try:
                file.save(file_path)
                logger.info(f"✅ File saved: {file_path}")
            except Exception as save_error:
                result['errors'].append(f"File save failed: {save_error}")
                return result
            
            # Post-upload validation
            post_validation = self._validate_post_upload(file_path, media_type)
            if not post_validation['valid']:
                # Cleanup failed file
                try:
                    os.remove(file_path)
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
                    'original_name': file.filename,
                    'upload_time': datetime.now().isoformat()
                }
            })
            
            logger.info(f"✅ Universal media upload success - Bot {bot_id}: {secure_name}")
            return result
            
        except Exception as e:
            result['errors'].append(f"Upload validation failed: {e}")
            logger.error(f"❌ Universal media upload failed - Bot {bot_id}: {e}")
            return result
    
    def _validate_pre_upload(self, file, media_type: str, bot_id: int) -> Dict[str, Any]:
        """Pre-upload validation checks"""
        validation = {'valid': True, 'errors': [], 'warnings': []}
        
        # Check media type
        if media_type not in self.media_configs:
            validation['valid'] = False
            validation['errors'].append(f"Unsupported media type: {media_type}")
            return validation
        
        config = self.media_configs[media_type]
        
        # Check file object
        if not file or not hasattr(file, 'filename') or not file.filename:
            validation['valid'] = False
            validation['errors'].append("Invalid or missing file")
            return validation
        
        # Check bot_id
        if not bot_id or bot_id <= 0:
            validation['valid'] = False
            validation['errors'].append("Invalid bot_id for file isolation")
            return validation
        
        # Check file extension
        if '.' not in file.filename:
            validation['valid'] = False
            validation['errors'].append("File missing extension")
            return validation
        
        extension = file.filename.rsplit('.', 1)[1].lower()
        if extension not in config['extensions']:
            validation['valid'] = False
            validation['errors'].append(f"Invalid extension .{extension}")
            return validation
        
        # Check file size
        try:
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            if size > config['max_size']:
                validation['valid'] = False
                validation['errors'].append(f"File too large: {size/(1024*1024):.1f}MB")
            elif size == 0:
                validation['valid'] = False
                validation['errors'].append("File is empty")
        except:
            validation['warnings'].append("Could not verify file size")
        
        return validation
    
    def _generate_bot_specific_filename(self, original_filename: str, bot_id: int) -> Optional[str]:
        """Generate secure bot-specific filename"""
        try:
            import uuid
            
            # Clean filename
            clean_name = secure_filename(original_filename)
            if not clean_name:
                return None
            
            # Split name and extension
            if '.' in clean_name:
                name, ext = clean_name.rsplit('.', 1)
            else:
                name, ext = clean_name, ''
            
            # Generate bot-specific unique filename
            unique_id = uuid.uuid4().hex[:12]
            if ext:
                return f"bot{bot_id}_{unique_id}_{name}.{ext}"
            else:
                return f"bot{bot_id}_{unique_id}_{name}"
                
        except Exception as e:
            logger.error(f"Filename generation failed: {e}")
            return None
    
    def _validate_post_upload(self, file_path: str, media_type: str) -> Dict[str, Any]:
        """Post-upload validation checks"""
        validation = {'valid': True, 'errors': []}
        
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
            
            # Check against max size
            config = self.media_configs[media_type]
            if size > config['max_size']:
                validation['valid'] = False
                validation['errors'].append(f"File exceeds size limit")
                return validation
                
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"Size validation failed: {e}")
        
        return validation
    
    def start_proactive_monitoring(self, check_interval_minutes: int = 30):
        """Start proactive media integrity monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval_minutes,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"✅ Universal media monitoring started (interval: {check_interval_minutes} min)")
    
    def stop_proactive_monitoring(self):
        """Stop proactive monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Universal media monitoring stopped")
    
    def _monitoring_loop(self, check_interval_minutes: int):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                # Run integrity check
                self.run_system_wide_integrity_check()
                self.last_check = datetime.now()
                
                # Wait for next check
                time.sleep(check_interval_minutes * 60)
                
            except Exception as e:
                logger.error(f"Media monitoring error: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def run_system_wide_integrity_check(self) -> Dict[str, Any]:
        """Run integrity check across all bots"""
        try:
            if not self.app:
                return {'error': 'No app context available'}
            
            with self.app.app_context():
                from media_integrity_service import media_integrity
                
                # Check all bots
                overall_validation = media_integrity.validate_content_media_integrity()
                
                # Auto-repair if needed
                if overall_validation['missing_media'] or overall_validation['corrupted_references']:
                    logger.warning(f"Found {len(overall_validation['missing_media'])} missing and {len(overall_validation['corrupted_references'])} corrupted media files")
                    repair_stats = media_integrity.repair_media_integrity(auto_fix=True)
                    logger.info(f"Auto-repair completed: {repair_stats['broken_references_fixed']} fixes, {repair_stats['errors']} errors")
                
                integrity_score = overall_validation['summary'].get('integrity_score', 0)
                
                # Log status
                if integrity_score >= 95:
                    logger.info(f"✅ System-wide media integrity: {integrity_score}% - Excellent")
                elif integrity_score >= 80:
                    logger.warning(f"⚠️ System-wide media integrity: {integrity_score}% - Good")
                else:
                    logger.error(f"❌ System-wide media integrity: {integrity_score}% - Critical")
                
                return overall_validation
                
        except Exception as e:
            logger.error(f"System-wide integrity check failed: {e}")
            return {'error': str(e)}
    
    def validate_existing_media_references(self, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate all existing media references for specific bot or all bots"""
        try:
            if not self.app:
                return {'error': 'No app context available'}
            
            with self.app.app_context():
                from models import Content
                
                query = Content.query
                if bot_id:
                    query = query.filter_by(bot_id=bot_id)
                
                contents = query.filter(
                    (Content.image_filename.isnot(None)) |
                    (Content.video_filename.isnot(None)) |
                    (Content.audio_filename.isnot(None))
                ).all()
                
                validation_results = {
                    'total_checked': len(contents),
                    'valid_references': 0,
                    'broken_references': 0,
                    'details': []
                }
                
                for content in contents:
                    content_info = f"Bot {content.bot_id} Day {content.day_number}"
                    
                    # Check image
                    if content.image_filename:
                        file_path = os.path.join(self.upload_folder, 'images', content.image_filename)
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            validation_results['valid_references'] += 1
                            validation_results['details'].append(f"✅ {content_info} - Image valid")
                        else:
                            validation_results['broken_references'] += 1
                            validation_results['details'].append(f"❌ {content_info} - Image missing: {content.image_filename}")
                    
                    # Check video
                    if content.video_filename:
                        file_path = os.path.join(self.upload_folder, 'videos', content.video_filename)
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            validation_results['valid_references'] += 1
                            validation_results['details'].append(f"✅ {content_info} - Video valid")
                        else:
                            validation_results['broken_references'] += 1
                            validation_results['details'].append(f"❌ {content_info} - Video missing: {content.video_filename}")
                    
                    # Check audio
                    if content.audio_filename:
                        file_path = os.path.join(self.upload_folder, 'audio', content.audio_filename)
                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                            validation_results['valid_references'] += 1
                            validation_results['details'].append(f"✅ {content_info} - Audio valid")
                        else:
                            validation_results['broken_references'] += 1
                            validation_results['details'].append(f"❌ {content_info} - Audio missing: {content.audio_filename}")
                
                # Calculate integrity score
                total_references = validation_results['valid_references'] + validation_results['broken_references']
                if total_references > 0:
                    integrity_score = (validation_results['valid_references'] / total_references) * 100
                else:
                    integrity_score = 100
                
                validation_results['integrity_score'] = round(integrity_score, 2)
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Media reference validation failed: {e}")
            return {'error': str(e)}

# Global prevention system instance
universal_prevention = UniversalMediaPreventionSystem()

def initialize_prevention_system(app):
    """Initialize the prevention system with Flask app context"""
    global universal_prevention
    universal_prevention.app = app
    universal_prevention.start_proactive_monitoring(check_interval_minutes=30)
    return universal_prevention

def validate_and_upload_with_prevention(file, media_type: str, bot_id: int):
    """Validate and upload file using prevention system"""
    return universal_prevention.validate_upload_integrity(file, media_type, bot_id)

def run_integrity_check_for_bot(bot_id: int):
    """Run integrity check for specific bot"""
    return universal_prevention.validate_existing_media_references(bot_id)

def run_system_wide_check():
    """Run system-wide integrity check"""
    return universal_prevention.run_system_wide_integrity_check()

if __name__ == "__main__":
    print("🛡️ Universal Media Prevention System")
    print("====================================")
    
    prevention = UniversalMediaPreventionSystem()
    
    print(f"Upload folder: {prevention.upload_folder}")
    print(f"Supported media types: {list(prevention.media_configs.keys())}")
    
    for media_type, config in prevention.media_configs.items():
        folder_path = os.path.join(prevention.upload_folder, config['folder'])
        exists = os.path.exists(folder_path)
        max_size_mb = config['max_size'] / (1024 * 1024)
        print(f"  {media_type}: {folder_path} {'✅' if exists else '❌'} (max: {max_size_mb}MB)")
    
    print("\n✅ Prevention system ready for deployment!")