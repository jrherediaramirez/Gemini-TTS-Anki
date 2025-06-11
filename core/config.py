# -*- coding: utf-8 -*-
"""
Gemini TTS Configuration Dialog
===============================

User interface for configuring TTS settings including API key setup,
model selection, voice selection, and cache management.

Features:
- API key validation and testing
- Model selection (Flash vs Pro)
- Voice selection from available options
- Cache management controls
- User-friendly error handling
- Profile-aware instance management
"""

from aqt import mw
from aqt.theme import theme_manager
from aqt.qt import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
                    QCheckBox, QPushButton, QSpinBox, QDoubleSpinBox, QMessageBox,
                    QHBoxLayout, QLabel)

# ============================================================================
# DIALOG ENTRY POINT
# ============================================================================

def show_config_dialog():
    """
    Show the configuration dialog for Gemini TTS.
    
    This function handles dialog creation and error handling if the
    TTS engine is not available.
    """
    try:
        # Get current profile's TTS instance using unified management
        from .. import get_current_tts_instance, set_current_tts_instance
        
        tts_instance = get_current_tts_instance()
        if not tts_instance:
            # Create new instance if none exists for current profile
            from .tts_engine import GeminiTTS
            tts_instance = GeminiTTS()
            set_current_tts_instance(tts_instance)
        
        # Create and show dialog
        dialog = ConfigDialog(tts_instance)
        
        # Use exec_() for better compatibility across Qt versions
        if hasattr(dialog, 'exec_'):
            dialog.exec_()
        else:
            dialog.exec()
        
    except Exception as e:
        # Show error if configuration dialog fails to load
        from aqt.utils import showInfo
        showInfo(f"Configuration error: {e}")

# ============================================================================
# MAIN CONFIGURATION DIALOG CLASS
# ============================================================================

class ConfigDialog(QDialog):
    """
    Main configuration dialog for Gemini TTS settings.
    
    This dialog allows users to configure:
    - API key and connection testing
    - Model selection (Flash vs Pro)
    - Voice selection from available options
    - Temperature setting for voice variation
    - Cache settings and management
    """
    
    def __init__(self, tts_instance):
        """
        Initialize the configuration dialog.
        
        Args:
            tts_instance: GeminiTTS engine instance
        """
        super(ConfigDialog, self).__init__(mw)
        self.tts = tts_instance
        
        # Set dialog properties
        self.setWindowTitle("Gemini TTS Configuration")
        self.setMinimumWidth(450)
        
        # Build and populate UI
        self.setup_ui()
        self.load_current_config()
    
    # ========================================================================
    # UI SETUP METHODS
    # ========================================================================
    
    def setup_ui(self):
        """Create and arrange all UI elements."""
        layout = QVBoxLayout(self)
        
        # Main configuration form
        self.create_main_form(layout)
        
        # Information section
        self.create_info_section(layout)
        
        # Action buttons
        self.create_button_section(layout)
    
    def create_main_form(self, parent_layout):
        """
        Create the main configuration form.
        
        Args:
            parent_layout: Parent layout to add form to
        """
        form = QFormLayout()
        
        # API Key input field
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your Gemini API key")
        form.addRow("API Key:", self.api_key_input)
        
        # Model selection dropdown
        self.model_combo = QComboBox()
        models = self.tts.get_available_models()
        for model_key, model_info in models.items():
            self.model_combo.addItem(model_info["display_name"], model_key)
        form.addRow("Model:", self.model_combo)
        
        # Voice selection dropdown
        self.voice_combo = QComboBox()
        voices = self.tts.get_available_voices()
        self.voice_combo.addItems(voices)
        form.addRow("Voice:", self.voice_combo)
        
        # Temperature setting (voice variation)
        self.temp_spinner = QDoubleSpinBox()
        self.temp_spinner.setRange(0.0, 1.0)
        self.temp_spinner.setSingleStep(0.1)
        self.temp_spinner.setDecimals(1)
        self.temp_spinner.setToolTip("0.0 = deterministic, 1.0 = creative")
        form.addRow("Temperature:", self.temp_spinner)
        
        # Cache settings section
        self.create_cache_settings(form)
        
        parent_layout.addLayout(form)
    
    def create_cache_settings(self, form):
        """
        Create cache configuration controls.
        
        Args:
            form: Form layout to add cache settings to
        """
        cache_layout = QHBoxLayout()
        
        # Enable caching checkbox
        self.cache_enabled = QCheckBox("Enable caching")
        cache_layout.addWidget(self.cache_enabled)
        
        # Cache duration setting
        self.cache_days = QSpinBox()
        self.cache_days.setRange(1, 365)
        self.cache_days.setSuffix(" days")
        cache_layout.addWidget(QLabel("Keep for:"))
        cache_layout.addWidget(self.cache_days)
        cache_layout.addStretch()
        
        form.addRow("Cache:", cache_layout)
    
    def create_info_section(self, parent_layout):
        """
        Create information section with API key instructions.
        
        Args:
            parent_layout: Parent layout to add info section to
        """
        info_label = QLabel(
            "<b>How to get API key:</b><br>"
            "1. Visit <a href='https://ai.google.dev/'>ai.google.dev</a><br>"
            "2. Click 'Get API key' then 'Create API key'<br>"
            "3. Copy and paste the key above<br><br>"
            "<b>Audio Placement:</b><br>"
            "Audio will be automatically added to the field you're editing"
        )
        
        # Configure info label appearance and behavior
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        
        # Set background color based on Anki's theme for better visibility
        bg_color = "#3a3a3a" if theme_manager.night_mode else "#f0f0f0"
        
        info_label.setStyleSheet(
            f"QLabel {{ "
            f"background-color: {bg_color}; "
            f"padding: 10px; "
            f"border-radius: 5px; "
            f"}}"
        )
        
        parent_layout.addWidget(info_label)
    
    def create_button_section(self, parent_layout):
        """
        Create action buttons section.
        
        Args:
            parent_layout: Parent layout to add buttons to
        """
        button_layout = QHBoxLayout()
        
        # Utility buttons
        self.create_utility_buttons(button_layout)
        
        # Add spacer
        button_layout.addStretch()
        
        # Main action buttons
        self.create_action_buttons(button_layout)
        
        parent_layout.addLayout(button_layout)
    
    def create_utility_buttons(self, button_layout):
        """
        Create utility buttons (test, cleanup).
        
        Args:
            button_layout: Layout to add utility buttons to
        """
        # API key test button
        test_btn = QPushButton("Test API Key")
        test_btn.clicked.connect(self.test_api_key)
        button_layout.addWidget(test_btn)
        
        # Cache cleanup button
        cleanup_btn = QPushButton("Clean Cache")
        cleanup_btn.clicked.connect(self.cleanup_cache)
        button_layout.addWidget(cleanup_btn)
    
    def create_action_buttons(self, button_layout):
        """
        Create main action buttons (save, cancel).
        
        Args:
            button_layout: Layout to add action buttons to
        """
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        save_btn.setDefault(True)  # Default button (Enter key)
        button_layout.addWidget(save_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
    
    # ========================================================================
    # DATA MANAGEMENT METHODS
    # ========================================================================
    
    def load_current_config(self):
        """Load current configuration values into form fields."""
        config = self.tts.config
        
        # Load API key
        self.api_key_input.setText(config.get("api_key", ""))
        
        # Load and set model selection
        model_key = config.get("model", "flash")
        model_index = self.model_combo.findData(model_key)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        
        # Load and set voice selection
        voice = config.get("voice", "Zephyr")
        voice_index = self.voice_combo.findText(voice)
        if voice_index >= 0:
            self.voice_combo.setCurrentIndex(voice_index)
        
        # Load other settings
        self.temp_spinner.setValue(config.get("temperature", 0.0))
        self.cache_enabled.setChecked(config.get("enable_cache", True))
        self.cache_days.setValue(config.get("cache_days", 30))
    
    def save_config(self):
        """Validate and save configuration settings."""
        # Get values from form
        api_key = self.api_key_input.text().strip()
        
        # Validate required fields
        if not api_key:
            QMessageBox.warning(self, "Error", "API key is required")
            return
        
        # Get selected model key
        model_key = self.model_combo.currentData()
        
        # Create configuration dictionary
        new_config = {
            "api_key": api_key,
            "model": model_key,
            "voice": self.voice_combo.currentText(),
            "temperature": self.temp_spinner.value(),
            "enable_cache": self.cache_enabled.isChecked(),
            "cache_days": self.cache_days.value()
        }
        
        # Attempt to save configuration
        try:
            self.tts.save_config(new_config)
            QMessageBox.information(self, "Success", "Configuration saved successfully")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")
    
    # ========================================================================
    # UTILITY ACTIONS
    # ========================================================================
    
    def test_api_key(self):
        """Test the entered API key with current settings."""
        api_key = self.api_key_input.text().strip()
        
        # Validate API key is entered
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first")
            return
        
        # Get current form values for testing
        model_key = self.model_combo.currentData()
        voice = self.voice_combo.currentText()
        temperature = self.temp_spinner.value()
        
        # Use current TTS instance for testing with temporary config
        test_config = self.tts.config.copy()
        test_config["api_key"] = api_key
        test_config["model"] = model_key
        test_config["voice"] = voice
        test_config["temperature"] = temperature
        
        # Temporarily update config for test
        original_config = self.tts.config
        self.tts.config = test_config
        
        try:
            # Test with short text to minimize API usage
            test_text = "Hello"
            audio_data = self.tts.generate_audio_http(test_text)
            
            # Check if reasonable amount of audio data was returned
            if len(audio_data) > 1000:
                QMessageBox.information(
                    self, "Success", 
                    f"API key is working with {model_key.title()} model and {voice} voice. "
                    f"Generated {len(audio_data):,} bytes of audio data."
                )
            else:
                QMessageBox.warning(
                    self, "Warning", 
                    "API key works but audio data seems small. Check your configuration."
                )
                
        except Exception as e:
            # Handle different types of API errors
            error_msg = str(e)
            
            if "403" in error_msg or "Invalid API key" in error_msg:
                QMessageBox.critical(self, "Error", "Invalid API key or access denied")
            elif "429" in error_msg or "Rate limited" in error_msg:
                QMessageBox.warning(
                    self, "Rate Limited", 
                    "Rate limited. API key is likely valid, try again later."
                )
            else:
                QMessageBox.critical(self, "Error", f"API test failed:\n{error_msg}")
        
        finally:
            # Restore original config
            self.tts.config = original_config
    
    def cleanup_cache(self):
        """Clean up expired cache files and show results."""
        try:
            # Perform cache cleanup
            cleaned = self.tts.cleanup_cache()
            
            # Show results to user
            if cleaned > 0:
                QMessageBox.information(
                    self, "Cache Cleanup", 
                    f"Cleaned up {cleaned} expired cache files."
                )
            else:
                QMessageBox.information(
                    self, "Cache Cleanup", 
                    "No expired cache files found."
                )
                
        except Exception as e:
            # Show error if cleanup fails
            QMessageBox.warning(self, "Error", f"Cache cleanup failed: {e}")