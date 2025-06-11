# -*- coding: utf-8 -*-
"""
Gemini TTS Core Module
======================

Core functionality for Gemini TTS addon including:
- TTS engine implementation
- Configuration management
- API integration

This __init__.py file makes the core directory a proper Python package
and provides clean imports for the main addon file.
"""

# Import main classes to make them available at package level
try:
    from .tts_engine import GeminiTTS
    from . import config
    
    # Export these for use by parent package
    __all__ = ['GeminiTTS', 'config']
    
except ImportError as e:
    # If imports fail, log but don't crash the addon
    print(f"Gemini TTS Core: Import warning - {e}")
    __all__ = []