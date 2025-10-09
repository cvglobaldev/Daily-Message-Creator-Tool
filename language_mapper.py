"""
Language Mapper
Centralized mapping system for converting human-readable language names to Google Cloud language codes
"""

# Language mapping: human-readable name -> Google Cloud language code
LANGUAGE_CODE_MAP = {
    # English variants
    'English': 'en-US',
    'english': 'en-US',
    'en': 'en-US',
    
    # Indonesian
    'Indonesian': 'id-ID',
    'indonesian': 'id-ID',
    'Bahasa Indonesia': 'id-ID',
    'bahasa indonesia': 'id-ID',
    'id': 'id-ID',
    
    # Hindi
    'Hindi': 'hi-IN',
    'hindi': 'hi-IN',
    'hi': 'hi-IN',
    
    # Arabic
    'Arabic': 'ar-SA',
    'arabic': 'ar-SA',
    'ar': 'ar-SA',
    
    # Spanish
    'Spanish': 'es-ES',
    'spanish': 'es-ES',
    'Español': 'es-ES',
    'español': 'es-ES',
    'es': 'es-ES',
    
    # French
    'French': 'fr-FR',
    'french': 'fr-FR',
    'Français': 'fr-FR',
    'français': 'fr-FR',
    'fr': 'fr-FR',
    
    # Burmese
    'Burmese': 'my-MM',
    'burmese': 'my-MM',
    'Myanmar': 'my-MM',
    'myanmar': 'my-MM',
    'my': 'my-MM',
    
    # Mandarin Chinese
    'Chinese': 'zh-CN',
    'chinese': 'zh-CN',
    'Mandarin': 'zh-CN',
    'mandarin': 'zh-CN',
    'zh': 'zh-CN',
    
    # Portuguese
    'Portuguese': 'pt-BR',
    'portuguese': 'pt-BR',
    'Português': 'pt-BR',
    'português': 'pt-BR',
    'pt': 'pt-BR',
}

def get_language_code(language_name: str, default: str = 'en-US') -> str:
    """
    Convert human-readable language name to Google Cloud language code
    
    Args:
        language_name: Human-readable language name (e.g., "Indonesian", "English")
        default: Default language code if no mapping found (default: 'en-US')
    
    Returns:
        Google Cloud language code (e.g., 'id-ID', 'en-US')
    
    Examples:
        >>> get_language_code("Indonesian")
        'id-ID'
        >>> get_language_code("English")
        'en-US'
        >>> get_language_code("Unknown Language")
        'en-US'
    """
    if not language_name:
        return default
    
    # Try exact match first (case-insensitive)
    language_code = LANGUAGE_CODE_MAP.get(language_name.strip(), None)
    
    if language_code:
        return language_code
    
    # If no exact match, try case-insensitive lookup
    for key, value in LANGUAGE_CODE_MAP.items():
        if key.lower() == language_name.lower().strip():
            return value
    
    # No match found, return default
    return default

def get_supported_languages():
    """
    Get list of all supported language names
    
    Returns:
        List of unique supported language names
    """
    # Get unique language names (exclude duplicates like lowercase variants)
    unique_languages = set()
    for lang in LANGUAGE_CODE_MAP.keys():
        if lang[0].isupper():  # Only include capitalized variants
            unique_languages.add(lang)
    
    return sorted(list(unique_languages))
