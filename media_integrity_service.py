"""
Media Integrity Service for Multi-Bot WhatsApp System
=====================================================

Comprehensive media file management service that ensures reliable content delivery
across all bots by validating file existence, cleaning broken references, and 
providing automated maintenance.

This service prevents the issue where media files are referenced in the database
but don't exist on the filesystem, causing content delivery failures.

Features:
- Automatic detection of missing media files
- Database cleanup of broken references  
- Proactive file validation before content delivery
- Bot-specific media file isolation
- Comprehensive reporting and logging

Author: AI Assistant
Date: August 12, 2025
"""

import os
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class MediaIntegrityService:
    """Service for maintaining media file integrity across all bots"""
    
    def __init__(self, app=None):
        self.app = app
        self.media_directories = {
            'image': 'static/uploads/images',
            'video': 'static/uploads/videos',
            'audio': 'static/uploads/audio'
        }
        
        # Ensure all directories exist
        for dir_path in self.media_directories.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def validate_content_media_integrity(self, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Validate media integrity for all content items
        
        Args:
            bot_id: Optional bot ID to filter validation (None for all bots)
            
        Returns:
            Comprehensive validation report
        """
        try:
            from models import Content
            
            query = Content.query
            if bot_id:
                query = query.filter_by(bot_id=bot_id)
            
            # Get all content with media references
            contents = query.filter(
                (Content.image_filename.isnot(None)) |
                (Content.video_filename.isnot(None)) |
                (Content.audio_filename.isnot(None))
            ).all()
            
            results = {
                'total_checked': len(contents),
                'valid_media': [],
                'missing_media': [],
                'corrupted_references': [],
                'bots_affected': set(),
                'summary': {}
            }
            
            logger.info(f"Validating media integrity for {len(contents)} content items (bot_id: {bot_id or 'all'})")
            
            for content in contents:
                bot_info = f"Bot {content.bot_id}"
                content_info = f"{bot_info} Day {content.day_number} - {content.title}"
                results['bots_affected'].add(content.bot_id)
                
                # Check image file
                if content.image_filename:
                    file_path = os.path.join(self.media_directories['image'], content.image_filename)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        results['valid_media'].append(f"✅ IMAGE: {content_info} - {content.image_filename}")
                    elif os.path.exists(file_path):
                        results['corrupted_references'].append(f"⚠️  EMPTY IMAGE: {content_info} - {content.image_filename}")
                    else:
                        results['missing_media'].append(f"❌ MISSING IMAGE: {content_info} - {content.image_filename}")
                        
                # Check video file  
                if content.video_filename:
                    file_path = os.path.join(self.media_directories['video'], content.video_filename)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        results['valid_media'].append(f"✅ VIDEO: {content_info} - {content.video_filename}")
                    elif os.path.exists(file_path):
                        results['corrupted_references'].append(f"⚠️  EMPTY VIDEO: {content_info} - {content.video_filename}")
                    else:
                        results['missing_media'].append(f"❌ MISSING VIDEO: {content_info} - {content.video_filename}")
                        
                # Check audio file
                if content.audio_filename:
                    file_path = os.path.join(self.media_directories['audio'], content.audio_filename)
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        results['valid_media'].append(f"✅ AUDIO: {content_info} - {content.audio_filename}")
                    elif os.path.exists(file_path):
                        results['corrupted_references'].append(f"⚠️  EMPTY AUDIO: {content_info} - {content.audio_filename}")
                    else:
                        results['missing_media'].append(f"❌ MISSING AUDIO: {content_info} - {content.audio_filename}")
            
            # Generate summary
            results['summary'] = {
                'total_content_items': len(contents),
                'valid_files': len(results['valid_media']),
                'missing_files': len(results['missing_media']),
                'corrupted_files': len(results['corrupted_references']),
                'bots_affected': len(results['bots_affected']),
                'integrity_score': round((len(results['valid_media']) / max(len(results['valid_media']) + len(results['missing_media']) + len(results['corrupted_references']), 1)) * 100, 2)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error validating media integrity: {e}")
            return {
                'total_checked': 0,
                'valid_media': [],
                'missing_media': [],
                'corrupted_references': [f"Validation error: {e}"],
                'bots_affected': set(),
                'summary': {'integrity_score': 0}
            }
    
    def repair_media_integrity(self, bot_id: Optional[int] = None, auto_fix: bool = True) -> Dict[str, int]:
        """
        Repair media integrity issues by cleaning broken references
        
        Args:
            bot_id: Optional bot ID to filter repairs (None for all bots)
            auto_fix: Whether to automatically fix issues
            
        Returns:
            Repair statistics
        """
        try:
            from models import Content
            from app import db
            
            repair_stats = {
                'content_items_checked': 0,
                'broken_references_fixed': 0,
                'files_cleaned': 0,
                'errors': 0
            }
            
            # Get validation results first
            validation = self.validate_content_media_integrity(bot_id)
            
            if not validation['missing_media'] and not validation['corrupted_references']:
                logger.info("✅ No media integrity issues found")
                return repair_stats
            
            if not auto_fix:
                logger.info(f"Found {len(validation['missing_media']) + len(validation['corrupted_references'])} issues but auto_fix is disabled")
                return repair_stats
            
            logger.warning(f"Repairing {len(validation['missing_media']) + len(validation['corrupted_references'])} media integrity issues...")
            
            # Get all content items that need fixing
            query = Content.query
            if bot_id:
                query = query.filter_by(bot_id=bot_id)
            
            contents = query.filter(
                (Content.image_filename.isnot(None)) |
                (Content.video_filename.isnot(None)) |
                (Content.audio_filename.isnot(None))
            ).all()
            
            for content in contents:
                repair_stats['content_items_checked'] += 1
                updated = False
                
                # Fix missing/corrupted image files
                if content.image_filename:
                    file_path = os.path.join(self.media_directories['image'], content.image_filename)
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        logger.info(f"Fixing broken image reference for Bot {content.bot_id} Day {content.day_number}")
                        content.image_filename = None
                        if content.media_type == 'image':
                            content.media_type = 'text'
                        updated = True
                        repair_stats['broken_references_fixed'] += 1
                        
                # Fix missing/corrupted video files
                if content.video_filename:
                    file_path = os.path.join(self.media_directories['video'], content.video_filename)
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        logger.info(f"Fixing broken video reference for Bot {content.bot_id} Day {content.day_number}")
                        content.video_filename = None
                        if content.media_type == 'video':
                            content.media_type = 'text'
                        updated = True
                        repair_stats['broken_references_fixed'] += 1
                        
                # Fix missing/corrupted audio files
                if content.audio_filename:
                    file_path = os.path.join(self.media_directories['audio'], content.audio_filename)
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        logger.info(f"Fixing broken audio reference for Bot {content.bot_id} Day {content.day_number}")
                        content.audio_filename = None
                        if content.media_type == 'audio':
                            content.media_type = 'text'
                        updated = True
                        repair_stats['broken_references_fixed'] += 1
                
                if updated:
                    try:
                        db.session.commit()
                        logger.info(f"✅ Fixed media references for Bot {content.bot_id} Day {content.day_number}")
                    except Exception as e:
                        db.session.rollback()
                        repair_stats['errors'] += 1
                        logger.error(f"❌ Error fixing content for Bot {content.bot_id} Day {content.day_number}: {e}")
            
            return repair_stats
            
        except Exception as e:
            logger.error(f"Error repairing media integrity: {e}")
            return {'content_items_checked': 0, 'broken_references_fixed': 0, 'files_cleaned': 0, 'errors': 1}
    
    def cleanup_orphaned_files(self, bot_id: Optional[int] = None) -> Dict[str, int]:
        """
        Clean up orphaned media files that are no longer referenced in database
        
        Args:
            bot_id: Optional bot ID to filter cleanup (None for all bots)
            
        Returns:
            Cleanup statistics
        """
        try:
            from models import Content
            
            cleanup_stats = {
                'files_scanned': 0,
                'files_removed': 0,
                'bytes_freed': 0,
                'errors': 0
            }
            
            # Get all referenced filenames from database
            query = Content.query
            if bot_id:
                query = query.filter_by(bot_id=bot_id)
            
            contents = query.all()
            referenced_files = set()
            
            for content in contents:
                if content.image_filename:
                    referenced_files.add(('image', content.image_filename))
                if content.video_filename:
                    referenced_files.add(('video', content.video_filename))
                if content.audio_filename:
                    referenced_files.add(('audio', content.audio_filename))
            
            logger.info(f"Found {len(referenced_files)} referenced files in database")
            
            # Scan each media directory for orphaned files
            for media_type, directory in self.media_directories.items():
                if os.path.exists(directory):
                    for filename in os.listdir(directory):
                        file_path = os.path.join(directory, filename)
                        if os.path.isfile(file_path):
                            cleanup_stats['files_scanned'] += 1
                            
                            # Check if file is referenced in database
                            if (media_type, filename) not in referenced_files:
                                # Additional check: if bot_id specified, only remove bot-specific files
                                if bot_id and not filename.startswith(f'bot{bot_id}_'):
                                    continue
                                    
                                try:
                                    file_size = os.path.getsize(file_path)
                                    os.remove(file_path)
                                    cleanup_stats['files_removed'] += 1
                                    cleanup_stats['bytes_freed'] += file_size
                                    logger.info(f"Removed orphaned {media_type} file: {filename}")
                                except Exception as e:
                                    cleanup_stats['errors'] += 1
                                    logger.error(f"Error removing orphaned file {filename}: {e}")
            
            logger.info(f"Cleanup completed: {cleanup_stats['files_removed']} files removed, {cleanup_stats['bytes_freed']} bytes freed")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Error cleaning up orphaned files: {e}")
            return {'files_scanned': 0, 'files_removed': 0, 'bytes_freed': 0, 'errors': 1}
    
    def generate_integrity_report(self, bot_id: Optional[int] = None) -> str:
        """Generate comprehensive media integrity report"""
        try:
            validation = self.validate_content_media_integrity(bot_id)
            
            report_lines = []
            report_lines.append("=" * 70)
            report_lines.append("MEDIA INTEGRITY REPORT")
            report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report_lines.append(f"Scope: {'Bot ' + str(bot_id) if bot_id else 'All Bots'}")
            report_lines.append("=" * 70)
            
            # Summary
            summary = validation['summary']
            report_lines.append(f"\n📊 SUMMARY:")
            report_lines.append(f"  Content Items: {summary.get('total_content_items', 0)}")
            report_lines.append(f"  Valid Files: {summary.get('valid_files', 0)}")
            report_lines.append(f"  Missing Files: {summary.get('missing_files', 0)}")
            report_lines.append(f"  Corrupted Files: {summary.get('corrupted_files', 0)}")
            report_lines.append(f"  Bots Affected: {summary.get('bots_affected', 0)}")
            report_lines.append(f"  Integrity Score: {summary.get('integrity_score', 0)}%")
            
            # Status indicator
            integrity_score = summary.get('integrity_score', 0)
            if integrity_score >= 95:
                status = "🟢 EXCELLENT"
            elif integrity_score >= 80:
                status = "🟡 GOOD"
            elif integrity_score >= 60:
                status = "🟠 NEEDS ATTENTION"
            else:
                status = "🔴 CRITICAL"
            
            report_lines.append(f"  Overall Status: {status}")
            
            # Valid media (show first few)
            if validation['valid_media']:
                report_lines.append(f"\n✅ VALID MEDIA ({len(validation['valid_media'])}):")
                for item in validation['valid_media'][:5]:
                    report_lines.append(f"  {item}")
                if len(validation['valid_media']) > 5:
                    report_lines.append(f"  ... and {len(validation['valid_media']) - 5} more")
            
            # Missing media
            if validation['missing_media']:
                report_lines.append(f"\n❌ MISSING MEDIA ({len(validation['missing_media'])}):")
                for item in validation['missing_media'][:10]:
                    report_lines.append(f"  {item}")
                if len(validation['missing_media']) > 10:
                    report_lines.append(f"  ... and {len(validation['missing_media']) - 10} more")
            
            # Corrupted media
            if validation['corrupted_references']:
                report_lines.append(f"\n⚠️  CORRUPTED MEDIA ({len(validation['corrupted_references'])}):")
                for item in validation['corrupted_references'][:10]:
                    report_lines.append(f"  {item}")
                if len(validation['corrupted_references']) > 10:
                    report_lines.append(f"  ... and {len(validation['corrupted_references']) - 10} more")
            
            # Recommendations
            report_lines.append(f"\n💡 RECOMMENDATIONS:")
            if validation['missing_media']:
                report_lines.append("  - Run media integrity repair to fix broken references")
            if validation['corrupted_references']:
                report_lines.append("  - Check file permissions and disk space")
            if not validation['missing_media'] and not validation['corrupted_references']:
                report_lines.append("  - System is healthy, no action required")
            
            report_lines.append("  - Schedule regular integrity checks")
            report_lines.append("  - Monitor file upload processes")
            
            report_lines.append("\n" + "=" * 70)
            
            return "\n".join(report_lines)
            
        except Exception as e:
            return f"Error generating integrity report: {e}"

# Global service instance
media_integrity = MediaIntegrityService()

def validate_media_integrity(bot_id=None):
    """Convenience function to validate media integrity"""
    return media_integrity.validate_content_media_integrity(bot_id)

def repair_media_integrity(bot_id=None, auto_fix=True):
    """Convenience function to repair media integrity"""
    return media_integrity.repair_media_integrity(bot_id, auto_fix)

def cleanup_orphaned_files(bot_id=None):
    """Convenience function to cleanup orphaned files"""
    return media_integrity.cleanup_orphaned_files(bot_id)

def generate_integrity_report(bot_id=None):
    """Convenience function to generate integrity report"""
    return media_integrity.generate_integrity_report(bot_id)

if __name__ == "__main__":
    print("🔍 Starting Media Integrity Service...")
    print()
    
    # Generate and display integrity report
    report = generate_integrity_report()
    print(report)
    
    # Run repairs if needed
    print("\n🔧 Running integrity repairs...")
    repair_stats = repair_media_integrity(auto_fix=True)
    print(f"Fixed: {repair_stats['broken_references_fixed']}")
    print(f"Errors: {repair_stats['errors']}")
    
    print("\n✅ Media integrity service completed!")