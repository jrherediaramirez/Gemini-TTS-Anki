# -*- coding: utf-8 -*-
"""
Gemini TTS Engine - FIXED VERSION
=================================

Main TTS engine using direct HTTP requests to Google's Gemini API.
Handles audio generation, caching, and integration with Anki's editor.

FIXES APPLIED:
- Race condition in cache writes (atomic writes)
- Manual HTML entity replacement (html.unescape)
- Inefficient cache cleanup (metadata tracking)
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
import html  # FIXED: Use standard library for HTML entity replacement
import tempfile
from typing import Optional, Dict, Any
from functools import partial

from aqt import mw
from aqt.qt import QTimer
from aqt.utils import tooltip

# ============================================================================
# MAIN TTS ENGINE CLASS
# ============================================================================

class GeminiTTS:
    """
    Main TTS engine class with race condition and optimization fixes.
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
    # CACHE METADATA MANAGEMENT (OPTIMIZATION FIX)
    # ========================================================================
    
    def load_cache_metadata(self) -> Dict[str, Any]:
        """
        Load cache metadata for efficient cleanup.
        
        Returns:
            Metadata dictionary with file tracking info
        """
        if not os.path.exists(self.cache_metadata_file):
            return {"version": "1.0", "files": {}}
        
        try:
            with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                # Ensure proper structure
                if "files" not in metadata:
                    metadata["files"] = {}
                return metadata
        except (json.JSONDecodeError, OSError):
            # Return empty metadata if file is corrupted
            return {"version": "1.0", "files": {}}
    
    def save_cache_metadata(self):
        """Save cache metadata to disk."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_metadata_file), exist_ok=True)
            
            # Write atomically using temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.cache_metadata_file),
                prefix='.metadata_tmp_'
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(self.cache_metadata, f, indent=2)
                
                # Atomic rename
                os.rename(temp_path, self.cache_metadata_file)
                
            except:
                # Cleanup temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except OSError:
            # Silently fail if metadata can't be saved
            pass
    
    def track_cache_file(self, cache_key: str):
        """
        Track a cache file in metadata.
        
        Args:
            cache_key: MD5 hash key for the cached file
        """
        filename = f"{cache_key}.wav"
        current_time = time.time()
        
        self.cache_metadata["files"][filename] = {
            "created": current_time,
            "accessed": current_time
        }
        
        self.save_cache_metadata()
    
    def update_cache_access(self, cache_key: str):
        """
        Update access time for cache file.
        
        Args:
            cache_key: MD5 hash key for the accessed file
        """
        filename = f"{cache_key}.wav"
        
        if filename in self.cache_metadata["files"]:
            self.cache_metadata["files"][filename]["accessed"] = time.time()
            self.save_cache_metadata()
    
    # ========================================================================
    # CACHE MANAGEMENT SYSTEM (WITH FIXES)
    # ========================================================================
    
    def create_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            if not self.cache_dir.startswith(mw.col.media.dir()):
                raise ValueError("Security error: Cache directory outside media folder")
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError:
            pass
    
    def get_cache_key(self, text: str, voice: str) -> str:
        """Generate unique cache key for text and voice combination."""
        normalized_text = text.strip().lower()
        content = f"{normalized_text}:{voice}:{self.config.get('temperature', 0.0)}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached_audio(self, cache_key: str) -> Optional[str]:
        """
        Check if audio is cached and not expired (OPTIMIZED).
        
        Args:
            cache_key: MD5 hash key for cached audio
            
        Returns:
            Filename if cached audio exists and is valid, None otherwise
        """
        if not self.config.get("enable_cache", True):
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        if not cache_file.startswith(self.cache_dir):
            return None
        
        # Check metadata first (OPTIMIZATION: avoid file system calls)
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
        """
        Cache audio data to disk with atomic writes (RACE CONDITION FIX).
        
        Args:
            cache_key: MD5 hash key for caching
            audio_data: WAV audio data to cache
        """
        if not self.config.get("enable_cache", True):
            return
        
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        if not cache_file.startswith(self.cache_dir):
            return
        
        try:
            # RACE CONDITION FIX: Use atomic writes with temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.cache_dir,
                prefix=f'.cache_tmp_{cache_key[:8]}_',
                suffix='.wav'
            )
            
            try:
                # Write to temporary file
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(audio_data)
                
                # Atomic rename to final location
                os.rename(temp_path, cache_file)
                
                # Track in metadata
                self.track_cache_file(cache_key)
                
            except:
                # Cleanup temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
                
        except OSError:
            # Silently fail if we can't write to cache
            pass
    
    def cleanup_cache(self) -> int:
        """
        Clean up expired cache files (OPTIMIZED with metadata).
        
        Returns:
            Number of files cleaned up
        """
        if not os.path.exists(self.cache_dir):
            return 0
        
        cleaned = 0
        max_age = self.config.get("cache_days", 30) * 24 * 3600
        current_time = time.time()
        
        # OPTIMIZATION: Check metadata first, only access filesystem when necessary
        files_to_remove = []
        
        for filename, file_info in self.cache_metadata["files"].items():
            file_age = current_time - file_info["created"]
            if file_age > max_age:
                files_to_remove.append(filename)
        
        # Remove expired files
        for filename in files_to_remove:
            file_path = os.path.join(self.cache_dir, filename)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned += 1
            except OSError:
                pass
            
            # Remove from metadata
            if filename in self.cache_metadata["files"]:
                del self.cache_metadata["files"][filename]
        
        # Clean up orphaned temporary files (from failed atomic writes)
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('.cache_tmp_') and filename.endswith('.wav'):
                    temp_path = os.path.join(self.cache_dir, filename)
                    try:
                        # Remove temp files older than 1 hour
                        if current_time - os.path.getmtime(temp_path) > 3600:
                            os.remove(temp_path)
                            cleaned += 1
                    except OSError:
                        pass
        except OSError:
            pass
        
        # Save updated metadata
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
        
        voice = self.config.get("voice", "Zephyr")
        temperature = self.config.get("temperature", 0.0)
        
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash-preview-tts:generateContent?key={api_key}")
        
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
        
        cache_key = self.get_cache_key(text, self.config.get("voice", "Zephyr"))
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
    # TEXT PROCESSING AND NORMALIZATION (HTML ENTITY FIX)
    # ========================================================================
    
    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize text for TTS processing (FIXED HTML entities).
        
        Args:
            text: Raw text from editor selection
            
        Returns:
            Cleaned text suitable for TTS API
        """
        if not text:
            return ""
        
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # FIXED: Use html.unescape() instead of manual dictionary
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
            
            button = editor.addButton(
                icon=use_icon,
                cmd="gemini_tts",
                tip="Generate Gemini TTS (Ctrl+G)",
                func=lambda ed: self.on_button_click(ed),
                keys="Ctrl+G"
            )
            
            buttons.append(button)
            
        except Exception as e:
            print(f"Gemini TTS: Button setup error - {e}")
        
        return buttons
    
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
                tooltip("Audio generated successfully")
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
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_available_voices(self):
        """Get list of available Gemini TTS voices."""
        return [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
            "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
            "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
            "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
            "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ]