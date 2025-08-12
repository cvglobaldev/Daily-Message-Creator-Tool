"""
Media File Management and Validation System
==========================================

Comprehensive media file management system for multi-bot WhatsApp and Telegram integration.
Handles file validation, missing file recovery, and automatic fallback mechanisms.

This system ensures that:
1. All media files referenced in database actually exist on filesystem
2. Missing files are detected and logged with corrective actions
3. Content delivery continues gracefully with text-only fallbacks
4. Administrators are notified of missing media issues

Author: AI Assistant
Date: August 12, 2025
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class MediaFileManager:
    """Comprehensive media file validation and management system"""
    
    def __init__(self, db_url=None):
        self.base_path = "static/uploads"
        self.media_directories = {
            'image': 'static/uploads/images',
            'video': 'static/uploads/videos', 
            'audio': 'static/uploads/audio'
        }
        
        # Ensure all directories exist
        for dir_path in self.media_directories.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def validate_all_media_files(self) -> Dict[str, List[str]]:
        """
        Validate all media files referenced in database content
        
        Returns:
            Dictionary with 'missing', 'found', and 'issues' lists
        """
        try:
            from models import Content
            from app import db
            
            results = {
                'missing': [],
                'found': [],
                'issues': [],
                'summary': {}
            }
            
            # Get all content with media references
            contents = Content.query.filter(
                (Content.image_filename.isnot(None)) |
                (Content.video_filename.isnot(None)) |
                (Content.audio_filename.isnot(None))
            ).all()
            
            logger.info(f"Checking {len(contents)} content items with media references")
            
            for content in contents:
                content_info = f"Bot {content.bot_id} Day {content.day_number} - {content.title}"
                
                # Check image file
                if content.image_filename:
                    file_path = os.path.join(self.media_directories['image'], content.image_filename)
                    if os.path.exists(file_path):
                        results['found'].append(f"✅ IMAGE: {content_info} - {content.image_filename}")
                    else:
                        results['missing'].append(f"❌ IMAGE: {content_info} - {content.image_filename}")
                        
                # Check video file  
                if content.video_filename:
                    file_path = os.path.join(self.media_directories['video'], content.video_filename)
                    if os.path.exists(file_path):
                        results['found'].append(f"✅ VIDEO: {content_info} - {content.video_filename}")
                    else:
                        results['missing'].append(f"❌ VIDEO: {content_info} - {content.video_filename}")
                        
                # Check audio file
                if content.audio_filename:
                    file_path = os.path.join(self.media_directories['audio'], content.audio_filename)
                    if os.path.exists(file_path):
                        results['found'].append(f"✅ AUDIO: {content_info} - {content.audio_filename}")
                    else:
                        results['missing'].append(f"❌ AUDIO: {content_info} - {content.audio_filename}")
                        
            # Generate summary
            results['summary'] = {
                'total_content_items': len(contents),
                'found_files': len(results['found']),
                'missing_files': len(results['missing']),
                'issues_detected': len(results['issues'])
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating media files: {e}")
            return {'missing': [], 'found': [], 'issues': [str(e)], 'summary': {}}
    
    def fix_missing_media_files(self, auto_fix: bool = True) -> Dict[str, int]:
        """
        Fix missing media file references in database
        
        Args:
            auto_fix: If True, automatically update database to remove missing file references
            
        Returns:
            Dictionary with fix statistics
        """
        try:
            from models import Content
            from app import db
            
            fixed_count = 0
            error_count = 0
            
            # Get validation results
            validation = self.validate_all_media_files()
            missing_files = validation['missing']
            
            if not missing_files:
                logger.info("✅ No missing media files found")
                return {'fixed': 0, 'errors': 0, 'total_missing': 0}
            
            logger.warning(f"Found {len(missing_files)} missing media files")
            
            if auto_fix:
                # Get all content items and fix missing references
                contents = Content.query.filter(
                    (Content.image_filename.isnot(None)) |
                    (Content.video_filename.isnot(None)) |
                    (Content.audio_filename.isnot(None))
                ).all()
                
                for content in contents:
                    updated = False
                    
                    # Check and fix image file
                    if content.image_filename:
                        file_path = os.path.join(self.media_directories['image'], content.image_filename)
                        if not os.path.exists(file_path):
                            logger.info(f"Fixing missing image for Bot {content.bot_id} Day {content.day_number}")
                            content.image_filename = None
                            if content.media_type == 'image':
                                content.media_type = 'text'
                            updated = True
                            
                    # Check and fix video file
                    if content.video_filename:
                        file_path = os.path.join(self.media_directories['video'], content.video_filename)
                        if not os.path.exists(file_path):
                            logger.info(f"Fixing missing video for Bot {content.bot_id} Day {content.day_number}")
                            content.video_filename = None
                            if content.media_type == 'video':
                                content.media_type = 'text'
                            updated = True
                            
                    # Check and fix audio file
                    if content.audio_filename:
                        file_path = os.path.join(self.media_directories['audio'], content.audio_filename)
                        if not os.path.exists(file_path):
                            logger.info(f"Fixing missing audio for Bot {content.bot_id} Day {content.day_number}")
                            content.audio_filename = None
                            if content.media_type == 'audio':
                                content.media_type = 'text'
                            updated = True
                    
                    if updated:
                        try:
                            db.session.commit()
                            fixed_count += 1
                            logger.info(f"✅ Fixed content for Bot {content.bot_id} Day {content.day_number}")
                        except Exception as e:
                            db.session.rollback()
                            error_count += 1
                            logger.error(f"❌ Error fixing content for Bot {content.bot_id} Day {content.day_number}: {e}")
            
            return {
                'fixed': fixed_count,
                'errors': error_count,
                'total_missing': len(missing_files)
            }
            
        except Exception as e:
            logger.error(f"Error fixing missing media files: {e}")
            return {'fixed': 0, 'errors': 1, 'total_missing': 0}
    
    def list_available_media_files(self) -> Dict[str, List[str]]:
        """List all available media files in upload directories"""
        available_files = {}
        
        for media_type, directory in self.media_directories.items():
            if os.path.exists(directory):
                files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
                available_files[media_type] = files
            else:
                available_files[media_type] = []
                
        return available_files
    
    def generate_media_report(self) -> str:
        """Generate comprehensive media file status report"""
        try:
            validation = self.validate_all_media_files()
            available = self.list_available_media_files()
            
            report = []
            report.append("=" * 60)
            report.append("MEDIA FILE VALIDATION REPORT")
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("=" * 60)
            
            # Summary
            summary = validation['summary']
            report.append(f"\nSUMMARY:")
            report.append(f"  Content Items Checked: {summary.get('total_content_items', 0)}")
            report.append(f"  Files Found: {summary.get('found_files', 0)}")
            report.append(f"  Files Missing: {summary.get('missing_files', 0)}")
            report.append(f"  Issues: {summary.get('issues_detected', 0)}")
            
            # Available files
            report.append(f"\nAVAILABLE FILES:")
            for media_type, files in available.items():
                report.append(f"  {media_type.upper()}: {len(files)} files")
                for file in files[:5]:  # Show first 5 files
                    report.append(f"    - {file}")
                if len(files) > 5:
                    report.append(f"    ... and {len(files) - 5} more")
            
            # Missing files
            if validation['missing']:
                report.append(f"\nMISSING FILES ({len(validation['missing'])}):")
                for missing in validation['missing'][:10]:  # Show first 10
                    report.append(f"  {missing}")
                if len(validation['missing']) > 10:
                    report.append(f"  ... and {len(validation['missing']) - 10} more")
            
            # Issues
            if validation['issues']:
                report.append(f"\nISSUES:")
                for issue in validation['issues']:
                    report.append(f"  - {issue}")
                    
            report.append("\n" + "=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            return f"Error generating media report: {e}"

# Global instance
media_manager = MediaFileManager()

def validate_media_files():
    """Convenience function to validate all media files"""
    return media_manager.validate_all_media_files()

def fix_missing_media_files(auto_fix=True):
    """Convenience function to fix missing media files"""
    return media_manager.fix_missing_media_files(auto_fix)

def generate_media_report():
    """Convenience function to generate media report"""
    return media_manager.generate_media_report()

if __name__ == "__main__":
    # Run media validation and fixing
    print("Starting Media File Validation and Repair...")
    print()
    
    # Generate report
    report = generate_media_report()
    print(report)
    
    # Fix missing files
    print("\nFixing missing media file references...")
    fix_results = fix_missing_media_files(auto_fix=True)
    print(f"Fixed: {fix_results['fixed']}")
    print(f"Errors: {fix_results['errors']}")
    print(f"Total Missing: {fix_results['total_missing']}")