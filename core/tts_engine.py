# -*- coding: utf-8 -*-
"""
Gemini TTS Engine - Unified Version
===================================

Complete TTS engine with unified preprocessing + audio generation,
intelligent content analysis, and enhanced caching system.
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
from typing import Optional, Dict, Any, Tuple
from functools import partial

from aqt import mw
from aqt.qt import QTimer, QMenu, QCursor
from aqt.utils import tooltip

class GeminiTTS:
    """Enhanced TTS engine with unified preprocessing and audio generation."""
    
    def __init__(self):
        """Initialize the TTS engine with configuration and cache setup."""
        self.config = self.load_config()
        self.cache_dir = os.path.join(mw.col.media.dir(), ".gemini_cache")
        self.cache_metadata_file = os.path.join(self.cache_dir, "cache_metadata.json")
        self.create_cache_dir()
        self.cache_metadata = self.load_cache_metadata()
        
        # Initialize content analyzer
        try:
            from .content_analyzer import ContentAnalyzer
            self.content_analyzer = ContentAnalyzer()
        except ImportError:
            self.content_analyzer = None
            print("Warning: ContentAnalyzer not available, using fallback")
    
    # ========================================================================
    # CONFIGURATION MANAGEMENT
    # ========================================================================
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from Anki with enhanced defaults."""
        defaults = {
            # Basic settings
            "api_key": "",
            "model": "flash_unified",
            "processing_mode": "unified",
            "voice": "Zephyr",
            "temperature": 0.0,
            
            # Advanced settings
            "thinking_budget": 0,
            "enable_cache": True,
            "cache_days": 30,
            "enable_fallback": True,
            "cache_preprocessing": True,
            
            # Processing settings
            "preprocessing_style": "natural",
            "enable_style_control": True,
            "auto_detect_content": True,
            "prefer_instructions": True
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
    
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Get available TTS models including unified options."""
        return {
            "flash_unified": {
                "model_id": "gemini-2.5-flash-preview-06-05",
                "display_name": "Gemini 2.5 Flash (Unified)",
                "description": "AI preprocessing + TTS in one call",
                "mode": "unified",
                "thinking_budget_range": (0, 24576)
            },
            "pro_unified": {
                "model_id": "gemini-2.5-pro-preview-06-05",
                "display_name": "Gemini 2.5 Pro (Unified)",
                "description": "Best quality with AI preprocessing",
                "mode": "unified",
                "thinking_budget_range": (128, 32768)
            },
            "flash_tts": {
                "model_id": "gemini-2.5-flash-preview-tts",
                "display_name": "Gemini 2.5 Flash (TTS Only)",
                "description": "Traditional TTS without preprocessing",
                "mode": "traditional"
            },
            "pro_tts": {
                "model_id": "gemini-2.5-pro-preview-tts",
                "display_name": "Gemini 2.5 Pro (TTS Only)", 
                "description": "High quality traditional TTS",
                "mode": "traditional"
            }
        }
    
    def get_current_model_info(self) -> Dict[str, Any]:
        """Get information about the currently selected model."""
        models = self.get_available_models()
        model_key = self.config.get("model", "flash_unified")
        return models.get(model_key, models["flash_unified"])
    
    def get_available_voices(self):
        """Get list of available Gemini TTS voices."""
        return [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
            "Callirhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", 
            "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
            "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
            "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
        ]
    
    # ========================================================================
    # CONTENT ANALYSIS AND PREPROCESSING
    # ========================================================================
    
    def analyze_content(self, text: str) -> Dict[str, Any]:
        """Analyze content structure for optimal processing."""
        if self.content_analyzer:
            return self.content_analyzer.analyze_structure(text)
        else:
            # Fallback analysis
            return {
                "type": "general",
                "complexity": "medium",
                "suggested_thinking_budget": 128,
                "preprocessing_strategy": "enhanced"
            }
    
    def build_preprocessing_prompt(self, text: str, analysis: Dict[str, Any]) -> str:
        """Build intelligent preprocessing prompt based on content analysis."""
        content_type = analysis.get("type", "general")
        style = self.config.get("preprocessing_style", "natural")
        
        if self.content_analyzer:
            template = self.content_analyzer.get_preprocessing_prompt_template(content_type, style)
            return template.format(text=text)
        else:
            # Fallback prompt
            return f"""
Transform this text into natural spoken language using a {style} style:

{text}

RULES:
- Convert bullet points and lists into flowing sentences
- Add appropriate transitions between ideas
- Make it sound conversational and natural
- Preserve all important information

Generate natural speech text:"""
    
    def should_use_unified_mode(self, text: str) -> bool:
        """Determine if unified mode should be used for this text."""
        processing_mode = self.config.get("processing_mode", "unified")
        
        if processing_mode == "traditional":
            return False
        elif processing_mode == "unified":
            return True
        elif processing_mode == "auto":
            # Auto-detect based on content structure
            analysis = self.analyze_content(text)
            return analysis.get("has_bullets", False) or analysis.get("has_numbers", False)
        elif processing_mode == "hybrid":
            # Use unified for complex content, traditional for simple
            analysis = self.analyze_content(text)
            return analysis.get("complexity", "medium") != "low"
        
        return True  # Default to unified
    
    # ========================================================================
    # UNIFIED AUDIO GENERATION
    # ========================================================================
    
    def generate_audio_unified(self, text: str) -> bytes:
        """Generate audio using unified preprocessing + TTS in single API call."""
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise ValueError("API key not configured")
        
        # Analyze content for optimal processing
        analysis = self.analyze_content(text)
        
        # Build preprocessing prompt
        preprocessing_prompt = self.build_preprocessing_prompt(text, analysis)
        
        # Get model information
        model_info = self.get_current_model_info()
        model_id = model_info["model_id"]
        
        # Ensure we're using a unified-capable model
        if model_info.get("mode") != "unified":
            # Fall back to using the unified version
            model_id = "gemini-2.5-flash-preview-06-05"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        
        # Build API payload
        payload = {
            "contents": [{"parts": [{"text": preprocessing_prompt}]}],
            "generationConfig": {
                "temperature": self.config.get("temperature", 0.0),
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.config.get("voice", "Zephyr")
                        }
                    }
                }
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM"
                }
            ]
        }
        
        # Add thinking budget if configured
        thinking_budget = self.config.get("thinking_budget", 0)
        suggested_budget = analysis.get("suggested_thinking_budget", 0)
        
        # Use configured budget or suggested budget, whichever is higher
        final_budget = max(thinking_budget, suggested_budget) if self.config.get("auto_detect_content", True) else thinking_budget
        
        # Validate budget against model limits
        if "thinking_budget_range" in model_info:
            min_budget, max_budget = model_info["thinking_budget_range"]
            final_budget = max(min_budget, min(final_budget, max_budget))
        
        if final_budget > 0:
            payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": final_budget,
                "includeThoughts": False
            }
        
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(request, timeout=45) as response:  # Longer timeout for unified processing
                response_data = json.loads(response.read().decode('utf-8'))
            
        except urllib.error.HTTPError as e:
            if e.code == 400:
                raise ValueError("Invalid request - check API key and text")
            elif e.code == 403:
                raise ValueError("Invalid API key or access denied")
            elif e.code == 429:
                # Implement exponential backoff
                raise ValueError("Rate limited - please wait and try again")
            else:
                raise ValueError(f"API error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ValueError(f"Network error: {e.reason}")
        except json.JSONDecodeError:
            raise ValueError("Invalid response from API")
        
        # Extract audio data
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
    
    def generate_audio_http(self, text: str) -> bytes:
        """Generate audio using traditional HTTP request to Gemini TTS API."""
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise ValueError("API key not configured")
        
        model_info = self.get_current_model_info()
        model_id = model_info["model_id"]
        
        # Ensure we're using a TTS-only model for traditional mode
        if model_info.get("mode") != "traditional":
            model_id = "gemini-2.5-flash-preview-tts"
        
        voice = self.config.get("voice", "Zephyr")
        temperature = self.config.get("temperature", 0.0)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
        
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
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM"
                }
            ]
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
    # ENHANCED CACHE MANAGEMENT SYSTEM
    # ========================================================================
    
    def load_cache_metadata(self) -> Dict[str, Any]:
        """Load cache metadata for efficient cleanup."""
        if not os.path.exists(self.cache_metadata_file):
            return {"version": "2.0", "files": {}}
        
        try:
            with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                if "files" not in metadata:
                    metadata["files"] = {}
                return metadata
        except (json.JSONDecodeError, OSError):
            return {"version": "2.0", "files": {}}
    
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
    
    def create_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            if not self.cache_dir.startswith(mw.col.media.dir()):
                raise ValueError("Security error: Cache directory outside media folder")
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError:
            pass
    
    def get_cache_key(self, text: str, processing_mode: str = None) -> str:
        """Generate cache key including processing mode and settings."""
        if processing_mode is None:
            processing_mode = self.config.get("processing_mode", "unified")
        
        # Include relevant settings in cache key
        voice = self.config.get("voice", "Zephyr")
        model = self.config.get("model", "flash_unified")
        temperature = self.config.get("temperature", 0.0)
        
        # For unified mode, include processing settings
        if processing_mode == "unified":
            style = self.config.get("preprocessing_style", "natural")
            thinking_budget = self.config.get("thinking_budget", 0)
            content = f"{text}:{voice}:{model}:{temperature}:{processing_mode}:{style}:{thinking_budget}"
        else:
            content = f"{text}:{voice}:{model}:{temperature}:{processing_mode}"
        
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
                del self.cache_metadata["files"][filename]
                self.save_cache_metadata()
                try:
                    os.remove(cache_file)
                except OSError:
                    pass
                return None
        
        # Verify file actually exists
        if not os.path.exists(cache_file):
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
    
    def track_cache_file(self, cache_key: str):
        """Track a cache file in metadata."""
        filename = f"{cache_key}.wav"
        current_time = time.time()
        
        self.cache_metadata["files"][filename] = {
            "created": current_time,
            "accessed": current_time,
            "version": "2.0"
        }
        
        self.save_cache_metadata()
    
    def update_cache_access(self, cache_key: str):
        """Update access time for cache file."""
        filename = f"{cache_key}.wav"
        
        if filename in self.cache_metadata["files"]:
            self.cache_metadata["files"][filename]["accessed"] = time.time()
            self.save_cache_metadata()
    
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
        """Main audio generation method with intelligent mode selection."""
        text = text.strip()
        if not text:
            raise ValueError("No text provided")
        
        text = text.replace('\x00', '')
        
        if len(text) > 5000:
            raise ValueError("Text too long (max 5000 characters)")
        
        # Determine processing mode
        use_unified = self.should_use_unified_mode(text)
        processing_mode = "unified" if use_unified else "traditional"
        
        # Generate cache key
        cache_key = self.get_cache_key(text, processing_mode)
        cached_filename = self.get_cached_audio(cache_key)
        if cached_filename:
            return cached_filename
        
        # Generate audio with fallback handling
        try:
            if use_unified:
                audio_data = self.generate_audio_unified(text)
            else:
                # Apply traditional normalization first
                normalized_text = self.normalize_text(text)
                audio_data = self.generate_audio_http(normalized_text)
        
        except Exception as e:
            # Fallback to traditional mode if unified fails and fallback is enabled
            if use_unified and self.config.get("enable_fallback", True):
                try:
                    normalized_text = self.normalize_text(text)
                    audio_data = self.generate_audio_http(normalized_text)
                    tooltip("Unified mode failed, used traditional mode")
                except Exception as fallback_error:
                    raise e  # Raise original error if fallback also fails
            else:
                raise e
        
        # Save to media directory
        timestamp = int(time.time())
        filename = f"gemini_tts_{cache_key[:8]}_{timestamp}.wav"
        
        file_path = os.path.join(mw.col.media.dir(), filename)
        if not file_path.startswith(mw.col.media.dir()):
            raise ValueError("Security error: Invalid file path")
        
        with open(file_path, 'wb') as f:
            f.write(audio_data)
        
        # Cache the result
        self.cache_audio(cache_key, audio_data)
        
        return filename
    
    # ========================================================================
    # TEXT PROCESSING AND NORMALIZATION
    # ========================================================================
    
    def normalize_text(self, text: str) -> str:
        """Clean and normalize text for traditional TTS processing."""
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
        """Add enhanced TTS buttons to editor toolbar."""
        try:
            addon_dir = os.path.dirname(os.path.dirname(__file__))
            icon_path = os.path.join(addon_dir, "icons", "gemini.png")
            use_icon = icon_path if os.path.exists(icon_path) else None
            
            # Get current settings for tooltip
            model_info = self.get_current_model_info()
            processing_mode = self.config.get("processing_mode", "unified")
            current_voice = self.config.get("voice", "Zephyr")
            
            tip = (f"Generate Gemini TTS (Ctrl+G)\n"
                   f"Model: {model_info['display_name']}\n"
                   f"Mode: {processing_mode.title()}\n"
                   f"Voice: {current_voice}")
            
            # Main TTS button
            button = editor.addButton(
                icon=use_icon,
                cmd="gemini_tts",
                tip=tip,
                func=lambda ed: self.on_button_click(ed),
                keys="Ctrl+G"
            )
            
            # Mode selection button
            mode_button = editor.addButton(
                None,
                cmd="gemini_mode",
                tip=f"Processing Mode: {processing_mode.title()}\nClick to change",
                func=lambda ed: self.show_mode_menu(ed),
                label=f"Mode: {processing_mode[:3].title()}"
            )
            
            # Model selection button
            model_button = editor.addButton(
                None,
                cmd="gemini_model",
                tip=f"Model: {model_info['display_name']}\nClick to change",
                func=lambda ed: self.show_model_menu(ed),
                label="Model"
            )
            
            # Voice selection button  
            voice_button = editor.addButton(
                None,
                cmd="gemini_voice", 
                tip=f"Voice: {current_voice}\nClick to change",
                func=lambda ed: self.show_voice_menu(ed),
                label="Voice"
            )
            
            buttons.extend([button, mode_button, model_button, voice_button])
            
        except Exception as e:
            print(f"Gemini TTS: Button setup error - {e}")
        
        return buttons
    
    def show_mode_menu(self, editor):
        """Show processing mode selection menu."""
        menu = QMenu(editor.widget)
        current_mode = self.config.get("processing_mode", "unified")
        
        modes = [
            ("unified", "Unified (AI + TTS)"),
            ("traditional", "Traditional (TTS Only)"),
            ("hybrid", "Hybrid (Auto-Select)"),
            ("auto", "Auto-Detect")
        ]
        
        for mode_key, mode_name in modes:
            action = menu.addAction(mode_name)
            action.setCheckable(True)
            action.setChecked(mode_key == current_mode)
            action.triggered.connect(lambda checked, mk=mode_key: self.change_processing_mode(mk))
        
        menu.exec(QCursor.pos())
    
    def show_model_menu(self, editor):
        """Show model selection menu."""
        menu = QMenu(editor.widget)
        models = self.get_available_models()
        current_model = self.config.get("model", "flash_unified")
        
        for model_key, model_info in models.items():
            action = menu.addAction(model_info["display_name"])
            action.setCheckable(True)
            action.setChecked(model_key == current_model)
            action.triggered.connect(lambda checked, mk=model_key: self.change_model(mk))
        
        menu.exec(QCursor.pos())
    
    def show_voice_menu(self, editor):
        """Show voice selection menu."""
        menu = QMenu(editor.widget)
        voices = self.get_available_voices()
        current_voice = self.config.get("voice", "Zephyr")
        
        for voice in voices:
            action = menu.addAction(voice)
            action.setCheckable(True)
            action.setChecked(voice == current_voice)
            action.triggered.connect(lambda checked, v=voice: self.change_voice(v))
        
        menu.exec(QCursor.pos())
    
    def change_processing_mode(self, mode_key):
        """Change processing mode and update configuration."""
        config = self.config.copy()
        config["processing_mode"] = mode_key
        self.save_config(config)
        
        mode_names = {
            "unified": "Unified (AI + TTS)",
            "traditional": "Traditional",
            "hybrid": "Hybrid",
            "auto": "Auto-Detect"
        }
        tooltip(f"Processing mode: {mode_names.get(mode_key, mode_key)}")
    
    def change_model(self, model_key):
        """Change model and update configuration."""
        config = self.config.copy()
        config["model"] = model_key
        self.save_config(config)
        
        model_info = self.get_available_models()[model_key]
        tooltip(f"Model: {model_info['display_name']}")
    
    def change_voice(self, voice):
        """Change voice and update configuration."""
        config = self.config.copy()
        config["voice"] = voice
        self.save_config(config)
        tooltip(f"Voice: {voice}")

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
        
        # Check if we should preprocess the text or use it as-is
        if self.should_use_unified_mode(raw_text):
            # Unified mode will handle preprocessing
            final_text = raw_text
        else:
            # Traditional mode - apply normalization
            final_text = self.normalize_text(raw_text)
        
        if not final_text.strip():
            tooltip("Selected text cannot be converted to speech")
            return
        
        self.process_selected_text(editor, final_text)
    
    def process_selected_text(self, editor, selected_text):
        """Process selected text for TTS generation."""
        if not self.config.get("api_key", "").strip():
            tooltip("Please configure API key first")
            return
        
        # Show processing indicator based on mode
        processing_mode = self.config.get("processing_mode", "unified")
        if processing_mode == "unified":
            tooltip("Generating TTS with AI preprocessing...")
        else:
            tooltip("Generating TTS...")
        
        QTimer.singleShot(100, lambda: self.generate_and_add_audio(editor, selected_text))
    
    def generate_and_add_audio(self, editor, text):
        """Generate audio and add to note (non-blocking operation)."""
        try:
            filename = self.generate_audio(text)
            
            if self.add_audio_to_note(editor, filename):
                model_info = self.get_current_model_info()
                current_voice = self.config.get("voice", "Zephyr")
                processing_mode = self.config.get("processing_mode", "unified")
                
                tooltip(f"Audio generated: {model_info['display_name']} ({processing_mode}) - {current_voice}")
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
            elif "too long" in error_msg:
                tooltip("Text too long - select shorter text")
            else:
                tooltip(f"Error: {error_msg[:50]}...")