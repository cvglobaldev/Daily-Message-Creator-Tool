"""
Media File Browser for CMS
=========================

Provides functionality to browse and select previously uploaded media files
for reuse in content management system. Supports filtering by bot, media type,
and file attributes.

Author: AI Assistant
Date: August 12, 2025
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

class MediaFileBrowser:
    """Browse and manage previously uploaded media files"""
    
    def __init__(self, upload_folder: str = 'static/uploads'):
        self.upload_folder = upload_folder
        self.media_types = {
            'image': {
                'folder': 'images',
                'extensions': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
                'display_name': 'Images'
            },
            'video': {
                'folder': 'videos',
                'extensions': ['mp4', 'mov', 'avi', 'mkv'],
                'display_name': 'Videos'
            },
            'audio': {
                'folder': 'audio',
                'extensions': ['mp3', 'wav', 'ogg', 'm4a', 'aac'],
                'display_name': 'Audio'
            }
        }
    
    def get_available_files(self, media_type: Optional[str] = None, bot_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get list of available media files with metadata"""
        available_files = []
        
        # Determine which media types to scan
        types_to_scan = [media_type] if media_type else list(self.media_types.keys())
        
        for mtype in types_to_scan:
            if mtype not in self.media_types:
                continue
                
            config = self.media_types[mtype]
            folder_path = os.path.join(self.upload_folder, config['folder'])
            
            if not os.path.exists(folder_path):
                continue
            
            try:
                for filename in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, filename)
                    
                    # Skip directories and non-files
                    if not os.path.isfile(file_path):
                        continue
                    
                    # Check file extension
                    if '.' not in filename:
                        continue
                    
                    extension = filename.lower().split('.')[-1]
                    if extension not in config['extensions']:
                        continue
                    
                    # Extract bot ID from filename if bot filtering requested
                    file_bot_id = self._extract_bot_id_from_filename(filename)
                    if bot_id is not None and file_bot_id != bot_id:
                        continue
                    
                    # Get file metadata
                    try:
                        stat = os.stat(file_path)
                        file_info = {
                            'filename': filename,
                            'display_name': self._get_display_name(filename),
                            'media_type': mtype,
                            'bot_id': file_bot_id,
                            'size': stat.st_size,
                            'size_display': self._format_file_size(stat.st_size),
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'modified_display': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                            'extension': extension,
                            'url': f"/static/uploads/{config['folder']}/{filename}",
                            'relative_path': os.path.join(config['folder'], filename)
                        }
                        available_files.append(file_info)
                        
                    except Exception as e:
                        logger.warning(f"Could not get metadata for {filename}: {e}")
                        
            except Exception as e:
                logger.error(f"Error scanning {folder_path}: {e}")
        
        # Sort by modification date (newest first)
        available_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return available_files
    
    def _extract_bot_id_from_filename(self, filename: str) -> Optional[int]:
        """Extract bot ID from filename (e.g., bot2_xxx -> 2)"""
        try:
            if filename.startswith('bot') and '_' in filename:
                bot_part = filename.split('_')[0]
                if bot_part.startswith('bot') and bot_part[3:].isdigit():
                    return int(bot_part[3:])
        except:
            pass
        return None
    
    def _get_display_name(self, filename: str) -> str:
        """Generate user-friendly display name from filename"""
        try:
            # Remove bot prefix if present
            display_name = filename
            if filename.startswith('bot') and '_' in filename:
                parts = filename.split('_', 2)
                if len(parts) >= 3:
                    display_name = parts[2]  # Skip bot prefix and UUID
                elif len(parts) == 2:
                    display_name = parts[1]
            
            # Remove file extension
            if '.' in display_name:
                display_name = '.'.join(display_name.split('.')[:-1])
            
            # Replace underscores and hyphens with spaces
            display_name = display_name.replace('_', ' ').replace('-', ' ')
            
            # Capitalize first letter of each word
            display_name = ' '.join(word.capitalize() for word in display_name.split())
            
            return display_name or filename
            
        except:
            return filename
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size for display"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def get_files_for_bot(self, bot_id: int, media_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get files specifically for a bot"""
        return self.get_available_files(media_type=media_type, bot_id=bot_id)
    
    def get_file_info(self, filename: str, media_type: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for specific file"""
        if media_type not in self.media_types:
            return None
        
        config = self.media_types[media_type]
        file_path = os.path.join(self.upload_folder, config['folder'], filename)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            stat = os.stat(file_path)
            return {
                'filename': filename,
                'display_name': self._get_display_name(filename),
                'media_type': media_type,
                'bot_id': self._extract_bot_id_from_filename(filename),
                'size': stat.st_size,
                'size_display': self._format_file_size(stat.st_size),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'modified_display': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'url': f"/static/uploads/{config['folder']}/{filename}",
                'full_path': file_path
            }
        except:
            return None
    
    def validate_file_exists(self, filename: str, media_type: str) -> bool:
        """Validate that a file exists and is accessible"""
        if not filename or media_type not in self.media_types:
            return False
        
        config = self.media_types[media_type]
        file_path = os.path.join(self.upload_folder, config['folder'], filename)
        
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for media files"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'by_type': {},
            'by_bot': {},
            'recent_uploads': []
        }
        
        all_files = self.get_available_files()
        
        for file_info in all_files:
            stats['total_files'] += 1
            stats['total_size'] += file_info['size']
            
            # By type
            mtype = file_info['media_type']
            if mtype not in stats['by_type']:
                stats['by_type'][mtype] = {'count': 0, 'size': 0}
            stats['by_type'][mtype]['count'] += 1
            stats['by_type'][mtype]['size'] += file_info['size']
            
            # By bot
            bot_id = file_info.get('bot_id', 'unknown')
            if bot_id not in stats['by_bot']:
                stats['by_bot'][bot_id] = {'count': 0, 'size': 0}
            stats['by_bot'][bot_id]['count'] += 1
            stats['by_bot'][bot_id]['size'] += file_info['size']
        
        # Recent uploads (last 10)
        stats['recent_uploads'] = all_files[:10]
        
        # Format total size
        stats['total_size_display'] = self._format_file_size(stats['total_size'])
        
        return stats

# Global browser instance
media_browser = MediaFileBrowser()

def get_available_media_files(media_type: Optional[str] = None, bot_id: Optional[int] = None):
    """Get available media files for selection"""
    return media_browser.get_available_files(media_type=media_type, bot_id=bot_id)

def validate_media_file_exists(filename: str, media_type: str):
    """Validate media file exists"""
    return media_browser.validate_file_exists(filename, media_type)

if __name__ == "__main__":
    # Test the browser
    browser = MediaFileBrowser()
    
    print("📁 Media File Browser Test")
    print("=" * 40)
    
    # Get all files
    all_files = browser.get_available_files()
    print(f"Total files found: {len(all_files)}")
    
    # Show files by type
    for media_type in ['image', 'video', 'audio']:
        files = browser.get_available_files(media_type=media_type)
        print(f"{media_type.capitalize()} files: {len(files)}")
        
        for file_info in files[:3]:  # Show first 3
            print(f"  - {file_info['display_name']} ({file_info['size_display']})")
    
    # Usage stats
    stats = browser.get_usage_stats()
    print(f"\nTotal storage used: {stats['total_size_display']}")
    print("Files by bot:", {k: v['count'] for k, v in stats['by_bot'].items()})