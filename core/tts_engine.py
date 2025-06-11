# -*- coding: utf-8 -*-
"""
Gemini TTS Engine - Enhanced with Model Selection
=================================================

Main TTS engine using direct HTTP requests to Google's Gemini API.
Handles audio generation, caching, model selection, and integration with Anki's editor.

ENHANCEMENTS:
- Model selection (Flash vs Pro)
- Voice validation
- Enhanced editor UI with model and voice dropdowns
"""

import os
import json
import base64
import hashlib
import time
import struct
import urllib.request
import urllib.parse
import urllib.error
import html
import tempfile
from typing import Optional, Dict, Any
from functools import partial

from aqt import mw
from aqt.qt import QTimer, QComboBox, QHBoxLayout, QLabel
from aqt.utils import tooltip

# ============================================================================
# MAIN TTS ENGINE CLASS
# ============================================================================

class GeminiTTS:
    """
    Main TTS engine class with model selection and enhanced UI.
    """
    
    def __init__(self):
        """Initialize the TTS engine with configuration and cache setup."""
        self.config = self.load_config()
        self.cache_dir = os.path.join(mw.col.media.dir(), ".gemini_cache")
        self.cache_metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")
        self.create_cache_dir()
        self.cache_metadata = self.load_cache_metadata()
    
    # ========================================================================
    # CONFIGURATION MANAGEMENT
    # ========================================================================
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from Anki with sensible defaults."""
        defaults = {
            "api_key": "",
            "model": "flash",
            "voice": "Zephyr",
            "enable_cache": True,
            "cache_days": 30,
            "temperature": 0.0
        }
        
        try:
            saved = mw.col.get_config("gemini_tts", {})
        except AttributeError:
            saved = mw.col.conf.get("gemini_tts", {})
        
        defaults.update(saved)
        return defaults
    
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to Anki."""
        try:
            mw.col.set_config("gemini_tts", config)
        except AttributeError:
            mw.col.conf["gemini_tts"] = config
        self.config = config
    
    # ========================================================================
    # MODEL AND VOICE MANAGEMENT
    # ========================================================================
    
    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get available TTS models with their metadata."""
        return {
            "flash": {
                "model_id": "gemini-2.5-flash-preview-tts",
                "display_name": "Gemini 2.5 Flash",
                "description": "Fast and cost-effective"
            },
            "pro": {
                "model_id": "gemini-2.5-pro-preview-tts",
                "display_name": "Gemini 2.5 Pro", 
                "description": "Higher quality audio"
            }
        }
    
    def get_current_model_id(self) -> str:
        """Get the full model ID for the currently selected model."""
        models = self.get_available_models()
        model_key = self.config.get("model", "flash")
        return models[model_key]["model_id"]
    
    def get_available_voices(self):
        """Get list of available Gemini TTS voices."""
        return [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
            "Callirhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", 
            "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
            "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
            "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ]
    
    def validate_current_settings(self) -> tuple[bool, str]:
        """
        Validate current model and voice settings.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Test with minimal text
            test_audio = self.generate_audio_http("test")
            return len(test_audio) > 1000, ""
        except Exception as e:
            return False, str(e)
    
    # ========================================================================
    # FIELD DETECTION
    # ========================================================================
    
    def detect_source_field(self, editor):
        """Detect which field the user is currently working in."""
        if not (editor and hasattr(editor, 'note') and editor.note):
            return "Front"
        
        if hasattr(editor, 'currentField') and editor.currentField is not None:
            field_names = list(editor.note.keys())
            if 0 <= editor.currentField < len(field_names):
                return field_names[editor.currentField]
        
        field_names = list(editor.note.keys())
        return field_names[0] if field_names else "Front"
    
    # ========================================================================
    # CACHE METADATA MANAGEMENT
    # ========================================================================
    
    def load_cache_metadata(self) -> Dict[str, Any]:
        """Load cache metadata for efficient cleanup."""
        if not os.path.exists(self.cache_metadata_file):
            return {"version": "1.0", "files": {}}
        
        try:
            with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if "files" not in metadata:
                    metadata["files"] = {}
                return metadata
        except (json.JSONDecodeError, OSError):
            return {"version": "1.0", "files": {}}
    
    def save_cache_metadata(self):
        """Save cache metadata to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_metadata_file), exist_ok=True)
            
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.cache_metadata_file),
                prefix='.metadata_tmp_'
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(self.cache_metadata, f, indent=2)
                
                os.rename(temp_path, self.cache_metadata_file)
                
            except:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except OSError:
            pass
    
    def track_cache_file(self, cache_key: str):
        """Track a cache file in metadata."""
        filename = f"{cache_key}.wav"
        current_time = time.time()
        
        self.cache_metadata["files"][filename] = {
            "created": current_time,
            "accessed": current_time
        }
        
        self.save_cache_metadata()
    
    def update_cache_access(self, cache_key: str):
        """Update access time for cache file."""
        filename = f"{cache_key}.wav"
        
        if filename in self.cache_metadata["files"]:
            self.cache_metadata["files"][filename]["accessed"] = time.time()
            self.save_cache_metadata()
    
    # ========================================================================
    # CACHE MANAGEMENT SYSTEM
    # ========================================================================
    
    def create_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            if not self.cache_dir.startswith(mw.col.media.dir()):
                raise ValueError("Security error: Cache directory outside media folder")
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError:
            pass
    
    def get_cache_key(self, text: str, voice: str, model: str) -> str:
        """Generate unique cache key for text, voice, and model combination."""
        normalized_text = text.strip().lower()
        content = f"{normalized_text}:{voice}:{model}:{self.config.get('temperature', 0.0)}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached_audio(self, cache_key: str) -> Optional[str]:
        """Check if audio is cached and not expired."""
        if not self.config.get("enable_cache", True):
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        if not cache_file.startswith(self.cache_dir):
            return None
        
        # Check metadata first
        filename = f"{cache_key}.wav"
        if filename in self.cache_metadata["files"]:
            file_info = self.cache_metadata["files"][filename]
            file_age = time.time() - file_info["created"]
            max_age = self.config.get("cache_days", 30) * 24 * 3600
            
            if file_age > max_age:
                # Remove from metadata and filesystem
                del self.cache_metadata["files"][filename]
                self.save_cache_metadata()
                try:
                    os.remove(cache_file)
                except OSError:
                    pass
                return None
        
        # Verify file actually exists
        if not os.path.exists(cache_file):
            # Remove stale metadata entry
            if filename in self.cache_metadata["files"]:
                del self.cache_metadata["files"][filename]
                self.save_cache_metadata()
            return None
        
        # Update access time
        self.update_cache_access(cache_key)
        
        # Copy cached file to media collection with unique name
        timestamp = int(time.time())
        dest_filename = f"gemini_tts_{cache_key[:8]}_{timestamp}.wav"
        dest_path = os.path.join(mw.col.media.dir(), dest_filename)
        
        if not dest_path.startswith(mw.col.media.dir()):
            return None
        
        try:
            with open(cache_file, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            return dest_filename
        except OSError:
            return None
    
    def cache_audio(self, cache_key: str, audio_data: bytes):
        """Cache audio data to disk with atomic writes."""
        if not self.config.get("enable_cache", True):
            return
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        if not cache_file.startswith(self.cache_dir):
            return
        
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.cache_dir,
                prefix=f'.cache_tmp_{cache_key[:8]}_',
                suffix='.wav'
            )
            
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(audio_data)
                
                os.rename(temp_path, cache_file)
                self.track_cache_file(cache_key)
                
            except:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except OSError:
            pass
    
    def cleanup_cache(self) -> int:
        """Clean up expired cache files."""
        if not os.path.exists(self.cache_dir):
            return 0
        
        cleaned = 0
        max_age = self.config.get("cache_days", 30) * 24 * 3600
        current_time = time.time()
        
        files_to_remove = []
        
        for filename, file_info in self.cache_metadata["files"].items():
            file_age = current_time - file_info["created"]
            if file_age > max_age:
                files_to_remove.append(filename)
        
        for filename in files_to_remove:
            file_path = os.path.join(self.cache_dir, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned += 1
            except OSError:
                pass
            
            if filename in self.cache_metadata["files"]:
                del self.cache_metadata["files"][filename]
        
        # Clean up orphaned temporary files
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('.cache_tmp_') and filename.endswith('.wav'):
                    temp_path = os.path.join(self.cache_dir, filename)
                    try:
                        if current_time - os.path.getmtime(temp_path) > 3600:
                            os.remove(temp_path)
                            cleaned += 1
                    except OSError:
                        pass
        except OSError:
            pass
        
        if files_to_remove:
            self.save_cache_metadata()
        
        return cleaned
    
    # ========================================================================
    # AUDIO GENERATION AND PROCESSING
    # ========================================================================
    
    def generate_audio_http(self, text: str) -> bytes:
        """Generate audio using direct HTTP request to Gemini API."""
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise ValueError("API key not configured")
        
        model_id = self.get_current_model_id()
        voice = self.config.get("voice", "Zephyr")
        temperature = self.config.get("temperature", 0.0)
        
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model_id}:generateContent?key={api_key}")
        
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                }
            }
        }
        
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
            
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise ValueError("Invalid request - check API key and text")
            elif e.code == 403:
                raise ValueError("Invalid API key or access denied")
            elif e.code == 429:
                raise ValueError("Rate limited - please wait and try again")
            else:
                raise ValueError(f"API error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ValueError(f"Network error: {e.reason}")
        except json.JSONDecodeError:
            raise ValueError("Invalid response from API")
        
        try:
            candidates = response_data.get('candidates', [])
            if not candidates:
                raise ValueError("No audio generated")
            
            parts = candidates[0].get('content', {}).get('parts', [])
            if not parts:
                raise ValueError("No audio data in response")
            
            inline_data = parts[0].get('inlineData', {})
            audio_b64 = inline_data.get('data', '')
            
            if not audio_b64:
                raise ValueError("No audio data received")
            
            audio_data = base64.b64decode(audio_b64)
            mime_type = inline_data.get('mimeType', 'audio/L16;rate=24000')
            wav_data = self.convert_to_wav(audio_data, mime_type)
            
            return wav_data
            
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response format: {e}")
    
    def convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """Convert raw audio data to WAV format."""
        sample_rate = 24000
        if 'rate=' in mime_type:
            try:
                rate_str = mime_type.split('rate=')[1].split(';')[0]
                sample_rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        
        channels = 1
        bits_per_sample = 16
        bytes_per_sample = bits_per_sample // 8
        byte_rate = sample_rate * channels * bytes_per_sample
        block_align = channels * bytes_per_sample
        data_size = len(audio_data)
        
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16, 1, channels,
            sample_rate, byte_rate, block_align, bits_per_sample,
            b'data', data_size
        )
        
        return header + audio_data
    
    def generate_audio(self, text: str) -> str:
        """Main audio generation method with caching."""
        text = text.strip()
        if not text:
            raise ValueError("No text provided")
        
        text = text.replace('\x00', '')
        
        if len(text) > 5000:
            raise ValueError("Text too long (max 5000 characters)")
        
        model_key = self.config.get("model", "flash")
        voice = self.config.get("voice", "Zephyr")
        cache_key = self.get_cache_key(text, voice, model_key)
        cached_filename = self.get_cached_audio(cache_key)
        if cached_filename:
            return cached_filename
        
        audio_data = self.generate_audio_http(text)
        
        timestamp = int(time.time())
        filename = f"gemini_tts_{cache_key[:8]}_{timestamp}.wav"
        
        file_path = os.path.join(mw.col.media.dir(), filename)
        if not file_path.startswith(mw.col.media.dir()):
            raise ValueError("Security error: Invalid file path")
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        self.cache_audio(cache_key, audio_data)
        
        return filename
    
    # ========================================================================
    # TEXT PROCESSING AND NORMALIZATION
    # ========================================================================
    
    def normalize_text(self, text: str) -> str:
        """Clean and normalize text for TTS processing."""
        if not text:
            return ""
        
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Unescape HTML entities
        text = html.unescape(text)
        
        # Handle bullet points and list markers
        bullet_patterns = [
            r'^[\s]*[•·‣⁃▪▫‧◦⦾⦿]\s*',
            r'^[\s]*[-*+]\s*',
            r'^[\s]*\d+[.)]\s*',
            r'^[\s]*[a-zA-Z][.)]\s*',
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for pattern in bullet_patterns:
                line = re.sub(pattern, '', line, flags=re.MULTILINE)
                line = line.strip()
            
            if line:
                cleaned_lines.append(line)
        
        text = ' '.join(cleaned_lines)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Normalize whitespace characters
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2000', ' ')  # En quad
        text = text.replace('\u2001', ' ')  # Em quad
        text = text.replace('\u2002', ' ')  # En space
        text = text.replace('\u2003', ' ')  # Em space
        text = text.replace('\u2009', ' ')  # Thin space
        text = text.replace('\u200b', '')   # Zero-width space
        
        return text
    
    # ========================================================================
    # ANKI EDITOR INTEGRATION
    # ========================================================================
    
    def add_audio_to_note(self, editor, filename: str):
        """Add generated audio to the detected source field in Anki note."""
        target_field = self.detect_source_field(editor)
        
        if target_field not in editor.note:
            tooltip(f"Field '{target_field}' not found")
            return False
        
        sound_tag = f"[sound:{filename}]"
        current_content = editor.note[target_field]
        
        if sound_tag not in current_content:
            if current_content.strip():
                editor.note[target_field] = f"{current_content} {sound_tag}"
            else:
                editor.note[target_field] = sound_tag
        
        editor.loadNote()
        QTimer.singleShot(100, lambda: self.focus_editor(editor))
        return True
    
    def focus_editor(self, editor):
        """Restore focus to editor web view."""
        try:
            if hasattr(editor, 'web') and hasattr(editor.web, 'setFocus'):
                editor.web.setFocus()
        except:
            pass
    
    def setup_editor_button(self, buttons, editor):
        """Add TTS button to editor toolbar."""
        try:
            addon_dir = os.path.dirname(os.path.dirname(__file__))
            icon_path = os.path.join(addon_dir, "icons", "gemini.png")
            use_icon = icon_path if os.path.exists(icon_path) else None
            
            # Create main TTS button with current settings in tooltip
            current_model = self.get_available_models()[self.config.get("model", "flash")]["display_name"]
            current_voice = self.config.get("voice", "Zephyr")
            tip = f"Generate Gemini TTS (Ctrl+G)\nModel {current_model}\nVoice {current_voice}"
            
            button = editor.addButton(
                icon=use_icon,
                cmd="gemini_tts",
                tip=tip,
                func=lambda ed: self.on_button_click(ed),
                keys="Ctrl+G"
            )
            
            # Add model selection button
            model_button = editor.addButton(
                None,
                cmd="gemini_model",
                tip=f"Select Gemini TTS Model (Current: {current_model})",
                func=lambda ed: self.show_model_menu(ed),
                label="Model"
            )
            
            # Add voice selection button  
            voice_button = editor.addButton(
                None,
                cmd="gemini_voice", 
                tip=f"Select Gemini TTS Voice (Current: {current_voice})",
                func=lambda ed: self.show_voice_menu(ed),
                label="Voice"
            )
            
            buttons.append(button)
            buttons.append(model_button)
            buttons.append(voice_button)
            
        except Exception as e:
            print(f"Gemini TTS: Button setup error - {e}")
        
        return buttons
    
    def show_model_menu(self, editor):
        """Show model selection menu."""
        from aqt.qt import QMenu, QCursor
        
        menu = QMenu(editor.widget)
        models = self.get_available_models()
        current_model = self.config.get("model", "flash")
        
        for model_key, model_info in models.items():
            action = menu.addAction(model_info["display_name"])
            action.setCheckable(True)
            action.setChecked(model_key == current_model)
            action.triggered.connect(lambda checked, mk=model_key: self.change_model(mk, editor))
        
        # Show menu at mouse cursor position
        menu.exec(QCursor.pos())
    
    def show_voice_menu(self, editor):
        """Show voice selection menu."""
        from aqt.qt import QMenu, QCursor
        
        menu = QMenu(editor.widget)
        voices = self.get_available_voices()
        current_voice = self.config.get("voice", "Zephyr")
        
        for voice in voices:
            action = menu.addAction(voice)
            action.setCheckable(True)
            action.setChecked(voice == current_voice)
            action.triggered.connect(lambda checked, v=voice: self.change_voice(v, editor))
        
        # Show menu at mouse cursor position
        menu.exec(QCursor.pos())
    
    def change_model(self, model_key, editor):
        """Change model and update button label."""
        config = self.config.copy()
        config["model"] = model_key
        self.save_config(config)
        tooltip(f"Model changed to {self.get_available_models()[model_key]['display_name']}")
    
    def change_voice(self, voice, editor):
        """Change voice and update button label."""
        config = self.config.copy()
        config["voice"] = voice
        self.save_config(config)
        tooltip(f"Voice changed to {voice}")
    
    def on_model_changed(self, combo):
        """Handle model selection change."""
        model_key = combo.currentData()
        if model_key:
            config = self.config.copy()
            config["model"] = model_key
            self.save_config(config)
    
    def on_voice_changed(self, combo):
        """Handle voice selection change."""
        voice_text = combo.currentText()
        if voice_text.startswith("Voice: "):
            voice = voice_text[7:]  # Remove "Voice: " prefix
            config = self.config.copy()
            config["voice"] = voice
            self.save_config(config)
    
    # ========================================================================
    # USER INTERACTION HANDLERS
    # ========================================================================
    
    def on_button_click(self, editor):
        """Handle TTS button click in editor."""
        js_code = """
        (function() {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                const container = document.createElement('div');
                container.appendChild(range.cloneContents());
                return {
                    plainText: selection.toString(),
                    htmlContent: container.innerHTML,
                    hasContent: selection.toString().length > 0
                };
            }
            return {
                plainText: '',
                htmlContent: '',
                hasContent: false
            };
        })();
        """
        
        editor.web.evalWithCallback(js_code, partial(self.process_selection_result, editor))
    
    def process_selection_result(self, editor, result):
        """Process the selection result from JavaScript."""
        if not result.get('hasContent', False):
            tooltip("Please select some text first")
            return
        
        raw_text = result.get('plainText', '') or result.get('htmlContent', '')
        
        if not raw_text.strip():
            tooltip("No readable text found in selection")
            return
        
        cleaned_text = self.normalize_text(raw_text)
        
        if not cleaned_text.strip():
            tooltip("Selected text cannot be converted to speech")
            return
        
        self.process_selected_text(editor, cleaned_text)
    
    def process_selected_text(self, editor, selected_text):
        """Process selected text for TTS generation."""
        if not self.config.get("api_key", "").strip():
            tooltip("Please configure API key first")
            return
        
        tooltip("Generating TTS audio...")
        QTimer.singleShot(100, lambda: self.generate_and_add_audio(editor, selected_text))
    
    def generate_and_add_audio(self, editor, text):
        """Generate audio and add to note (non-blocking operation)."""
        try:
            filename = self.generate_audio(text)
            
            if self.add_audio_to_note(editor, filename):
                current_model = self.get_available_models()[self.config.get("model", "flash")]["display_name"]
                current_voice = self.config.get("voice", "Zephyr")
                tooltip(f"Audio generated with {current_model} - {current_voice}")
            else:
                tooltip("Failed to add audio to note")
                
        except Exception as e:
            error_msg = str(e)
            
            if "API key" in error_msg:
                tooltip("Invalid API key - check configuration")
            elif "Rate limited" in error_msg:
                tooltip("Rate limited - wait and try again")
            elif "Network error" in error_msg:
                tooltip("Network error - check connection")
            else:
                tooltip(f"Error: {error_msg[:50]}...")