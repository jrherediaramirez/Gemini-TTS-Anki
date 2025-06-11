# -*- coding: utf-8 -*-
"""
Gemini TTS Core Module
======================

Core functionality for Gemini TTS addon including:
- TTS engine implementation
- Configuration management
- Error handling
- API integration
- Profile-aware instance management
"""

# Import main classes to make them available at package level
try:
    from .tts_engine import GeminiTTS
    from . import config
    from . import error_handler
    
    # Export these for use by parent package
    __all__ = ['GeminiTTS', 'config', 'error_handler']
    
except ImportError as e:
    # If imports fail, log but don't crash the addon
    print(f"Gemini TTS Core: Import warning - {e}")
    __all__ = []