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
from aqt import mw, gui_hooks
from aqt.qt import QAction

# ============================================================================
# GLOBAL CONSTANTS
# ============================================================================

# Key for storing TTS instances per profile
TTS_INSTANCE_KEY = "_gemini_tts_instances"

# ============================================================================
# PROFILE-AWARE INSTANCE MANAGEMENT
# ============================================================================

def get_current_tts_instance():
    """
    Get the TTS instance for the current profile.
    
    Returns:
        GeminiTTS instance for current profile or None if not initialized
    """
    if not hasattr(mw, TTS_INSTANCE_KEY):
        return None
    
    profile_name = getattr(mw.pm, 'name', 'default')
    instances = getattr(mw, TTS_INSTANCE_KEY)
    return instances.get(profile_name)

def set_current_tts_instance(instance):
    """
    Set the TTS instance for the current profile.
    
    Args:
        instance: GeminiTTS instance to store
    """
    if not hasattr(mw, TTS_INSTANCE_KEY):
        setattr(mw, TTS_INSTANCE_KEY, {})
    
    profile_name = getattr(mw.pm, 'name', 'default')
    instances = getattr(mw, TTS_INSTANCE_KEY)
    instances[profile_name] = instance

def cleanup_profile_instance(profile_name=None):
    """
    Clean up TTS instance for specific profile.
    
    Args:
        profile_name: Profile to clean up, or current profile if None
    """
    if not hasattr(mw, TTS_INSTANCE_KEY):
        return
    
    if profile_name is None:
        profile_name = getattr(mw.pm, 'name', 'default')
    
    instances = getattr(mw, TTS_INSTANCE_KEY)
    if profile_name in instances:
        del instances[profile_name]
        print(f"Gemini TTS: Cleaned up instance for profile '{profile_name}'")

# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_addon():
    """
    Initialize the add-on after Anki profile loads.
    
    This function is called automatically when a user profile is loaded.
    It creates a TTS engine instance for the current profile.
    """
    try:
        # Import TTS engine class from core module
        from .core.tts_engine import GeminiTTS
        
        # Create TTS engine instance for current profile
        tts_instance = GeminiTTS()
        set_current_tts_instance(tts_instance)
        
        profile_name = getattr(mw.pm, 'name', 'default')
        print(f"Gemini TTS: Successfully initialized for profile '{profile_name}'")
        
    except Exception as e:
        # Log errors but don't crash Anki
        profile_name = getattr(mw.pm, 'name', 'default')
        print(f"Gemini TTS: Initialization error for profile '{profile_name}' - {e}")

def cleanup():
    """
    Clean up when Anki profile unloads.
    
    This ensures proper cleanup when switching profiles or closing Anki.
    """
    profile_name = getattr(mw.pm, 'name', 'default')
    cleanup_profile_instance(profile_name)

def cleanup_all_instances():
    """
    Clean up all TTS instances when Anki closes.
    """
    if hasattr(mw, TTS_INSTANCE_KEY):
        delattr(mw, TTS_INSTANCE_KEY)
        print("Gemini TTS: Cleaned up all instances")

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
    tts_instance = get_current_tts_instance()
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
# Use modern hook with fallback to legacy for older Anki versions
try:
    gui_hooks.profile_did_open.append(initialize_addon)
except AttributeError:
    # Fallback for older Anki versions
    addHook("profileLoaded", initialize_addon)

# Register cleanup function to run when profile unloads
addHook("unloadProfile", cleanup)

# Register cleanup for when Anki closes completely
try:
    gui_hooks.main_window_did_init.append(lambda: addHook("atexit", cleanup_all_instances))
except AttributeError:
    # Fallback for older versions
    addHook("atexit", cleanup_all_instances)

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