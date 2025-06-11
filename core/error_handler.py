# -*- coding: utf-8 -*-
"""
Gemini TTS Error Handler
========================

Centralized error handling and user feedback for Gemini TTS add-on.
"""

import logging
from aqt.utils import tooltip, showCritical

def get_logger():
    """Get or create logger for Gemini TTS."""
    logger = logging.getLogger("gemini_tts")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = get_logger()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handle_api_error(error: Exception, context: str = "") -> str:
    """Handle API-related errors with user-friendly messages."""
    error_str = str(error).lower()
    
    if "403" in error_str or "invalid api key" in error_str:
        message = "Invalid API key. Check your configuration."
        logger.error(f"API Key Error - {context}: {error}")
        tooltip(message)
        return message
        
    elif "429" in error_str or "rate limit" in error_str:
        message = "Rate limited. Wait a moment and try again."
        logger.warning(f"Rate Limit - {context}: {error}")
        tooltip(message)
        return message
        
    elif "400" in error_str:
        message = "Invalid request. Check your text and settings."
        logger.error(f"Bad Request - {context}: {error}")
        tooltip(message)
        return message
        
    else:
        message = f"API error: {str(error)[:50]}..."
        logger.error(f"Unknown API Error - {context}: {error}")
        tooltip(message)
        return message

def handle_network_error(error: Exception, context: str = "") -> str:
    """Handle network-related errors."""
    error_str = str(error).lower()
    
    if "timeout" in error_str:
        message = "Network timeout. Check your connection."
    elif "connection" in error_str:
        message = "Connection failed. Check your internet."
    else:
        message = "Network error. Check your connection."
    
    logger.error(f"Network Error - {context}: {error}")
    tooltip(message)
    return message

def handle_config_error(error: Exception, context: str = "") -> str:
    """Handle configuration save/load errors."""
    message = "Configuration error. Settings may not save."
    logger.error(f"Config Error - {context}: {error}")
    tooltip(message)
    return message

def handle_cache_error(error: Exception, context: str = "") -> str:
    """Handle cache file I/O errors."""
    message = "Cache error. Audio may not be saved for reuse."
    logger.warning(f"Cache Error - {context}: {error}")
    # Don't show tooltip for cache errors - they're not critical
    return message

def handle_ui_error(error: Exception, context: str = "") -> str:
    """Handle UI creation errors."""
    message = "UI error. Some buttons may not work."
    logger.error(f"UI Error - {context}: {error}")
    tooltip(message)
    return message

# ============================================================================
# SAFE OPERATION WRAPPERS
# ============================================================================

def safe_api_call(func, *args, **kwargs):
    """Safely execute API calls with proper error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_api_error(e, f"API call: {func.__name__}")
        return None

def safe_config_operation(func, *args, **kwargs):
    """Safely execute config operations with proper error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_config_error(e, f"Config operation: {func.__name__}")
        return None

def safe_cache_operation(func, *args, **kwargs):
    """Safely execute cache operations with proper error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_cache_error(e, f"Cache operation: {func.__name__}")
        return None

def safe_ui_operation(func, *args, **kwargs):
    """Safely execute UI operations with proper error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_ui_error(e, f"UI operation: {func.__name__}")
        return None

# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    if not api_key or not api_key.strip():
        return False
    
    # Basic format check - Gemini API keys are typically long alphanumeric
    if len(api_key.strip()) < 20:
        return False
        
    return True

def validate_text_length(text: str, max_length: int = 5000) -> bool:
    """Validate text length for TTS processing."""
    if not text:
        return False
        
    if len(text) > max_length:
        logger.warning(f"Text too long: {len(text)} chars (max: {max_length})")
        tooltip(f"Text too long ({len(text)} chars). Maximum: {max_length}")
        return False
        
    return True

# ============================================================================
# ERROR REPORTING
# ============================================================================

def report_critical_error(error: Exception, context: str = ""):
    """Report critical errors that prevent add-on functionality."""
    message = f"Critical Gemini TTS error: {str(error)[:100]}"
    logger.critical(f"CRITICAL - {context}: {error}")
    showCritical(f"{message}\n\nCheck Tools > Add-ons for details.")

def log_debug_info(message: str):
    """Log debug information for troubleshooting."""
    logger.debug(f"DEBUG: {message}")

# ============================================================================
# CONTEXT MANAGERS
# ============================================================================

class error_context:
    """Context manager for handling errors in specific operations."""
    
    def __init__(self, operation_name: str, critical: bool = False):
        self.operation_name = operation_name
        self.critical = critical
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.critical:
                report_critical_error(exc_val, self.operation_name)
            else:
                logger.error(f"Error in {self.operation_name}: {exc_val}")
                tooltip(f"Error in {self.operation_name}")
        return False  # Don't suppress the exception