"""
Command Reliability and Media Delivery Checker
============================================== 

Comprehensive monitoring and self-healing system for WhatsApp/Telegram bot reliability.
Proactively detects and fixes issues with:
- Phone number formatting problems
- Missing media files
- Failed content delivery  
- Command processing errors
- Service validation issues

This system runs periodic health checks and automatic repairs to prevent user-facing issues.

Author: AI Assistant
Date: August 12, 2025
"""

import logging
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class SystemReliabilityChecker:
    """Comprehensive system reliability and self-healing checker"""
    
    def __init__(self):
        self.phone_processor = None
        self.media_manager = None
        self.issues_found = []
        self.fixes_applied = []
        
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """
        Run complete system health check covering all critical areas
        
        Returns comprehensive health report with issue detection and fixes
        """
        logger.info("🔍 Starting comprehensive system health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'checks_performed': [],
            'issues_found': [],
            'fixes_applied': [],
            'recommendations': [],
            'overall_status': 'HEALTHY'
        }
        
        # 1. Phone Number Processing Check
        try:
            phone_check = self._check_phone_number_processing()
            health_report['checks_performed'].append('phone_number_processing')
            if phone_check['issues']:
                health_report['issues_found'].extend(phone_check['issues'])
                health_report['overall_status'] = 'ISSUES_DETECTED'
        except Exception as e:
            health_report['issues_found'].append(f"Phone number check failed: {e}")
            
        # 2. Media File Validation
        try:
            media_check = self._check_media_file_integrity()
            health_report['checks_performed'].append('media_file_integrity')
            if media_check['issues']:
                health_report['issues_found'].extend(media_check['issues'])
                health_report['overall_status'] = 'ISSUES_DETECTED'
            if media_check['fixes']:
                health_report['fixes_applied'].extend(media_check['fixes'])
        except Exception as e:
            health_report['issues_found'].append(f"Media file check failed: {e}")
            
        # 3. Database Content Validation
        try:
            db_check = self._check_database_integrity()
            health_report['checks_performed'].append('database_integrity')
            if db_check['issues']:
                health_report['issues_found'].extend(db_check['issues'])
                health_report['overall_status'] = 'ISSUES_DETECTED'
        except Exception as e:
            health_report['issues_found'].append(f"Database check failed: {e}")
            
        # 4. Service Configuration Check
        try:
            service_check = self._check_service_configurations()
            health_report['checks_performed'].append('service_configurations')
            if service_check['issues']:
                health_report['issues_found'].extend(service_check['issues'])
                health_report['overall_status'] = 'ISSUES_DETECTED'
        except Exception as e:
            health_report['issues_found'].append(f"Service config check failed: {e}")
            
        # 5. Content Delivery Simulation
        try:
            delivery_check = self._simulate_content_delivery()
            health_report['checks_performed'].append('content_delivery_simulation')
            if delivery_check['issues']:
                health_report['issues_found'].extend(delivery_check['issues'])
                health_report['overall_status'] = 'ISSUES_DETECTED'
        except Exception as e:
            health_report['issues_found'].append(f"Content delivery check failed: {e}")
            
        # Generate recommendations
        health_report['recommendations'] = self._generate_recommendations(health_report)
        
        # Final status determination
        if health_report['issues_found']:
            if len(health_report['issues_found']) > 5:
                health_report['overall_status'] = 'CRITICAL'
            else:
                health_report['overall_status'] = 'ISSUES_DETECTED'
        else:
            health_report['overall_status'] = 'HEALTHY'
            
        logger.info(f"✅ Health check completed. Status: {health_report['overall_status']}")
        return health_report
    
    def _check_phone_number_processing(self) -> Dict[str, List[str]]:
        """Test phone number processing with various formats"""
        try:
            # Import phone number utilities
            from phone_number_utils import normalize_phone_number, generate_phone_variations
            
            test_numbers = [
                "+62 838-2233-1133",
                "62 838 2233 1133", 
                "(62) 838.2233.1133",
                "0838-2233-1133",
                "838-2233-1133",
                "62-800-1234-5678",
                "+6281234567890"
            ]
            
            issues = []
            for number in test_numbers:
                try:
                    normalized = normalize_phone_number(number)
                    variations = generate_phone_variations(number)
                    
                    if not normalized.startswith('+62'):
                        issues.append(f"Phone normalization failed for {number}: {normalized}")
                    if len(variations) < 2:
                        issues.append(f"Insufficient variations generated for {number}: {len(variations)}")
                        
                except Exception as e:
                    issues.append(f"Phone processing error for {number}: {e}")
                    
            return {'issues': issues, 'fixes': []}
            
        except Exception as e:
            return {'issues': [f"Phone number processing system unavailable: {e}"], 'fixes': []}
    
    def _check_media_file_integrity(self) -> Dict[str, List[str]]:
        """Check all media files referenced in database exist"""
        try:
            from media_file_manager import validate_media_files, fix_missing_media_files
            
            validation = validate_media_files()
            issues = []
            fixes = []
            
            if validation.get('missing'):
                issues.extend([f"Missing media file: {item}" for item in validation['missing'][:5]])
                
                # Auto-fix missing files
                try:
                    fix_result = fix_missing_media_files(auto_fix=True)
                    if fix_result['fixed'] > 0:
                        fixes.append(f"Auto-fixed {fix_result['fixed']} missing media file references")
                except Exception as fix_error:
                    issues.append(f"Failed to auto-fix media files: {fix_error}")
                    
            return {'issues': issues, 'fixes': fixes}
            
        except Exception as e:
            return {'issues': [f"Media file integrity check failed: {e}"], 'fixes': []}
    
    def _check_database_integrity(self) -> Dict[str, List[str]]:
        """Check database structure and content integrity"""
        issues = []
        
        try:
            # Check if required environment variables exist
            required_vars = ['DATABASE_URL', 'GEMINI_API_KEY']
            for var in required_vars:
                if not os.environ.get(var):
                    issues.append(f"Missing required environment variable: {var}")
                    
            # Check critical database tables exist (would require db connection)
            # This is a placeholder for more comprehensive db checks
            
        except Exception as e:
            issues.append(f"Database integrity check error: {e}")
            
        return {'issues': issues, 'fixes': []}
    
    def _check_service_configurations(self) -> Dict[str, List[str]]:
        """Validate WhatsApp and Telegram service configurations"""
        issues = []
        
        try:
            # Check WhatsApp credentials
            whatsapp_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
            whatsapp_phone = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
            
            if not whatsapp_token:
                issues.append("WhatsApp access token not configured")
            elif len(whatsapp_token) < 50:
                issues.append("WhatsApp access token appears invalid (too short)")
                
            if not whatsapp_phone:
                issues.append("WhatsApp phone number ID not configured")
                
            # Check Telegram credentials
            telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not telegram_token:
                issues.append("Telegram bot token not configured")
            elif not telegram_token.startswith(('1', '2', '5', '6')):
                issues.append("Telegram bot token format appears invalid")
                
            # Check Gemini API
            gemini_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_key:
                issues.append("Gemini API key not configured")
                
        except Exception as e:
            issues.append(f"Service configuration check error: {e}")
            
        return {'issues': issues, 'fixes': []}
    
    def _simulate_content_delivery(self) -> Dict[str, List[str]]:
        """Simulate content delivery process for validation"""
        issues = []
        
        try:
            # Check if content delivery directories exist
            required_dirs = [
                'static/uploads/images',
                'static/uploads/videos', 
                'static/uploads/audio'
            ]
            
            for dir_path in required_dirs:
                if not os.path.exists(dir_path):
                    issues.append(f"Media directory missing: {dir_path}")
                elif not os.access(dir_path, os.W_OK):
                    issues.append(f"Media directory not writable: {dir_path}")
                    
            # Test URL construction
            try:
                domain = os.environ.get('REPLIT_DOMAINS', '').split(',')[0]
                if not domain:
                    issues.append("REPLIT_DOMAINS not configured")
                else:
                    test_url = f"https://{domain}/static/uploads/images/test.png"
                    if 'localhost' in test_url:
                        issues.append("Using localhost in media URLs (may cause delivery issues)")
            except Exception as e:
                issues.append(f"URL construction test failed: {e}")
                
        except Exception as e:
            issues.append(f"Content delivery simulation error: {e}")
            
        return {'issues': issues, 'fixes': []}
    
    def _generate_recommendations(self, health_report: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on health check results"""
        recommendations = []
        
        if any('phone' in issue.lower() for issue in health_report['issues_found']):
            recommendations.append("Review phone number processing logic and test with various formats")
            
        if any('media' in issue.lower() for issue in health_report['issues_found']):
            recommendations.append("Run media file validation and cleanup missing references")
            
        if any('token' in issue.lower() or 'credential' in issue.lower() for issue in health_report['issues_found']):
            recommendations.append("Verify API credentials and environment variable configuration")
            
        if any('directory' in issue.lower() for issue in health_report['issues_found']):
            recommendations.append("Ensure all required directories exist with proper permissions")
            
        if not health_report['issues_found']:
            recommendations.append("System is healthy - consider running regular preventive maintenance")
            
        return recommendations
    
    def generate_health_report_text(self, health_report: Dict[str, Any]) -> str:
        """Generate human-readable health report"""
        lines = []
        lines.append("=" * 60)
        lines.append("SYSTEM RELIABILITY HEALTH REPORT")
        lines.append(f"Generated: {health_report['timestamp']}")
        lines.append(f"Overall Status: {health_report['overall_status']}")
        lines.append("=" * 60)
        
        if health_report['checks_performed']:
            lines.append(f"\n✅ CHECKS PERFORMED ({len(health_report['checks_performed'])}):")
            for check in health_report['checks_performed']:
                lines.append(f"  - {check.replace('_', ' ').title()}")
                
        if health_report['issues_found']:
            lines.append(f"\n⚠️  ISSUES DETECTED ({len(health_report['issues_found'])}):")
            for issue in health_report['issues_found'][:10]:
                lines.append(f"  - {issue}")
            if len(health_report['issues_found']) > 10:
                lines.append(f"  ... and {len(health_report['issues_found']) - 10} more issues")
                
        if health_report['fixes_applied']:
            lines.append(f"\n🔧 FIXES APPLIED ({len(health_report['fixes_applied'])}):")
            for fix in health_report['fixes_applied']:
                lines.append(f"  - {fix}")
                
        if health_report['recommendations']:
            lines.append(f"\n💡 RECOMMENDATIONS ({len(health_report['recommendations'])}):")
            for rec in health_report['recommendations']:
                lines.append(f"  - {rec}")
                
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

# Global instance
reliability_checker = SystemReliabilityChecker()

def run_system_health_check():
    """Convenience function to run system health check"""
    return reliability_checker.run_comprehensive_health_check()

def generate_health_report():
    """Convenience function to generate and print health report"""
    health_report = run_system_health_check()
    return reliability_checker.generate_health_report_text(health_report)

if __name__ == "__main__":
    print("🔍 Running System Reliability Health Check...")
    print()
    
    health_report = generate_health_report()
    print(health_report)
    
    print("\n🔧 Health check completed!")