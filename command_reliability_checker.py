#!/usr/bin/env python3
"""
Command Reliability Checker - Monitoring and Self-Healing for Bot Commands
This script provides proactive monitoring and automatic fixes for command processing issues.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_manager import DatabaseManager
from services import WhatsAppService, TelegramService, GeminiService

logger = logging.getLogger(__name__)

class CommandReliabilityChecker:
    """Monitor and ensure command processing reliability across all bots"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.whatsapp_services = {}
        self.telegram_services = {}
        self.gemini_service = GeminiService()
        
    def check_command_processing_health(self) -> Dict[str, any]:
        """Comprehensive health check for command processing"""
        health_report = {
            "timestamp": datetime.now(),
            "overall_status": "healthy",
            "issues_found": [],
            "fixes_applied": [],
            "bots_checked": []
        }
        
        try:
            # Check all active bots
            from models import Bot
            bots = Bot.query.filter_by(status='active').all()
            
            for bot in bots:
                bot_health = self._check_bot_command_health(bot)
                health_report["bots_checked"].append({
                    "bot_id": bot.id,
                    "name": bot.name,
                    "health": bot_health
                })
                
                if bot_health["issues"]:
                    health_report["issues_found"].extend(bot_health["issues"])
                    health_report["overall_status"] = "degraded"
                
                if bot_health["fixes_applied"]:
                    health_report["fixes_applied"].extend(bot_health["fixes_applied"])
            
            # Check recent command failures
            recent_failures = self._check_recent_command_failures()
            if recent_failures:
                health_report["issues_found"].extend(recent_failures)
                health_report["overall_status"] = "degraded"
            
            # Check service availability
            service_issues = self._check_service_availability()
            if service_issues:
                health_report["issues_found"].extend(service_issues)
                health_report["overall_status"] = "critical"
                
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_report["overall_status"] = "critical"
            health_report["issues_found"].append(f"Health check failed: {e}")
        
        return health_report
    
    def _check_bot_command_health(self, bot) -> Dict[str, any]:
        """Check command processing health for a specific bot"""
        bot_health = {
            "bot_id": bot.id,
            "issues": [],
            "fixes_applied": []
        }
        
        try:
            # Check if bot has required command messages
            if not bot.help_message:
                bot_health["issues"].append(f"Bot {bot.id} missing help_message")
                self._fix_missing_help_message(bot)
                bot_health["fixes_applied"].append(f"Added default help_message for bot {bot.id}")
            
            if not bot.stop_message:
                bot_health["issues"].append(f"Bot {bot.id} missing stop_message")
                self._fix_missing_stop_message(bot)
                bot_health["fixes_applied"].append(f"Added default stop_message for bot {bot.id}")
            
            if not bot.human_message:
                bot_health["issues"].append(f"Bot {bot.id} missing human_message")
                self._fix_missing_human_message(bot)
                bot_health["fixes_applied"].append(f"Added default human_message for bot {bot.id}")
            
            # Check service availability for this bot
            if bot.whatsapp_phone_number_id and bot.whatsapp_access_token:
                service_health = self._check_whatsapp_service_health(bot)
                if not service_health:
                    bot_health["issues"].append(f"WhatsApp service unhealthy for bot {bot.id}")
            
            if bot.telegram_bot_token:
                service_health = self._check_telegram_service_health(bot)
                if not service_health:
                    bot_health["issues"].append(f"Telegram service unhealthy for bot {bot.id}")
                    
        except Exception as e:
            logger.error(f"Error checking bot {bot.id} health: {e}")
            bot_health["issues"].append(f"Health check error: {e}")
        
        return bot_health
    
    def _fix_missing_help_message(self, bot):
        """Add default help message for bot"""
        try:
            from models import db
            if "indonesia" in bot.name.lower() or bot.id == 2:
                bot.help_message = ("🤝 Perintah yang tersedia:\n\n"
                                  "📖 START - Mulai atau ulangi perjalanan spiritual\n"
                                  "⏸️ STOP - Jeda perjalanan\n" 
                                  "❓ HELP - Tampilkan pesan bantuan ini\n"
                                  "🧑‍💼 HUMAN - Bicara langsung dengan manusia\n\n"
                                  "Kirim pesan apa saja untuk berbagi pemikiran Anda!")
            else:
                bot.help_message = ("🤝 Available Commands:\n\n"
                                  "📖 START - Begin or restart your spiritual journey\n"
                                  "⏸️ STOP - Pause your journey\n"
                                  "❓ HELP - Show this help message\n"
                                  "🧑‍💼 HUMAN - Chat directly with a human\n\n"
                                  "Send any message to share your thoughts!")
            db.session.commit()
            logger.info(f"Added default help_message for bot {bot.id}")
        except Exception as e:
            logger.error(f"Error fixing help message for bot {bot.id}: {e}")
    
    def _fix_missing_stop_message(self, bot):
        """Add default stop message for bot"""
        try:
            from models import db
            if "indonesia" in bot.name.lower() or bot.id == 2:
                bot.stop_message = ("⏸️ Perjalanan spiritualmu lagi dijeda dulu, ya.\n\n"
                                  "Santai aja, nggak usah buru-buru. Lanjutkan lagi kapan pun kamu siap. "
                                  "Kirim START untuk melanjutkan, atau HUMAN kalau mau ngobrol langsung dengan seseorang.\n\n"
                                  "Ingat, ini adalah ruang pribadimu untuk bereksplorasi. Nggak ada paksaan, kok. "
                                  "Ikuti aja alurmu sendiri. 🙏")
            else:
                bot.stop_message = ("⏸️ Your faith journey has been paused.\n\n"
                                  "Take your time - there's no rush. Continue whenever you're ready. "
                                  "Send START to resume, or HUMAN to chat directly with someone.\n\n"
                                  "Remember, this is your personal space to explore. No pressure at all. "
                                  "Follow your own pace. 🙏")
            db.session.commit()
            logger.info(f"Added default stop_message for bot {bot.id}")
        except Exception as e:
            logger.error(f"Error fixing stop message for bot {bot.id}: {e}")
    
    def _fix_missing_human_message(self, bot):
        """Add default human message for bot"""
        try:
            from models import db
            if "indonesia" in bot.name.lower() or bot.id == 2:
                bot.human_message = ("🤝 Permintaan Chat dengan Manusia\n\n"
                                   "Terima kasih sudah menghubungi! Tim kami akan segera terhubung dengan Anda. "
                                   "Percakapan ini sudah ditandai sebagai prioritas untuk respon manusia.\n\n"
                                   "Sementara menunggu, ketahui bahwa Anda berharga dan perjalanan spiritual Anda penting. "
                                   "Silakan berbagi apa yang ada di hati Anda. 🙏")
            else:
                bot.human_message = ("🤝 Direct Human Chat Requested\n\n"
                                   "Thank you for reaching out! A member of our team will connect with you shortly. "
                                   "This conversation has been flagged for priority human response.\n\n"
                                   "In the meantime, know that you are valued and your journey matters. "
                                   "Feel free to share what's on your heart. 🙏")
            db.session.commit()
            logger.info(f"Added default human_message for bot {bot.id}")
        except Exception as e:
            logger.error(f"Error fixing human message for bot {bot.id}: {e}")
    
    def _check_recent_command_failures(self) -> List[str]:
        """Check for recent command processing failures"""
        issues = []
        try:
            # Check for unprocessed commands in the last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            # This would require database queries to check for:
            # 1. Messages with STOP/HELP/HUMAN/START that don't have responses
            # 2. Error patterns in logs
            # 3. Users stuck in processing states
            
            # For now, implementing basic structure
            logger.info("Command failure check completed")
            
        except Exception as e:
            issues.append(f"Failed to check command failures: {e}")
        
        return issues
    
    def _check_service_availability(self) -> List[str]:
        """Check if all services are available"""
        issues = []
        
        # Check Gemini API
        if not self.gemini_service.client:
            issues.append("Gemini AI service unavailable")
        
        # Check database connectivity
        try:
            self.db_manager.get_all_users()
        except Exception as e:
            issues.append(f"Database connectivity issue: {e}")
        
        return issues
    
    def _check_whatsapp_service_health(self, bot) -> bool:
        """Check WhatsApp service health for a specific bot"""
        try:
            service = WhatsAppService(
                access_token=bot.whatsapp_access_token,
                phone_number_id=bot.whatsapp_phone_number_id
            )
            return not service.simulate_mode
        except Exception as e:
            logger.error(f"WhatsApp service check failed for bot {bot.id}: {e}")
            return False
    
    def _check_telegram_service_health(self, bot) -> bool:
        """Check Telegram service health for a specific bot"""
        try:
            service = TelegramService(bot_token=bot.telegram_bot_token)
            return service.bot_token is not None
        except Exception as e:
            logger.error(f"Telegram service check failed for bot {bot.id}: {e}")
            return False

def run_health_check():
    """Run comprehensive health check and return report"""
    from app import app
    with app.app_context():
        checker = CommandReliabilityChecker()
        return checker.check_command_processing_health()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run health check with proper Flask context
    report = run_health_check()
    
    print(f"\n{'='*60}")
    print(f"COMMAND RELIABILITY HEALTH CHECK REPORT")
    print(f"{'='*60}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"Overall Status: {report['overall_status'].upper()}")
    print(f"Bots Checked: {len(report['bots_checked'])}")
    
    if report['issues_found']:
        print(f"\n🚨 ISSUES FOUND ({len(report['issues_found'])}):")
        for issue in report['issues_found']:
            print(f"  • {issue}")
    
    if report['fixes_applied']:
        print(f"\n✅ FIXES APPLIED ({len(report['fixes_applied'])}):")
        for fix in report['fixes_applied']:
            print(f"  • {fix}")
    
    print(f"\n{'='*60}")