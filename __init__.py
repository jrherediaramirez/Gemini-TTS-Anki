# -*- coding: utf-8 -*-
"""
Gemini TTS Add-on for Anki
==========================

Professional Text-to-Speech integration using Google's Gemini API.
Works on all platforms with zero external dependencies.

Author: Jesus Heredia Ramirez
License: MIT
"""

import os
from anki.hooks import addHook
from aqt import mw
from aqt.qt import QAction

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================

# Global TTS engine instance - initialized when profile loads
tts_instance = None

# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_addon():
    """
    Initialize the add-on after Anki profile loads.
    
    This function is called automatically when a user profile is loaded.
    It creates the main TTS engine instance and handles any initialization errors.
    """
    global tts_instance
    
    try:
        # Import TTS engine class from core module
        from .core.tts_engine import GeminiTTS
        
        # Create the main TTS engine instance
        tts_instance = GeminiTTS()
        print("Gemini TTS: Successfully initialized")
        
    except Exception as e:
        # Log errors but don't crash Anki
        print(f"Gemini TTS: Initialization error - {e}")
        tts_instance = None

def cleanup():
    """
    Clean up when Anki profile unloads.
    
    This ensures proper cleanup when switching profiles or closing Anki.
    """
    global tts_instance
    tts_instance = None
    print("Gemini TTS: Cleaned up")

# ============================================================================
# UI INTEGRATION FUNCTIONS
# ============================================================================

def setup_editor_button(buttons, editor):
    """
    Add TTS button to the note editor toolbar.
    
    Args:
        buttons: List of existing editor buttons
        editor: Anki editor instance
        
    Returns:
        Updated buttons list with TTS button added
    """
    if tts_instance:
        return tts_instance.setup_editor_button(buttons, editor)
    else:
        # If TTS engine failed to initialize, return buttons unchanged
        print("Gemini TTS: Cannot add button - engine not initialized")
        return buttons

def show_config():
    """
    Show the configuration dialog.
    
    Opens the TTS configuration window where users can set their API key
    and adjust other settings.
    """
    try:
        from .core import config
        config.show_config_dialog()
        
    except Exception as e:
        # Show user-friendly error if config dialog fails
        from aqt.utils import showInfo
        showInfo(f"Configuration error: {e}")

# ============================================================================
# ANKI HOOKS REGISTRATION
# ============================================================================

# Register initialization function to run when profile loads
addHook("profileLoaded", initialize_addon)

# Register cleanup function to run when profile unloads
addHook("profileUnloaded", cleanup)

# Register button setup function to add TTS button to editor
addHook("setupEditorButtons", setup_editor_button)

# ============================================================================
# MENU INTEGRATION
# ============================================================================

try:
    # Add configuration menu item to Tools menu
    config_action = QAction("Gemini TTS Configuration", mw)
    config_action.triggered.connect(show_config)
    mw.form.menuTools.addAction(config_action)
    
except Exception as e:
    # Log menu setup errors but don't crash
    print(f"Gemini TTS: Menu setup error - {e}")

# ============================================================================
# MODULE INFORMATION
# ============================================================================

__version__ = "2.0.0"
__author__ = "Jesus Heredia Ramirez"
__description__ = "Professional TTS for Anki using Google Gemini API with automatic field detection"