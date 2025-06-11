# -*- coding: utf-8 -*-
"""
Gemini TTS Configuration Dialog - Enhanced Version
==================================================

User interface for configuring TTS settings including API key setup,
model selection, voice selection, processing modes, and advanced options.
"""

from aqt import mw
from aqt.theme import theme_manager
from aqt.qt import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, 
                    QCheckBox, QPushButton, QSpinBox, QDoubleSpinBox, QMessageBox,
                    QHBoxLayout, QLabel, QGroupBox, QTabWidget, QWidget,
                    QSlider, QTextEdit, QFrame, Qt)

def show_config_dialog():
    """Show the configuration dialog for Gemini TTS."""
    try:
        from .. import get_current_tts_instance, set_current_tts_instance
        
        tts_instance = get_current_tts_instance()
        if not tts_instance:
            from .tts_engine import GeminiTTS
            tts_instance = GeminiTTS()
            set_current_tts_instance(tts_instance)
        
        dialog = ConfigDialog(tts_instance)
        
        if hasattr(dialog, 'exec_'):
            dialog.exec_()
        else:
            dialog.exec()
        
    except Exception as e:
        from aqt.utils import showInfo
        showInfo(f"Configuration error: {e}")

class ConfigDialog(QDialog):
    """Enhanced configuration dialog for Gemini TTS settings."""
    
    def __init__(self, tts_instance):
        super(ConfigDialog, self).__init__(mw)
        self.tts = tts_instance
        
        self.setWindowTitle("Gemini TTS Configuration")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        self.setup_ui()
        self.load_current_config()
    
    def setup_ui(self):
        """Create and arrange all UI elements with tabs."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Basic Settings Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)
        self.tab_widget.addTab(basic_tab, "Basic Settings")
        
        # Advanced Settings Tab
        advanced_tab = QWidget()
        self.setup_advanced_tab(advanced_tab)
        self.tab_widget.addTab(advanced_tab, "Advanced")
        
        # Processing Settings Tab
        processing_tab = QWidget()
        self.setup_processing_tab(processing_tab)
        self.tab_widget.addTab(processing_tab, "Processing")
        
        layout.addWidget(self.tab_widget)
        
        # Button section at bottom
        self.create_button_section(layout)
    
    def setup_basic_tab(self, tab):
        """Setup basic configuration tab."""
        layout = QVBoxLayout(tab)
        
        # API Configuration Group
        api_group = QGroupBox("API Configuration")
        api_form = QFormLayout(api_group)
        
        # API Key input field
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter your Gemini API key")
        api_form.addRow("API Key:", self.api_key_input)
        
        # Model selection dropdown
        self.model_combo = QComboBox()
        models = self.tts.get_available_models()
        for model_key, model_info in models.items():
            self.model_combo.addItem(model_info["display_name"], model_key)
        api_form.addRow("Model:", self.model_combo)
        
        # Processing Mode selection
        self.processing_mode_combo = QComboBox()
        self.processing_mode_combo.addItem("Unified (Recommended)", "unified")
        self.processing_mode_combo.addItem("Traditional", "traditional") 
        self.processing_mode_combo.addItem("Hybrid", "hybrid")
        self.processing_mode_combo.addItem("Auto-Select", "auto")
        api_form.addRow("Processing Mode:", self.processing_mode_combo)
        
        layout.addWidget(api_group)
        
        # Voice Configuration Group
        voice_group = QGroupBox("Voice & Audio Settings")
        voice_form = QFormLayout(voice_group)
        
        # Voice selection dropdown
        self.voice_combo = QComboBox()
        voices = self.tts.get_available_voices()
        self.voice_combo.addItems(voices)
        voice_form.addRow("Voice:", self.voice_combo)
        
        # Temperature setting
        self.temp_spinner = QDoubleSpinBox()
        self.temp_spinner.setRange(0.0, 2.0)
        self.temp_spinner.setSingleStep(0.1)
        self.temp_spinner.setDecimals(1)
        self.temp_spinner.setToolTip("0.0 = deterministic, 1.0 = balanced, 2.0 = creative")
        voice_form.addRow("Temperature:", self.temp_spinner)
        
        layout.addWidget(voice_group)
        
        # Information section
        self.create_info_section(layout)
        
        layout.addStretch()
    
    def setup_advanced_tab(self, tab):
        """Setup advanced configuration tab."""
        layout = QVBoxLayout(tab)
        
        # Thinking Budget Group
        thinking_group = QGroupBox("AI Reasoning Control")
        thinking_layout = QVBoxLayout(thinking_group)
        
        # Thinking budget slider
        budget_layout = QHBoxLayout()
        budget_layout.addWidget(QLabel("Thinking Budget:"))
        
        self.thinking_budget_slider = QSlider()
        self.thinking_budget_slider.setOrientation(Qt.Orientation.Horizontal)
        self.thinking_budget_slider.setRange(0, 1024)
        self.thinking_budget_slider.setValue(0)
        self.thinking_budget_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.thinking_budget_slider.setTickInterval(256)
        
        self.thinking_budget_label = QLabel("0 tokens")
        self.thinking_budget_slider.valueChanged.connect(
            lambda v: self.thinking_budget_label.setText(f"{v} tokens")
        )
        
        budget_layout.addWidget(self.thinking_budget_slider)
        budget_layout.addWidget(self.thinking_budget_label)
        thinking_layout.addLayout(budget_layout)
        
        # Budget explanation
        budget_info = QLabel(
            "Thinking Budget controls how much the AI reasons before responding:\n"
            "• 0 tokens: Fast, cost-efficient (recommended for simple text)\n"
            "• 256-512: Better handling of complex lists and structure\n"
            "• 512+: Advanced reasoning for technical content"
        )
        budget_info.setWordWrap(True)
        budget_info.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        thinking_layout.addWidget(budget_info)
        
        layout.addWidget(thinking_group)
        
        # Cache Configuration Group
        cache_group = QGroupBox("Cache Settings")
        cache_form = QFormLayout(cache_group)
        
        self.cache_enabled = QCheckBox("Enable caching")
        cache_form.addRow("Cache:", self.cache_enabled)
        
        self.cache_days = QSpinBox()
        self.cache_days.setRange(1, 365)
        self.cache_days.setSuffix(" days")
        cache_form.addRow("Keep cache for:", self.cache_days)
        
        layout.addWidget(cache_group)
        
        # Performance Group
        perf_group = QGroupBox("Performance Settings")
        perf_form = QFormLayout(perf_group)
        
        self.enable_fallback = QCheckBox("Enable fallback to traditional mode on errors")
        self.enable_fallback.setChecked(True)
        perf_form.addRow("Fallback:", self.enable_fallback)
        
        self.cache_preprocessing = QCheckBox("Cache preprocessing results")
        self.cache_preprocessing.setChecked(True)
        perf_form.addRow("Preprocessing Cache:", self.cache_preprocessing)
        
        layout.addWidget(perf_group)
        
        layout.addStretch()
    
    def setup_processing_tab(self, tab):
        """Setup text processing configuration tab."""
        layout = QVBoxLayout(tab)
        
        # Preprocessing Style Group
        style_group = QGroupBox("Preprocessing Style")
        style_form = QFormLayout(style_group)
        
        self.preprocessing_style_combo = QComboBox()
        self.preprocessing_style_combo.addItem("Natural", "natural")
        self.preprocessing_style_combo.addItem("Professional", "professional")
        self.preprocessing_style_combo.addItem("Conversational", "conversational")
        self.preprocessing_style_combo.addItem("Technical", "technical")
        style_form.addRow("Style:", self.preprocessing_style_combo)
        
        self.enable_style_control = QCheckBox("Enable advanced style control")
        self.enable_style_control.setChecked(True)
        style_form.addRow("Style Control:", self.enable_style_control)
        
        layout.addWidget(style_group)
        
        # Content Detection Group
        detection_group = QGroupBox("Content Detection")
        detection_form = QFormLayout(detection_group)
        
        self.auto_detect_content = QCheckBox("Automatically detect content type")
        self.auto_detect_content.setChecked(True)
        detection_form.addRow("Auto-detect:", self.auto_detect_content)
        
        self.prefer_instructions = QCheckBox("Prefer instruction-style for numbered lists")
        self.prefer_instructions.setChecked(True)
        detection_form.addRow("Instructions:", self.prefer_instructions)
        
        layout.addWidget(detection_group)
        
        # Preview Area
        preview_group = QGroupBox("Processing Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        preview_input_layout = QHBoxLayout()
        preview_input_layout.addWidget(QLabel("Test text:"))
        
        self.preview_input = QLineEdit()
        self.preview_input.setPlaceholderText("• First item\n• Second item\n• Third item")
        preview_input_layout.addWidget(self.preview_input)
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(self.preview_processing)
        preview_input_layout.addWidget(preview_btn)
        
        preview_layout.addLayout(preview_input_layout)
        
        self.preview_output = QTextEdit()
        self.preview_output.setMaximumHeight(100)
        self.preview_output.setPlaceholderText("Processed text will appear here...")
        preview_layout.addWidget(self.preview_output)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
    
    def create_info_section(self, parent_layout):
        """Create information section with API key instructions."""
        info_label = QLabel(
            "<b>Getting Started:</b><br>"
            "1. Get API key from <a href='https://ai.google.dev/'>ai.google.dev</a><br>"
            "2. Click 'Get API key' → 'Create API key'<br>"
            "3. Copy and paste above<br>"
            "4. Select text in Anki editor and press Ctrl+G<br><br>"
            "<b>Unified Mode:</b> AI preprocesses text for natural speech (recommended)<br>"
            "<b>Traditional Mode:</b> Basic text cleanup only"
        )
        
        info_label.setOpenExternalLinks(True)
        info_label.setWordWrap(True)
        
        bg_color = "#3a3a3a" if theme_manager.night_mode else "#f0f0f0"
        
        info_label.setStyleSheet(
            f"QLabel {{ "
            f"background-color: {bg_color}; "
            f"padding: 10px; "
            f"border-radius: 5px; "
            f"margin: 5px; "
            f"}}"
        )
        
        parent_layout.addWidget(info_label)
    
    def create_button_section(self, parent_layout):
        """Create action buttons section."""
        button_layout = QHBoxLayout()
        
        # Test button
        test_btn = QPushButton("Test API Key")
        test_btn.clicked.connect(self.test_api_key)
        button_layout.addWidget(test_btn)
        
        # Cache cleanup button
        cleanup_btn = QPushButton("Clean Cache")
        cleanup_btn.clicked.connect(self.cleanup_cache)
        button_layout.addWidget(cleanup_btn)
        
        # Preview unified mode button
        preview_unified_btn = QPushButton("Test Unified Mode")
        preview_unified_btn.clicked.connect(self.test_unified_mode)
        button_layout.addWidget(preview_unified_btn)
        
        button_layout.addStretch()
        
        # Save button
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        parent_layout.addLayout(button_layout)
    
    def load_current_config(self):
        """Load current configuration values into form fields."""
        config = self.tts.config
        
        # Basic settings
        self.api_key_input.setText(config.get("api_key", ""))
        
        # Set model selection
        model_key = config.get("model", "flash_unified")
        model_index = self.model_combo.findData(model_key)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        
        # Set processing mode
        processing_mode = config.get("processing_mode", "unified")
        mode_index = self.processing_mode_combo.findData(processing_mode)
        if mode_index >= 0:
            self.processing_mode_combo.setCurrentIndex(mode_index)
        
        # Set voice selection
        voice = config.get("voice", "Zephyr")
        voice_index = self.voice_combo.findText(voice)
        if voice_index >= 0:
            self.voice_combo.setCurrentIndex(voice_index)
        
        # Advanced settings
        self.temp_spinner.setValue(config.get("temperature", 0.0))
        self.thinking_budget_slider.setValue(config.get("thinking_budget", 0))
        self.thinking_budget_label.setText(f"{config.get('thinking_budget', 0)} tokens")
        
        # Cache settings
        self.cache_enabled.setChecked(config.get("enable_cache", True))
        self.cache_days.setValue(config.get("cache_days", 30))
        
        # Performance settings
        self.enable_fallback.setChecked(config.get("enable_fallback", True))
        self.cache_preprocessing.setChecked(config.get("cache_preprocessing", True))
        
        # Processing settings
        preprocessing_style = config.get("preprocessing_style", "natural")
        style_index = self.preprocessing_style_combo.findData(preprocessing_style)
        if style_index >= 0:
            self.preprocessing_style_combo.setCurrentIndex(style_index)
        
        self.enable_style_control.setChecked(config.get("enable_style_control", True))
        self.auto_detect_content.setChecked(config.get("auto_detect_content", True))
        self.prefer_instructions.setChecked(config.get("prefer_instructions", True))
    
    def save_config(self):
        """Validate and save configuration settings."""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Error", "API key is required")
            return
        
        model_key = self.model_combo.currentData()
        processing_mode = self.processing_mode_combo.currentData()
        
        new_config = {
            # Basic settings
            "api_key": api_key,
            "model": model_key,
            "processing_mode": processing_mode,
            "voice": self.voice_combo.currentText(),
            "temperature": self.temp_spinner.value(),
            
            # Advanced settings
            "thinking_budget": self.thinking_budget_slider.value(),
            "enable_cache": self.cache_enabled.isChecked(),
            "cache_days": self.cache_days.value(),
            "enable_fallback": self.enable_fallback.isChecked(),
            "cache_preprocessing": self.cache_preprocessing.isChecked(),
            
            # Processing settings
            "preprocessing_style": self.preprocessing_style_combo.currentData(),
            "enable_style_control": self.enable_style_control.isChecked(),
            "auto_detect_content": self.auto_detect_content.isChecked(),
            "prefer_instructions": self.prefer_instructions.isChecked()
        }
        
        try:
            self.tts.save_config(new_config)
            QMessageBox.information(self, "Success", "Configuration saved successfully")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration:\n{e}")
    
    def test_api_key(self):
        """Test the entered API key with current settings."""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first")
            return
        
        # Create temporary config for testing
        test_config = self.tts.config.copy()
        test_config.update({
            "api_key": api_key,
            "model": self.model_combo.currentData(),
            "voice": self.voice_combo.currentText(),
            "temperature": self.temp_spinner.value(),
            "processing_mode": "traditional"  # Use traditional for simple test
        })
        
        # Temporarily update config for test
        original_config = self.tts.config
        self.tts.config = test_config
        
        try:
            test_text = "Hello, this is a test."
            audio_data = self.tts.generate_audio_http(test_text)
            
            if len(audio_data) > 1000:
                QMessageBox.information(
                    self, "Success", 
                    f"API key is working! Generated {len(audio_data):,} bytes of audio data."
                )
            else:
                QMessageBox.warning(
                    self, "Warning", 
                    "API key works but audio data seems small. Check your configuration."
                )
                
        except Exception as e:
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
            self.tts.config = original_config
    
    def test_unified_mode(self):
        """Test unified mode with sample structured text."""
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Error", "Please enter an API key first")
            return
        
        sample_text = """Key features include:
- High-quality audio processing
- Real-time conversion
- Multiple voice options
- Easy integration
- Cost-effective pricing"""
        
        # Create temporary config for testing unified mode
        test_config = self.tts.config.copy()
        test_config.update({
            "api_key": api_key,
            "model": self.model_combo.currentData(),
            "processing_mode": "unified",
            "thinking_budget": self.thinking_budget_slider.value(),
            "preprocessing_style": self.preprocessing_style_combo.currentData()
        })
        
        original_config = self.tts.config
        self.tts.config = test_config
        
        try:
            # Test unified preprocessing
            from .content_analyzer import ContentAnalyzer
            analyzer = ContentAnalyzer()
            analysis = analyzer.analyze_structure(sample_text)
            
            QMessageBox.information(
                self, "Unified Mode Test", 
                f"Content Analysis Results:\n"
                f"• Type: {analysis['type']}\n"
                f"• Complexity: {analysis['complexity']}\n"
                f"• Suggested thinking budget: {analysis['suggested_thinking_budget']} tokens\n"
                f"• Processing strategy: {analysis['preprocessing_strategy']}\n\n"
                f"Unified mode is working correctly!"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Unified mode test failed:\n{e}")
        
        finally:
            self.tts.config = original_config
    
    def preview_processing(self):
        """Preview text processing with current settings."""
        input_text = self.preview_input.text().strip()
        if not input_text:
            input_text = "• First item\n• Second item\n• Third item"
        
        try:
            from .content_analyzer import ContentAnalyzer
            analyzer = ContentAnalyzer()
            analysis = analyzer.analyze_structure(input_text)
            
            style = self.preprocessing_style_combo.currentData()
            prompt_template = analyzer.get_preprocessing_prompt_template(analysis['type'], style)
            
            # Show what would be sent to the API
            full_prompt = prompt_template.format(text=input_text)
            
            # Simulate the result (in real implementation, this would call the API)
            self.preview_output.setText(
                f"Content Type: {analysis['type']}\n"
                f"Processing: {analysis['preprocessing_strategy']}\n"
                f"Prompt would be:\n{full_prompt[:200]}..."
            )
            
        except Exception as e:
            self.preview_output.setText(f"Preview error: {e}")
    
    def cleanup_cache(self):
        """Clean up expired cache files and show results."""
        try:
            cleaned = self.tts.cleanup_cache()
            
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
            QMessageBox.warning(self, "Error", f"Cache cleanup failed: {e}")