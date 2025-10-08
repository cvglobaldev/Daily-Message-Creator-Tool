
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from models import db, User, MessageLog, Content, Bot
from sqlalchemy import func, desc, and_

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for analytics data processing"""
    
    def get_user_journey_analytics(self, bot_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get user journey analytics data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query with bot filter
            query = User.query.filter(User.join_date >= cutoff_date)
            if bot_id:
                query = query.filter(User.bot_id == bot_id)
            
            # Get bot's journey duration
            journey_duration = 30  # default
            if bot_id:
                bot = Bot.query.get(bot_id)
                if bot:
                    journey_duration = bot.journey_duration_days
            
            # Journey Completion Funnel
            funnel_labels = [f"Day 1-10", f"Day 11-20", f"Day 21-30"]
            if journey_duration > 30:
                funnel_labels.extend([f"Day {i}-{min(i+9, journey_duration)}" for i in range(31, journey_duration, 10)])
            
            funnel_values = []
            for i, label in enumerate(funnel_labels):
                start_day = i * 10 + 1
                end_day = min((i + 1) * 10, journey_duration)
                count = query.filter(User.current_day >= start_day, User.current_day <= end_day).count()
                funnel_values.append(count)
            
            # Drop-off Rate by Day
            dropoff_days = list(range(1, min(journey_duration + 1, 31)))  # Show first 30 days
            dropoff_rates = []
            total_started = query.count()
            
            for day in dropoff_days:
                users_at_day = query.filter(User.current_day >= day).count()
                dropoff_rate = ((total_started - users_at_day) / total_started * 100) if total_started > 0 else 0
                dropoff_rates.append(round(dropoff_rate, 1))
            
            # Average Days to Completion
            completed_users = query.filter(User.status == 'completed').all()
            avg_days = 0
            if completed_users:
                total_days = sum([(u.completion_date - u.join_date).days for u in completed_users if u.completion_date])
                avg_days = total_days / len(completed_users) if completed_users else 0
            
            return {
                'funnel': {
                    'labels': funnel_labels,
                    'values': funnel_values
                },
                'dropoff': {
                    'days': dropoff_days,
                    'rates': dropoff_rates
                },
                'avg_days_to_completion': avg_days
            }
            
        except Exception as e:
            logger.error(f"Error getting user journey analytics: {e}")
            return {'funnel': {'labels': [], 'values': []}, 'dropoff': {'days': [], 'rates': []}, 'avg_days_to_completion': 0}
    
    def get_faith_journey_insights(self, bot_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get faith journey insights data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Base query with bot filter
            user_query = User.query.filter(User.join_date >= cutoff_date)
            if bot_id:
                user_query = user_query.filter(User.bot_id == bot_id)
            
            # Total Users
            total_users = user_query.count()
            
            # Total Faith Journeys (count of tags across all messages)
            message_query = MessageLog.query.join(User).filter(MessageLog.timestamp >= cutoff_date)
            if bot_id:
                message_query = message_query.filter(User.bot_id == bot_id)
            
            total_faith_journeys = message_query.filter(MessageLog.llm_tags.isnot(None)).count()
            
            # Completion Rate
            completed_users = user_query.filter(User.status == 'completed').count()
            completion_rate = (completed_users / total_users * 100) if total_users > 0 else 0
            
            # Average Journey Day
            avg_journey_day = db.session.query(func.avg(User.current_day)).filter(
                User.join_date >= cutoff_date
            )
            if bot_id:
                avg_journey_day = avg_journey_day.filter(User.bot_id == bot_id)
            avg_journey_day = avg_journey_day.scalar() or 0
            
            # Tag Distribution
            faith_tags = ['Introduction to Jesus (ITJ)', 'Bible Exposure', 'Bible Engagement', 
                         'Christian Learning', 'Gospel Presentation', 'Holy Spirit Empowerment', 
                         'Prayer', 'Salvation']
            
            tag_counts = {}
            tag_labels = []
            tag_values = []
            
            for tag in faith_tags:
                count = message_query.filter(MessageLog.llm_tags.contains([tag])).count()
                if count > 0:
                    tag_counts[tag] = count
                    tag_labels.append(tag)
                    tag_values.append(count)
            
            # Tag Stats with percentages
            total_tags = sum(tag_values)
            tag_stats = []
            for tag, count in tag_counts.items():
                percentage = (count / total_tags * 100) if total_tags > 0 else 0
                tag_stats.append({
                    'tag': tag,
                    'count': count,
                    'percentage': percentage
                })
            
            # Tag Timeline (when users receive tags by journey day)
            tag_timeline_data = {}
            journey_days = list(range(1, 31))  # First 30 days
            
            for tag in faith_tags:
                day_counts = []
                for day in journey_days:
                    count = db.session.query(func.count(MessageLog.id)).join(User).filter(
                        User.current_day == day,
                        MessageLog.llm_tags.contains([tag]),
                        MessageLog.timestamp >= cutoff_date
                    )
                    if bot_id:
                        count = count.filter(User.bot_id == bot_id)
                    day_counts.append(count.scalar() or 0)
                
                if sum(day_counts) > 0:  # Only include tags with data
                    tag_timeline_data[tag] = day_counts
            
            return {
                'total_users': total_users,
                'total_faith_journeys': total_faith_journeys,
                'completion_rate': completion_rate,
                'avg_journey_day': avg_journey_day,
                'tag_distribution': {
                    'labels': tag_labels,
                    'values': tag_values
                },
                'tag_stats': tag_stats,
                'tag_timeline': {
                    'days': journey_days,
                    'tags': list(tag_timeline_data.keys()),
                    'data': tag_timeline_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting faith journey insights: {e}")
            return {
                'total_users': 0,
                'total_faith_journeys': 0,
                'completion_rate': 0,
                'avg_journey_day': 0,
                'tag_distribution': {'labels': [], 'values': []},
                'tag_stats': [],
                'tag_timeline': {'days': [], 'tags': [], 'data': {}}
            }
