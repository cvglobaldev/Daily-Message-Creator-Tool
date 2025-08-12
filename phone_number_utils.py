"""
Phone Number Utilities for Multi-Bot WhatsApp System
====================================================

Universal phone number normalization and validation utilities that ensure
consistent handling across all bots and platforms.

This module provides robust phone number processing to handle various formats:
- International: +62 838-2233-1133
- Formatted: (62) 838.2233.1133  
- Spaced: 62 838 2233 1133
- Dashed: 62-838-2233-1133
- Clean: 6283822331133
- Local Indonesian: 0838-2233-1133

All formats are normalized to: +6283822331133

Author: AI Assistant
Date: August 12, 2025
"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

class PhoneNumberProcessor:
    """Comprehensive phone number processing for multi-platform chatbot system"""
    
    # Common Indonesian mobile prefixes
    INDONESIAN_MOBILE_PREFIXES = [
        '811', '812', '813', '814', '815', '816', '817', '818', '819',  # Telkomsel
        '821', '822', '823', '852', '853',  # Telkomsel
        '831', '832', '833', '838',  # Axis
        '855', '856', '857', '858',  # Indosat
        '877', '878',  # XL
        '881', '882', '883', '884', '885', '886', '887', '888', '889',  # Smartfren
    ]
    
    def __init__(self):
        self.formatting_chars = [' ', '-', '(', ')', '.', '_']
    
    def normalize_phone_number(self, phone_number: str, platform: str = "whatsapp") -> str:
        """
        Normalize phone number to standard international format
        
        Args:
            phone_number: Raw phone number in any format
            platform: Platform type ('whatsapp' or 'telegram')
            
        Returns:
            Normalized phone number (+6283822331133) or original for Telegram
        """
        if not phone_number:
            return phone_number
            
        # Skip Telegram chat IDs
        if platform == "telegram" or phone_number.startswith('tg_'):
            return phone_number
            
        logger.debug(f"Normalizing phone number: '{phone_number}'")
        
        # Remove all formatting characters
        clean_number = phone_number
        for char in self.formatting_chars:
            clean_number = clean_number.replace(char, '')
            
        # Remove common prefixes that might be added incorrectly
        clean_number = clean_number.lstrip('+0')
        
        # Handle Indonesian local format (0xxx) -> international (+62xxx)
        if clean_number.startswith('0') and len(clean_number) >= 10:
            # Convert 08xx to 62xx format
            clean_number = f"62{clean_number[1:]}"
        elif not clean_number.startswith('62') and len(clean_number) >= 9:
            # Assume it's Indonesian if it doesn't start with country code
            clean_number = f"62{clean_number}"
            
        # Add international prefix
        normalized = f"+{clean_number}"
        
        logger.info(f"Phone normalized: '{phone_number}' -> '{normalized}'")
        return normalized
    
    def generate_lookup_variations(self, phone_number: str) -> List[str]:
        """
        Generate common phone number variations for database lookup
        
        This ensures we can find users regardless of how their number was originally stored
        vs how it's received in new webhooks.
        """
        if not phone_number or phone_number.startswith('tg_'):
            return [phone_number]
            
        variations = set()
        
        # Start with the original number
        variations.add(phone_number)
        
        # Get base digits only
        base_digits = re.sub(r'[^\d]', '', phone_number)
        
        if not base_digits:
            return list(variations)
            
        # Add common international formats
        if base_digits.startswith('62'):
            variations.add(f"+{base_digits}")
            variations.add(base_digits)
            variations.add(f"0{base_digits[2:]}")  # Local Indonesian format
        elif base_digits.startswith('0') and len(base_digits) >= 10:
            # Local Indonesian to international
            international = f"62{base_digits[1:]}"
            variations.add(f"+{international}")
            variations.add(international)
            variations.add(base_digits)  # Keep original 0xxx format
        else:
            # Assume it's Indonesian mobile without country code
            if len(base_digits) >= 9:
                international = f"62{base_digits}"
                variations.add(f"+{international}")
                variations.add(international)
                variations.add(f"0{base_digits}")  # Local format
            variations.add(base_digits)
            variations.add(f"+{base_digits}")
            
        logger.debug(f"Generated {len(variations)} variations for '{phone_number}': {variations}")
        return list(variations)
    
    def validate_indonesian_mobile(self, phone_number: str) -> Tuple[bool, str]:
        """
        Validate if phone number is a valid Indonesian mobile number
        
        Returns:
            (is_valid, reason)
        """
        normalized = self.normalize_phone_number(phone_number)
        
        # Remove + and check if it starts with 62
        if not normalized.startswith('+62'):
            return False, "Not an Indonesian number (+62)"
            
        # Extract mobile part (after +62)
        mobile_part = normalized[3:]
        
        if len(mobile_part) < 9 or len(mobile_part) > 12:
            return False, f"Invalid length: {len(mobile_part)} digits (expected 9-12)"
            
        # Check if it starts with a valid mobile prefix
        prefix = mobile_part[:3]
        if prefix not in self.INDONESIAN_MOBILE_PREFIXES:
            return False, f"Invalid mobile prefix: {prefix}"
            
        return True, "Valid Indonesian mobile number"
    
    def format_display_number(self, phone_number: str) -> str:
        """
        Format phone number for display purposes
        
        Example: +6283822331133 -> +62 838-2233-1133
        """
        normalized = self.normalize_phone_number(phone_number)
        
        if not normalized.startswith('+62'):
            return phone_number  # Return original if not Indonesian
            
        # Extract parts: +62 838 2233 1133
        mobile_part = normalized[3:]
        if len(mobile_part) >= 9:
            return f"+62 {mobile_part[:3]}-{mobile_part[3:7]}-{mobile_part[7:]}"
            
        return normalized

# Global instance for use throughout the application
phone_processor = PhoneNumberProcessor()

# Convenience functions for backward compatibility
def normalize_phone_number(phone_number: str, platform: str = "whatsapp") -> str:
    """Normalize phone number to standard format"""
    return phone_processor.normalize_phone_number(phone_number, platform)

def generate_phone_variations(phone_number: str) -> List[str]:
    """Generate lookup variations for phone number"""
    return phone_processor.generate_lookup_variations(phone_number)

def validate_indonesian_mobile(phone_number: str) -> Tuple[bool, str]:
    """Validate Indonesian mobile number"""
    return phone_processor.validate_indonesian_mobile(phone_number)

if __name__ == "__main__":
    # Test cases
    test_numbers = [
        "+62 838-2233-1133",
        "62 838 2233 1133",
        "(62) 838.2233.1133",
        "0838-2233-1133",
        "838-2233-1133",
        "+6283822331133",
        "6283822331133"
    ]
    
    print("Phone Number Normalization Test Results:")
    print("=" * 50)
    
    for number in test_numbers:
        normalized = normalize_phone_number(number)
        variations = generate_phone_variations(number)
        is_valid, reason = validate_indonesian_mobile(number)
        
        print(f"Original:    {number}")
        print(f"Normalized:  {normalized}")
        print(f"Valid:       {is_valid} ({reason})")
        print(f"Variations:  {len(variations)} formats")
        print("-" * 30)