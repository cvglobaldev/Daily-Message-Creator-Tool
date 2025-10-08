import logging
from typing import List, Dict, Any, Optional
from models import db, TagRule, MessageLog, User, Bot

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Rule Engine for evaluating rule-based tags with When-If-Then logic.
    
    Supports:
    - WHEN triggers: message_received, user_day_reached, sentiment_detected, tag_applied
    - IF conditions: contains_keyword, sentiment_is, user_day_is, tag_exists, 
                     user_day_greater_than, user_day_less_than
    - THEN actions: apply_tag, remove_tag
    """
    
    def __init__(self):
        """Initialize the RuleEngine"""
        logger.info("RuleEngine initialized")
    
    def evaluate_rules(self, message: MessageLog, user: User, bot: Bot) -> List[str]:
        """
        Evaluate all active rule-based TagRules and return list of tags to apply.
        
        Args:
            message: MessageLog instance with message data
            user: User instance
            bot: Bot instance
            
        Returns:
            List of tag names that should be applied based on rules
        """
        logger.info(f"🔍 Starting rule evaluation for user {user.phone_number} (message_id: {message.id})")
        
        tags_to_apply = []
        tags_to_remove = []
        
        try:
            # Load active rule-based TagRules ordered by priority (higher priority first)
            rules = TagRule.query.filter_by(
                rule_type='rule_based',
                is_active=True
            ).order_by(TagRule.priority.desc()).all()
            
            logger.info(f"📋 Found {len(rules)} active rule-based TagRules to evaluate")
            
            for rule in rules:
                logger.debug(f"📌 Evaluating rule: {rule.tag_name} (priority: {rule.priority})")
                
                if not rule.rule_config:
                    logger.warning(f"⚠️ Rule {rule.tag_name} has no rule_config, skipping")
                    continue
                
                # Evaluate the rule
                if self._evaluate_rule(rule, message, user, bot):
                    # Process THEN actions
                    then_actions = rule.rule_config.get('then', [])
                    
                    for action in then_actions:
                        action_type = action.get('action')
                        tag_name = action.get('tag_name')
                        
                        if action_type == 'apply_tag' and tag_name:
                            if tag_name not in tags_to_apply:
                                tags_to_apply.append(tag_name)
                                logger.info(f"✅ Rule '{rule.tag_name}' triggered: APPLY tag '{tag_name}'")
                        
                        elif action_type == 'remove_tag' and tag_name:
                            if tag_name not in tags_to_remove:
                                tags_to_remove.append(tag_name)
                                logger.info(f"❌ Rule '{rule.tag_name}' triggered: REMOVE tag '{tag_name}'")
            
            # Remove any tags that are marked for removal from the apply list
            final_tags = [tag for tag in tags_to_apply if tag not in tags_to_remove]
            
            logger.info(f"🏁 Rule evaluation complete: {len(final_tags)} tags to apply: {final_tags}")
            return final_tags
            
        except Exception as e:
            logger.error(f"❌ Error evaluating rules: {e}", exc_info=True)
            return []
    
    def _evaluate_rule(self, rule: TagRule, message: MessageLog, user: User, bot: Bot) -> bool:
        """
        Evaluate a single rule against the message, user, and bot context.
        
        Args:
            rule: TagRule instance
            message: MessageLog instance
            user: User instance
            bot: Bot instance
            
        Returns:
            True if rule conditions are met, False otherwise
        """
        try:
            rule_config = rule.rule_config
            
            if not rule_config:
                logger.warning(f"⚠️ Rule '{rule.tag_name}' has no rule_config")
                return False
            
            # Check WHEN trigger
            when_config = rule_config.get('when', {})
            if not self._check_trigger(when_config, message, user):
                logger.debug(f"   ⏭️ Trigger not matched for rule '{rule.tag_name}'")
                return False
            
            logger.debug(f"   ✓ Trigger matched for rule '{rule.tag_name}'")
            
            # Check IF conditions (all must be true - AND logic)
            if_conditions = rule_config.get('if', [])
            
            if not if_conditions:
                # No conditions means rule is always triggered when trigger matches
                logger.debug(f"   ✓ No conditions to check for rule '{rule.tag_name}'")
                return True
            
            for condition in if_conditions:
                if not self._check_condition(condition, message, user):
                    logger.debug(f"   ✗ Condition failed: {condition.get('condition_type')}")
                    return False
            
            logger.debug(f"   ✓ All conditions passed for rule '{rule.tag_name}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error evaluating rule '{rule.tag_name}': {e}", exc_info=True)
            return False
    
    def _check_trigger(self, when_config: Dict[str, Any], message: MessageLog, user: User) -> bool:
        """
        Check if the WHEN trigger condition is met.
        
        Args:
            when_config: When configuration dict
            message: MessageLog instance
            user: User instance
            
        Returns:
            True if trigger is met, False otherwise
        """
        if not when_config:
            return False
            
        trigger = when_config.get('trigger')
        
        if trigger == 'message_received':
            # Trigger when user sends a message (incoming direction)
            return message.direction == 'incoming'
        
        elif trigger == 'user_day_reached':
            # Trigger when user reaches specific day
            day = when_config.get('day')
            if day is not None:
                return user.current_day == day
            return False
        
        elif trigger == 'sentiment_detected':
            # Trigger when specific sentiment is detected
            sentiment = when_config.get('sentiment')
            if sentiment and message.llm_sentiment:
                return message.llm_sentiment.lower() == sentiment.lower()
            return False
        
        elif trigger == 'tag_applied':
            # Trigger when another specific tag is applied
            tag = when_config.get('tag')
            if tag and message.llm_tags:
                return tag in message.llm_tags
            return False
        
        else:
            logger.warning(f"⚠️ Unknown trigger type: {trigger}")
            return False
    
    def _check_condition(self, condition: Dict[str, Any], message: MessageLog, user: User) -> bool:
        """
        Check if a single IF condition is met.
        
        Args:
            condition: Condition configuration dict
            message: MessageLog instance
            user: User instance
            
        Returns:
            True if condition is met, False otherwise
        """
        if not condition:
            return False
            
        condition_type = condition.get('condition_type')
        value = condition.get('value')
        
        if condition_type == 'contains_keyword':
            # Check if message contains specific keyword (case-insensitive)
            if not message.raw_text or not value:
                return False
            return value.lower() in message.raw_text.lower()
        
        elif condition_type == 'sentiment_is':
            # Check if message sentiment equals specific value
            if not message.llm_sentiment or not value:
                return False
            return message.llm_sentiment.lower() == value.lower()
        
        elif condition_type == 'user_day_is':
            # Check if user's current_day equals value
            if value is None:
                return False
            return user.current_day == value
        
        elif condition_type == 'tag_exists':
            # Check if user already has specific tag
            if not value:
                return False
            user_tags = user.tags or []
            return value in user_tags
        
        elif condition_type == 'user_day_greater_than':
            # Check if user's current_day > value
            if value is None:
                return False
            return user.current_day > value
        
        elif condition_type == 'user_day_less_than':
            # Check if user's current_day < value
            if value is None:
                return False
            return user.current_day < value
        
        else:
            logger.warning(f"⚠️ Unknown condition type: {condition_type}")
            return False
    
    def get_active_rules_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all active rule-based TagRules.
        
        Returns:
            List of rule summaries
        """
        try:
            rules = TagRule.query.filter_by(
                rule_type='rule_based',
                is_active=True
            ).order_by(TagRule.priority.desc()).all()
            
            summaries = []
            for rule in rules:
                summaries.append({
                    'id': rule.id,
                    'tag_name': rule.tag_name,
                    'description': rule.description,
                    'priority': rule.priority,
                    'rule_config': rule.rule_config,
                    'created_at': rule.created_at.isoformat()
                })
            
            return summaries
            
        except Exception as e:
            logger.error(f"❌ Error getting rules summary: {e}", exc_info=True)
            return []


# Singleton instance
rule_engine = RuleEngine()
