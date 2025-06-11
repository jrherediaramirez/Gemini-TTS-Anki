# -*- coding: utf-8 -*-
"""
Gemini TTS Engine
=================

Main TTS engine using direct HTTP requests to Google's Gemini API.
Handles audio generation, caching, and integration with Anki's editor.

Features:
- Zero external dependencies (uses only Python standard library)
- Multi-language support for all Unicode text
- Intelligent caching to reduce API costs
- Secure file operations within Anki's media directory
- Automatic field detection for audio placement
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
    Main TTS engine class.
    
    This class handles all TTS functionality including:
    - Configuration management
    - Audio generation via Gemini API
    - Caching system for cost optimization
    - Integration with Anki's editor
    - Automatic field detection for audio placement
    """
    
    def __init__(self):
        """Initialize the TTS engine with configuration and cache setup."""
        self.config = self.load_config()
        self.cache_dir = os.path.join(mw.col.media.dir(), ".gemini_cache")
        self.create_cache_dir()
    
    # ========================================================================
    # CONFIGURATION MANAGEMENT
    # ========================================================================
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from Anki with sensible defaults.
        
        Returns:
            Configuration dictionary with all required settings
        """
        # Define default configuration values
        defaults = {
            "api_key": "",              # User's Gemini API key
            "voice": "Zephyr",          # Default voice (gentle and flowing)
            "enable_cache": True,       # Enable caching to reduce API costs
            "cache_days": 30,          # Keep cached audio for 30 days
            "temperature": 0.0         # Deterministic output (0.0-1.0 range)
        }
        
        try:
            # Try new Anki configuration method
            saved = mw.col.get_config("gemini_tts", {})
        except AttributeError:
            # Fallback for older Anki versions
            saved = mw.col.conf.get("gemini_tts", {})
        
        # Merge saved settings with defaults
        defaults.update(saved)
        return defaults
    
    def save_config(self, config: Dict[str, Any]):
        """
        Save configuration to Anki.
        
        Args:
            config: Configuration dictionary to save
        """
        try:
            # Try new Anki configuration method
            mw.col.set_config("gemini_tts", config)
        except AttributeError:
            # Fallback for older Anki versions
            mw.col.conf["gemini_tts"] = config
        
        # Update current configuration
        self.config = config
    
    # ========================================================================
    # FIELD DETECTION
    # ========================================================================
    
    def detect_source_field(self, editor):
        """
        Detect which field the user is currently working in.
        
        Args:
            editor: Anki editor instance
            
        Returns:
            Field name where audio should be placed
        """
        if not (editor and hasattr(editor, 'note') and editor.note):
            return "Front"
        
        # Use editor.currentField index to determine active field
        if hasattr(editor, 'currentField') and editor.currentField is not None:
            field_names = list(editor.note.keys())
            if 0 <= editor.currentField < len(field_names):
                return field_names[editor.currentField]
        
        # Fallback: Return first available field
        field_names = list(editor.note.keys())
        return field_names[0] if field_names else "Front"
    
    # ========================================================================
    # CACHE MANAGEMENT SYSTEM
    # ========================================================================
    
    def create_cache_dir(self):
        """
        Create cache directory if it doesn't exist.
        
        Cache is stored in a hidden folder within Anki's media directory
        to keep it organized and ensure proper cleanup.
        """
        try:
            # Security check: ensure cache directory is within media directory
            if not self.cache_dir.startswith(mw.col.media.dir()):
                raise ValueError("Security error: Cache directory outside media folder")
            
            # Create directory with exist_ok=True (won't error if already exists)
            os.makedirs(self.cache_dir, exist_ok=True)
            
        except OSError:
            # Silently fail if we can't create cache directory
            # TTS will still work, just without caching
            pass
    
    def get_cache_key(self, text: str, voice: str) -> str:
        """
        Generate unique cache key for text and voice combination.
        
        Args:
            text: Text to be converted to speech
            voice: Voice name to use
            
        Returns:
            MD5 hash string for use as cache key
        """
        # Normalize text for consistent caching across languages
        normalized_text = text.strip().lower()
        
        # Include voice and temperature in cache key to ensure correct caching
        content = f"{normalized_text}:{voice}:{self.config.get('temperature', 0.0)}"
        
        # Use UTF-8 encoding to properly handle all Unicode characters
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached_audio(self, cache_key: str) -> Optional[str]:
        """
        Check if audio is cached and not expired.
        
        Args:
            cache_key: MD5 hash key for cached audio
            
        Returns:
            Filename if cached audio exists and is valid, None otherwise
        """
        # Skip if caching is disabled
        if not self.config.get("enable_cache", True):
            return None
        
        # Cache key is MD5 hash - already safe, no sanitization needed
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        # Security check - ensure path stays in cache directory
        if not cache_file.startswith(self.cache_dir):
            return None
        
        # Check if cache file exists
        if not os.path.exists(cache_file):
            return None
        
        # Check if cache has expired
        try:
            file_age = time.time() - os.path.getmtime(cache_file)
            max_age = self.config.get("cache_days", 30) * 24 * 3600
            
            if file_age > max_age:
                # Remove expired cache file
                os.remove(cache_file)
                return None
                
        except OSError:
            # If we can't check file age, assume it's invalid
            return None
        
        # Copy cached file to media collection with unique name
        timestamp = int(time.time())
        filename = f"gemini_tts_{cache_key[:8]}_{timestamp}.wav"
        dest_path = os.path.join(mw.col.media.dir(), filename)
        
        # Security check: ensure destination is in media directory
        if not dest_path.startswith(mw.col.media.dir()):
            return None
        
        try:
            # Copy cached audio to media collection
            with open(cache_file, 'rb') as src, open(dest_path, 'wb') as dst:
                dst.write(src.read())
            return filename
            
        except OSError:
            # If copy fails, return None (will regenerate audio)
            return None
    
    def cache_audio(self, cache_key: str, audio_data: bytes):
        """
        Cache audio data to disk for future use.
        
        Args:
            cache_key: MD5 hash key for caching
            audio_data: WAV audio data to cache
        """
        # Skip if caching is disabled
        if not self.config.get("enable_cache", True):
            return
        
        # Cache key is MD5 hash - already safe, no sanitization needed
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
        
        # Security check: ensure file stays in cache directory
        if not cache_file.startswith(self.cache_dir):
            return  # Silently fail for security
        
        try:
            # Write audio data to cache file
            with open(cache_file, 'wb') as f:
                f.write(audio_data)
                
        except OSError:
            # Silently fail if we can't write to cache
            # TTS will still work, just without caching benefit
            pass
    
    def cleanup_cache(self) -> int:
        """
        Clean up expired cache files.
        
        Returns:
            Number of files cleaned up
        """
        if not os.path.exists(self.cache_dir):
            return 0
        
        cleaned = 0
        max_age = self.config.get("cache_days", 30) * 24 * 3600
        current_time = time.time()
        
        try:
            # Iterate through all files in cache directory
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.wav'):
                    file_path = os.path.join(self.cache_dir, filename)
                    
                    try:
                        # Check if file is expired
                        if current_time - os.path.getmtime(file_path) > max_age:
                            os.remove(file_path)
                            cleaned += 1
                            
                    except OSError:
                        # Skip files we can't process
                        pass
                        
        except OSError:
            # If we can't read cache directory, return 0
            pass
        
        return cleaned
    
    # ========================================================================
    # AUDIO GENERATION AND PROCESSING
    # ========================================================================
    
    def generate_audio_http(self, text: str) -> bytes:
        """
        Generate audio using direct HTTP request to Gemini API.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            WAV audio data as bytes
            
        Raises:
            ValueError: If API request fails or configuration is invalid
        """
        # Validate API key
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise ValueError("API key not configured")
        
        # Get voice and temperature settings
        voice = self.config.get("voice", "Zephyr")
        temperature = self.config.get("temperature", 0.0)
        
        # Construct API endpoint URL
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-2.5-flash-preview-tts:generateContent?key={api_key}")
        
        # Prepare request payload
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
        
        # Make HTTP request to Gemini API
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
            
        except urllib.error.HTTPError as e:
            # Handle specific HTTP error codes with user-friendly messages
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
        
        # Extract audio data from API response
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
            
            # Decode base64 audio data
            audio_data = base64.b64decode(audio_b64)
            
            # Convert to WAV format
            mime_type = inline_data.get('mimeType', 'audio/L16;rate=24000')
            wav_data = self.convert_to_wav(audio_data, mime_type)
            
            return wav_data
            
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response format: {e}")
    
    def convert_to_wav(self, audio_data: bytes, mime_type: str) -> bytes:
        """
        Convert raw audio data to WAV format.
        
        Args:
            audio_data: Raw audio bytes from API
            mime_type: MIME type string containing audio parameters
            
        Returns:
            WAV formatted audio data
        """
        # Parse sample rate from MIME type (default to 24kHz)
        sample_rate = 24000
        if 'rate=' in mime_type:
            try:
                rate_str = mime_type.split('rate=')[1].split(';')[0]
                sample_rate = int(rate_str)
            except (ValueError, IndexError):
                # Use default if parsing fails
                pass
        
        # WAV format parameters
        channels = 1                              # Mono audio
        bits_per_sample = 16                     # 16-bit audio
        bytes_per_sample = bits_per_sample // 8  # 2 bytes per sample
        byte_rate = sample_rate * channels * bytes_per_sample
        block_align = channels * bytes_per_sample
        data_size = len(audio_data)
        
        # Create WAV header using struct.pack
        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',            # Chunk ID
            36 + data_size,     # Chunk size
            b'WAVE',            # Format
            b'fmt ',            # Subchunk1 ID
            16,                 # Subchunk1 size (PCM)
            1,                  # Audio format (PCM)
            channels,           # Number of channels
            sample_rate,        # Sample rate
            byte_rate,          # Byte rate
            block_align,        # Block align
            bits_per_sample,    # Bits per sample
            b'data',            # Subchunk2 ID
            data_size           # Subchunk2 size
        )
        
        # Combine header with audio data
        return header + audio_data
    
    def generate_audio(self, text: str) -> str:
        """
        Main audio generation method with caching.
        
        This is the primary method called to generate TTS audio. It handles
        input validation, caching, and file management.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Filename of generated audio file
            
        Raises:
            ValueError: If input is invalid or generation fails
        """
        # Input validation - preserve all valid Unicode
        text = text.strip()
        if not text:
            raise ValueError("No text provided")
        
        # Remove only null bytes (dangerous for file operations)
        text = text.replace('\x00', '')
        
        # Character limit (generous for all languages)
        if len(text) > 5000:
            raise ValueError("Text too long (max 5000 characters)")
        
        # Check cache first to avoid unnecessary API calls
        cache_key = self.get_cache_key(text, self.config.get("voice", "Zephyr"))
        cached_filename = self.get_cached_audio(cache_key)
        if cached_filename:
            return cached_filename
        
        # Generate new audio via API
        audio_data = self.generate_audio_http(text)
        
        # Generate secure filename using hash (no user content)
        timestamp = int(time.time())
        filename = f"gemini_tts_{cache_key[:8]}_{timestamp}.wav"
        
        # Ensure file path stays within media directory
        file_path = os.path.join(mw.col.media.dir(), filename)
        if not file_path.startswith(mw.col.media.dir()):
            raise ValueError("Security error: Invalid file path")
        
        # Write audio data to file
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        # Cache audio for future use
        self.cache_audio(cache_key, audio_data)
        
        return filename
    
    # ========================================================================
    # ANKI EDITOR INTEGRATION
    # ========================================================================
    
    def add_audio_to_note(self, editor, filename: str):
        """
        Add generated audio to the detected source field in Anki note.
        
        Args:
            editor: Anki editor instance
            filename: Audio filename to add
            
        Returns:
            True if successful, False otherwise
        """
        target_field = self.detect_source_field(editor)
        
        # Check if target field exists in current note type
        if target_field not in editor.note:
            tooltip(f"Field '{target_field}' not found")
            return False
        
        # Create audio tag for Anki
        sound_tag = f"[sound:{filename}]"
        current_content = editor.note[target_field]
        
        # Add sound tag if not already present
        if sound_tag not in current_content:
            if current_content.strip():
                # Append to existing content
                editor.note[target_field] = f"{current_content} {sound_tag}"
            else:
                # Set as only content
                editor.note[target_field] = sound_tag
        
        # Reload editor to show changes
        editor.loadNote()
        
        # Return focus to editor after brief delay
        QTimer.singleShot(100, lambda: self.focus_editor(editor))
        return True
    
    def focus_editor(self, editor):
        """
        Restore focus to editor web view.
        
        Args:
            editor: Anki editor instance
        """
        try:
            if hasattr(editor, 'web') and hasattr(editor.web, 'setFocus'):
                editor.web.setFocus()
        except:
            # Silently fail if focus restoration doesn't work
            pass
    
    def setup_editor_button(self, buttons, editor):
        """
        Add TTS button to editor toolbar.
        
        Args:
            buttons: List of existing editor buttons
            editor: Anki editor instance
            
        Returns:
            Updated buttons list
        """
        try:
            # Check for icon file (graceful fallback if not found)
            addon_dir = os.path.dirname(os.path.dirname(__file__))
            icon_path = os.path.join(addon_dir, "icons", "gemini.png")
            use_icon = icon_path if os.path.exists(icon_path) else None
            
            # Add button to editor toolbar
            button = editor.addButton(
                icon=use_icon,
                cmd="gemini_tts",
                tip="Generate Gemini TTS (Ctrl+G)",
                func=lambda ed: self.on_button_click(ed),
                keys="Ctrl+G"
            )
            
            buttons.append(button)
            
        except Exception as e:
            # Log error but don't break editor functionality
            print(f"Gemini TTS: Button setup error - {e}")
        
        return buttons
    
    # ========================================================================
    # TEXT PROCESSING AND NORMALIZATION
    # ========================================================================
    
    def normalize_text(self, text: str) -> str:
        """
        Clean and normalize text for TTS processing.
        
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
        
        # Convert HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&mdash;': '—',
            '&ndash;': '–'
        }
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        # Handle bullet points and list markers
        bullet_patterns = [
            r'^[\s]*[•·‣⁃▪▫‧◦⦾⦿]\s*',  # Various bullet characters
            r'^[\s]*[-*+]\s*',           # Dash/asterisk bullets
            r'^[\s]*\d+[.)]\s*',         # Numbered lists
            r'^[\s]*[a-zA-Z][.)]\s*',    # Lettered lists
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove bullet point prefixes
            for pattern in bullet_patterns:
                line = re.sub(pattern, '', line, flags=re.MULTILINE)
                line = line.strip()
            
            if line:  # Only add non-empty lines
                cleaned_lines.append(line)
        
        # Join lines with appropriate spacing
        text = ' '.join(cleaned_lines)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces -> single space
        text = text.strip()
        
        # Remove or replace problematic characters
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2000', ' ')  # En quad
        text = text.replace('\u2001', ' ')  # Em quad
        text = text.replace('\u2002', ' ')  # En space
        text = text.replace('\u2003', ' ')  # Em space
        text = text.replace('\u2009', ' ')  # Thin space
        text = text.replace('\u200b', '')   # Zero-width space
        
        return text
    
    # ========================================================================
    # USER INTERACTION HANDLERS
    # ========================================================================
    
    def on_button_click(self, editor):
        """
        Handle TTS button click in editor.
        
        Args:
            editor: Anki editor instance
        """
        # Enhanced text extraction with HTML content fallback
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
        """
        Process the selection result from JavaScript.
        
        Args:
            editor: Anki editor instance
            result: Selection data from JavaScript
        """
        if not result.get('hasContent', False):
            tooltip("Please select some text first")
            return
        
        # Try plain text first, fall back to HTML content if needed
        raw_text = result.get('plainText', '') or result.get('htmlContent', '')
        
        if not raw_text.strip():
            tooltip("No readable text found in selection")
            return
        
        # Clean and normalize the text
        cleaned_text = self.normalize_text(raw_text)
        
        if not cleaned_text.strip():
            tooltip("Selected text cannot be converted to speech")
            return
        
        # Proceed with TTS generation
        self.process_selected_text(editor, cleaned_text)
    
    def process_selected_text(self, editor, selected_text):
        """
        Process selected text for TTS generation.
        
        Args:
            editor: Anki editor instance
            selected_text: Cleaned text for TTS
        """
        # Validate that API key is configured
        if not self.config.get("api_key", "").strip():
            tooltip("Please configure API key first")
            return
        
        # Show progress message
        tooltip("Generating TTS audio...")
        
        # Use QTimer to avoid blocking UI during generation
        QTimer.singleShot(100, lambda: self.generate_and_add_audio(editor, selected_text))
    
    def generate_and_add_audio(self, editor, text):
        """
        Generate audio and add to note (non-blocking operation).
        
        Args:
            editor: Anki editor instance
            text: Text to convert to speech
        """
        try:
            # Generate audio file
            filename = self.generate_audio(text)
            
            # Add to note and show success message
            if self.add_audio_to_note(editor, filename):
                tooltip("Audio generated successfully")
            else:
                tooltip("Failed to add audio to note")
                
        except Exception as e:
            # Handle errors with user-friendly messages
            error_msg = str(e)
            
            if "API key" in error_msg:
                tooltip("Invalid API key - check configuration")
            elif "Rate limited" in error_msg:
                tooltip("Rate limited - wait and try again")
            elif "Network error" in error_msg:
                tooltip("Network error - check connection")
            else:
                # Generic error message (truncated for UI)
                tooltip(f"Error: {error_msg[:50]}...")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_available_voices(self):
        """
        Get list of available Gemini TTS voices.
        
        Returns:
            List of voice names available for TTS generation
        """
        return [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
            "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
            "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
            "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
            "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ]