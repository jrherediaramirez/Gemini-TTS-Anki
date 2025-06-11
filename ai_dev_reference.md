# AI Development Reference Guide

## Table of Contents
1. [Anki Development Reference](#anki-development-reference)
2. [Python Version & Compatibility](#python-version--compatibility)
3. [Gemini 2.5 API Reference](#gemini-25-api-reference)
4. [Python Feature Compatibility Matrix](#python-feature-compatibility-matrix)
5. [Qt Compatibility Guard-rails](#qt-compatibility-guard-rails)

---

## Anki Development Reference

### Current Environment
- **Anki Version**: 25.02.6 (Latest)
- **Qt Version**: 6.6.x
- **PyQt Version**: 6.6.x
- **Python Bindings**: PyQt6

### Critical Qt 6.6 Requirements
- **Import Pattern**: `from aqt.qt import *` (Required)
- **Enum Syntax**: `Qt.Orientation.Horizontal` (Not magic numbers)
- **Slider Ticks**: `QSlider.TickPosition.TicksBelow`
- **Echo Mode**: `QLineEdit.EchoMode.Password`

### Essential Documentation
- **Qt 6.6 Main**: https://doc.qt.io/qt-6/
- **Qt Widgets**: https://doc.qt.io/qt-6/qtwidgets-index.html
- **PyQt6 Reference**: https://doc.qt.io/qtforpython-6/

### Breaking Changes from Qt5
- No magic numbers for orientations/positions
- Enum values require full path specification
- Qt5 builds no longer supported

### Code Standards
```python
# Correct Qt 6.6 patterns
from aqt.qt import *
slider = QSlider(Qt.Orientation.Horizontal)
slider.setTickPosition(QSlider.TickPosition.TicksBelow)
super().__init__(parent)
```

---

## Python Version & Compatibility

### Embedded Interpreter
**Anki 2.1.x desktop bundles CPython 3.9.18**, so your add-on must run on Python 3.9.

### What to Avoid
- **New syntax**: no `match/case`, no pattern-matching features added in 3.10+
- **Stdlib APIs**: skip modules or functions introduced after 3.9

### If You Need Newer Libraries
1. **Bundle wheels** compiled for CPython 3.9 (e.g. via `pip download --abi cp39-abi3`)
2. List them in `requirements.txt` and document their inclusion
3. Test under 3.9—don't assume users can upgrade Anki's interpreter

### Runtime Checks & Warnings
```python
import sys
from aqt.utils import showWarning

if sys.version_info < (3, 9):
    raise RuntimeError("This add-on requires Python >= 3.9 (Anki 2.1.x).")
elif sys.version_info >= (3, 10):
    showWarning("Untested Python version; some features may not work as expected.")
```

### Best Practices
- **Develop & CI-test** on CPython 3.9
- **Document** any bundled dependencies clearly
- **Fail fast** with a clear error if the interpreter is unsupported

---

## Gemini 2.5 API Reference

### Model Overview (June 2025)

| Use-case | Latest model ID | Token limits (in/out) | Extras |
|----------|----------------|----------------------|--------|
| **Chat / multimodal, max quality** | `gemini-2.5-pro-preview-06-05` | 1,048,576 / 65,536 | "thinking" always on; function-calling, files, long context |
| **Chat / multimodal, fast-cheap** | `gemini-2.5-flash-preview-05-20` | 1,048,576 / 65,536 | "thinking" optional; set `thinkingBudget` to 0 to disable |
| **Single/Multi-speaker TTS (fast)** | `gemini-2.5-flash-preview-tts` | 8,000 / 16,000 | 30 voices; mono & stereo |
| **Single/Multi-speaker TTS (highest quality)** | `gemini-2.5-pro-preview-tts` | 8,000 / 16,000 | same controls, slower costlier |

### Base REST Endpoint
```http
POST https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key=YOUR_API_KEY
```

**Headers:**
```http
Content-Type: application/json
# OR use bearer auth instead of the key:
Authorization: Bearer YOUR_API_KEY
```

### Minimal Chat Request (curl)
```bash
curl -s \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-preview-06-05:generateContent?key=$API_KEY" \
  -H "Content-Type: application/json" -d @- <<'EOF'
{
  "contents": [{
    "role": "user",
    "parts": [{"text": "Give me three study tips"}]
  }],
  "generationConfig": {
    "temperature": 0.7,
    "topP": 0.95,
    "topK": 40,
    "maxOutputTokens": 256
  },
  "safetySettings": [{
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE"
  }]
}
EOF
```

### Generation Configuration Options

| Field | Purpose |
|-------|---------|
| `temperature` (0-2) | Randomness; 0 = deterministic |
| `topP`, `topK` | Nucleus / k-sampling filters |
| `maxOutputTokens` | Hard cap on reply length |
| `stopSequences` | Early stop strings |
| `candidateCount` | Return N alternatives |
| **2.5-only** `thinkingConfig.thinkingBudget` | 128-32,768 (Pro) or 0-24,576 (Flash); 0 disables thinking on Flash |
| **2.5-only** `thinkingConfig.includeThoughts` | true to get model "thoughts" in response metadata |

### TTS Request (Single Speaker)
```bash
curl -s \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=$API_KEY" \
  -H "Content-Type: application/json" -d @- <<'EOF'
{
  "contents":[{
    "parts":[{
      "text":"Say cheerfully: Have a wonderful day!"
    }]
  }],
  "generationConfig":{
    "responseModalities":["AUDIO"],
    "speechConfig":{
      "voiceConfig":{
        "prebuiltVoiceConfig":{
          "voiceName":"Kore"
        }
      }
    }
  }
}
EOF | jq -r '.candidates[0].content.parts[0].inlineData.data' | base64 -d >out.pcm

ffmpeg -f s16le -ar 24000 -ac 1 -i out.pcm out.wav
```

**Multi-speaker:** replace `voiceConfig` with `multiSpeakerVoiceConfig` listing up to 2 speakers

**Voices available:** 30 pre-built options e.g. *Kore, Puck, Enceladus, Leda*

### Good Defaults & Safety
```json
"generationConfig": {
  "temperature": 0.5,
  "topP": 0.9,
  "topK": 32,
  "maxOutputTokens": 1024
},
"safetySettings": [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM"
  }
]
```

### Rate Limits (Preview Tier)

| Model | Requests/min | TPM* |
|-------|-------------|------|
| 2.5 Pro Preview | 25 | 80k |
| 2.5 Flash Preview | 60 | 80k |
| 2.5 TTS models | 10 | — |

*(tokens per minute)*

### Migration Tips for Pure-HTTP Use
1. **Centralise** the endpoint builder so swapping model IDs is one line
2. **Surface** critical errors (`429`, `5xx`) with exponential back-off
3. **Gate** SDK-only features—always check for `thinkingConfig` keys before sending
4. **Cache** identical prompt + config hashes to save quota
5. **Bundle** an **API key validator** at startup; fail fast if missing

---

## Python Feature Compatibility Matrix

### 🚫 Python 3.10+ Features to Avoid (Anki runs on 3.9.18)

| Feature / API | Why it breaks on 3.9 | First appeared |
|---------------|----------------------|----------------|
| `match … case …` structural-pattern-matching | SyntaxError | 3.10 |
| Union-operator in type hints (`int\|str`) | SyntaxError | 3.10 |
| Parenthesised multi-line `with (...)` context-managers | SyntaxError | 3.10 |
| `@dataclass(slots=True, kw_only=True)` options | `TypeError: unexpected keyword` | 3.10 |
| `typing.ParamSpec`, `TypeGuard`, `TypeAlias`, variadic generics | `AttributeError` (absent in typing) | 3.10 |

### 🚫 Python 3.11 Features to Avoid

| Feature / API | Why it breaks | First appeared |
|---------------|---------------|----------------|
| `except*` & `ExceptionGroup` | SyntaxError | 3.11 |
| `asyncio.TaskGroup` | AttributeError | 3.11 |
| `typing.Self`, `Required`, `NotRequired`, variadic generics improvements | AttributeError | 3.11 |
| Std-lib `tomllib` module | ModuleNotFoundError | 3.11 |

### 🚫 Python 3.12+ Features to Avoid

| Feature / API | Why it breaks | First appeared |
|---------------|---------------|----------------|
| New `type` statement & full type-parameter syntax (PEP 695) | SyntaxError | 3.12 |
| Relaxed / multiline **f-strings** (PEP 701) | SyntaxError | 3.12 |
| `itertools.batched()` | AttributeError | 3.12 |
| `typing.TypeAliasType`, `override` decorator, etc. | AttributeError | 3.12 |

### Practical Guard-rails
```python
import sys, warnings, typing, itertools, asyncio, importlib

# 1. Fail fast on unsupported interpreter
if sys.version_info < (3, 9):
    raise RuntimeError("Requires Python ≥3.9")
elif sys.version_info >= (3, 10):
    warnings.warn(
        "Running under Python 3.10+. "
        "Some Anki add-on code may crash – run at your own risk.",
        RuntimeWarning,
    )

# 2. Soft-import risky std-lib pieces
try:
    import tomllib  # noqa: F401
except ModuleNotFoundError:
    tomllib = None  # use 'tomli' back-port

# 3. Avoid APIs if absent
if not hasattr(asyncio, "TaskGroup"):
    # fallback to asyncio.gather / create_task
    ...
```

---

## Qt Compatibility Guard-rails

### Target Baseline
**Python 3.9.18 + Qt 6.6.2 + PyQt 6.6.1** (the exact toolkit bundled with Anki 25.02)

### 1. Newer Qt Modules You Must NOT Import
*(they debut in ≥ 6.7 and are absent in the Anki bundle)*

| Module (Python import) | First shipped | Why to skip |
|------------------------|---------------|-------------|
| `PyQt6.QtGraphs` / `QtGraphs` | 6.7 | 2-D/3-D graphs add-on; not bundled |
| `PyQt6.QtHttpServer` | 6.8 | Lightweight HTTP server |
| `PyQt6.QtGrpc`, `PyQt6.QtProtobuf` | 6.8 | gRPC / Protobuf helpers |
| `PyQt6.QtQuick3DXr` / `QtQuick3D.XR` | 6.8 | XR & spatial |
| `PyQt6.QtQuickVectorImage` | 6.8 | Vector-image renderer |
| `PyQt6.QtLocation`, `PyQt6.QtGamepad`, `PyQt6.QtKnx`, `PyQt6.QtMacExtras` | 6.7-6.8 | Not in 6.6 package |
| `PyQt6.QtLanguageServer` (QML LS) | 6.7 | Dev-only tooling |

### 2. APIs & Helpers Added After 6.6 to Avoid

| Call / constant | Since | Safe substitute |
|----------------|--------|-----------------|
| `QCryptographicHash.hashInto()` & any *into-buffer* overloads | 6.8 | Use `hash()` or `addData()` |
| Any classes using C++ `<=>` three-way comparisons via PyQt | 6.8 | Stick to normal `<`, `==` |
| `QtAsyncio.run(handle_sigint=…)` option | PyQt 6.7 | Don't rely on `handle_sigint` flag; fallback to plain `QtAsyncio.run()` |
| QML **Graph-related** types (`QtGraphs.*`) | 6.7 | — |
| New Quick Controls properties (variable-fonts, child-windows) | 6.7 | Use standard `QFont`, `QWindow` behaviour |
| New `QtHttpServer` SSL helpers | 6.8 | Roll your own `QTcpServer` + `QSslSocket` |

### 3. Enum / Namespace Notes
- PyQt 6 already **removed short enum names**; always use fully-qualified enums (`Qt.ItemDataRole.DisplayRole`)
- No problems here, just **don't copy-paste PySide6 short forms**

### 4. Runtime Guard-check (Qt)
```python
from PyQt6.QtCore import QT_VERSION_STR
from packaging import version
import warnings

if version.parse(QT_VERSION_STR) > version.parse("6.6.2"):
    warnings.warn("Untested Qt build; some APIs may behave differently.", RuntimeWarning)
elif version.parse(QT_VERSION_STR) < version.parse("6.6.0"):
    raise RuntimeError("Add-on requires Qt ≥ 6.6")
```

### 5. Practical Tips
1. **Stick to core, GUI, widgets, multimedia** – everything else *may* be stripped from Anki's smaller lib folder
2. **Don't rely on Qt Graphs for charting** – use a pure-Python lib (Matplotlib, PyQtGraph) instead
3. **No `QtAsyncio` fanciness** – Anki's event loop is already busy; use plain threads for background work
4. **Bundle back-ports** only if you *must* (e.g. include a small HTTP helper instead of Qt HttpServer)
5. **Test with Anki's shipped Python**: `Tools → Python Console` inside Anki ensures you're on the same interpreter and Qt build

---

## Development Checklist

### Before Releasing
- [ ] Tested on Python 3.9.18
- [ ] No Python 3.10+ syntax or stdlib features
- [ ] Qt 6.6 compatibility verified
- [ ] No newer Qt modules imported
- [ ] Runtime version checks implemented
- [ ] Dependencies documented and bundled if needed
- [ ] Code follows Anki Qt 6.6 patterns

### Testing Environment
- Use `Tools → Python Console` in Anki for interpreter testing
- Verify enum syntax follows full path specification
- Check import patterns use `from aqt.qt import *`
- Validate error handling for version mismatches