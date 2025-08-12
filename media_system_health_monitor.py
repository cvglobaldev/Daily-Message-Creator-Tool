#!/usr/bin/env python3
"""
Media System Health Monitor
==========================

Comprehensive monitoring and reporting tool for the Universal Media Prevention System.
Provides real-time health checks, integrity reports, and proactive monitoring for all bots.

Usage:
    python3 media_system_health_monitor.py --check-all
    python3 media_system_health_monitor.py --bot 2
    python3 media_system_health_monitor.py --repair --auto-fix
    python3 media_system_health_monitor.py --monitor --interval 15

Author: AI Assistant
Date: August 12, 2025
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_flask_context():
    """Setup Flask application context"""
    try:
        from main import app
        return app
    except Exception as e:
        logger.error(f"Failed to setup Flask context: {e}")
        return None

def check_bot_health(bot_id: Optional[int] = None) -> Dict[str, Any]:
    """Check health of specific bot or all bots"""
    app = setup_flask_context()
    if not app:
        return {'error': 'Failed to setup Flask context'}
    
    with app.app_context():
        try:
            from universal_media_prevention_system import run_integrity_check_for_bot, run_system_wide_check
            
            if bot_id:
                print(f"🔍 Checking Bot {bot_id} Health...")
                result = run_integrity_check_for_bot(bot_id)
            else:
                print("🔍 Checking System-Wide Health...")
                result = run_system_wide_check()
            
            return result
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'error': str(e)}

def generate_health_report(bot_id: Optional[int] = None) -> str:
    """Generate comprehensive health report"""
    health_data = check_bot_health(bot_id)
    
    if 'error' in health_data:
        return f"❌ Health Report Failed: {health_data['error']}"
    
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("MEDIA SYSTEM HEALTH REPORT")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Scope: {'Bot ' + str(bot_id) if bot_id else 'All Bots'}")
    report_lines.append("=" * 70)
    
    if bot_id:
        # Bot-specific report
        integrity_score = health_data.get('integrity_score', 0)
        valid_refs = health_data.get('valid_references', 0)
        broken_refs = health_data.get('broken_references', 0)
        total_refs = valid_refs + broken_refs
        
        report_lines.append(f"\n📊 BOT {bot_id} SUMMARY:")
        report_lines.append(f"  Total References: {total_refs}")
        report_lines.append(f"  Valid References: {valid_refs}")
        report_lines.append(f"  Broken References: {broken_refs}")
        report_lines.append(f"  Integrity Score: {integrity_score}%")
        
        # Status indicator
        if integrity_score >= 95:
            status = "🟢 EXCELLENT"
        elif integrity_score >= 80:
            status = "🟡 GOOD"
        elif integrity_score >= 60:
            status = "🟠 NEEDS ATTENTION"
        else:
            status = "🔴 CRITICAL"
        
        report_lines.append(f"  Status: {status}")
        
        # Details
        details = health_data.get('details', [])
        if details:
            report_lines.append(f"\n📝 DETAILS:")
            for detail in details[:10]:  # Show first 10
                report_lines.append(f"  {detail}")
            if len(details) > 10:
                report_lines.append(f"  ... and {len(details) - 10} more")
    
    else:
        # System-wide report
        summary = health_data.get('summary', {})
        integrity_score = summary.get('integrity_score', 0)
        
        report_lines.append(f"\n📊 SYSTEM SUMMARY:")
        report_lines.append(f"  Content Items: {summary.get('total_content_items', 0)}")
        report_lines.append(f"  Valid Files: {summary.get('valid_files', 0)}")
        report_lines.append(f"  Missing Files: {summary.get('missing_files', 0)}")
        report_lines.append(f"  Corrupted Files: {summary.get('corrupted_files', 0)}")
        report_lines.append(f"  Bots Affected: {summary.get('bots_affected', 0)}")
        report_lines.append(f"  Overall Integrity: {integrity_score}%")
        
        # System status
        if integrity_score >= 95:
            status = "🟢 SYSTEM HEALTHY"
        elif integrity_score >= 80:
            status = "🟡 MINOR ISSUES"
        elif integrity_score >= 60:
            status = "🟠 SIGNIFICANT ISSUES"
        else:
            status = "🔴 SYSTEM CRITICAL"
        
        report_lines.append(f"  Status: {status}")
    
    # Recommendations
    report_lines.append(f"\n💡 RECOMMENDATIONS:")
    if bot_id:
        if broken_refs > 0:
            report_lines.append("  - Run repair command to fix broken references")
        else:
            report_lines.append("  - Bot is healthy, continue monitoring")
    else:
        missing_files = summary.get('missing_files', 0)
        if missing_files > 0:
            report_lines.append("  - Run system-wide repair to fix broken references")
        if integrity_score < 95:
            report_lines.append("  - Review upload processes and file storage")
        if integrity_score >= 95:
            report_lines.append("  - System is healthy, maintain current practices")
    
    report_lines.append("  - Schedule regular health checks")
    report_lines.append("  - Monitor file upload success rates")
    report_lines.append("\n" + "=" * 70)
    
    return "\n".join(report_lines)

def repair_system(auto_fix: bool = False, bot_id: Optional[int] = None) -> Dict[str, Any]:
    """Repair system issues"""
    app = setup_flask_context()
    if not app:
        return {'error': 'Failed to setup Flask context'}
    
    with app.app_context():
        try:
            from media_integrity_service import repair_media_integrity
            
            print(f"🔧 Repairing {'Bot ' + str(bot_id) if bot_id else 'All Bots'}...")
            repair_stats = repair_media_integrity(bot_id=bot_id, auto_fix=auto_fix)
            
            print(f"Repair Results:")
            print(f"- Items Checked: {repair_stats.get('content_items_checked', 0)}")
            print(f"- References Fixed: {repair_stats.get('broken_references_fixed', 0)}")
            print(f"- Errors: {repair_stats.get('errors', 0)}")
            
            return repair_stats
            
        except Exception as e:
            logger.error(f"Repair failed: {e}")
            return {'error': str(e)}

def monitor_system(interval_minutes: int = 30):
    """Start continuous monitoring"""
    print(f"🔄 Starting continuous monitoring (interval: {interval_minutes} minutes)")
    print("Press Ctrl+C to stop")
    
    try:
        import time
        while True:
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Running health check...")
            
            # Generate and display report
            report = generate_health_report()
            print(report)
            
            # Wait for next check
            print(f"⏳ Next check in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Media System Health Monitor")
    parser.add_argument('--check-all', action='store_true', help='Check all bots health')
    parser.add_argument('--bot', type=int, help='Check specific bot health')
    parser.add_argument('--repair', action='store_true', help='Repair system issues')
    parser.add_argument('--auto-fix', action='store_true', help='Enable auto-fix during repair')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in minutes')
    parser.add_argument('--report', action='store_true', help='Generate health report')
    
    args = parser.parse_args()
    
    if args.check_all or args.report:
        print(generate_health_report())
    
    elif args.bot:
        print(generate_health_report(args.bot))
    
    elif args.repair:
        repair_system(auto_fix=args.auto_fix, bot_id=args.bot)
    
    elif args.monitor:
        monitor_system(args.interval)
    
    else:
        # Default: show system health
        print(generate_health_report())

if __name__ == "__main__":
    main()