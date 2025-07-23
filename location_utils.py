import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def get_ip_location_data(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Get location data from IP address using ip-api.com (free tier)
    Returns dict with country, region, city, timezone
    """
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        return {
            'country': None,
            'region': None, 
            'city': None,
            'timezone': None
        }
    
    try:
        # Use ip-api.com free service (no key required, 1000 requests/hour)
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('status') == 'success':
                return {
                    'country': data.get('country'),
                    'region': data.get('regionName'), 
                    'city': data.get('city'),
                    'timezone': data.get('timezone')
                }
            else:
                logger.warning(f"IP location API returned error: {data.get('message')}")
                
    except requests.RequestException as e:
        logger.error(f"Error fetching IP location for {ip_address}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in IP location lookup: {e}")
    
    return {
        'country': None,
        'region': None,
        'city': None, 
        'timezone': None
    }

def extract_telegram_user_data(user_data: dict, request_ip: str = None) -> dict:
    """
    Extract comprehensive user data from Telegram webhook user object
    """
    if not user_data:
        return {}
    
    # Get location data from IP if available
    location_data = get_ip_location_data(request_ip) if request_ip else {
        'country': None, 'region': None, 'city': None, 'timezone': None
    }
    
    return {
        'username': user_data.get('username'),
        'first_name': user_data.get('first_name'),
        'last_name': user_data.get('last_name'),
        'language_code': user_data.get('language_code'),
        'is_premium': user_data.get('is_premium'),
        'name': user_data.get('first_name') or user_data.get('username'),
        'ip_address': request_ip,
        **location_data
    }