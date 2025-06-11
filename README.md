# Gemini TTS - Simple HTTP Version

Professional Text-to-Speech for Anki using Google's Gemini API with **zero external dependencies**. Works on all platforms including Linux Flatpak.

## ✨ Features

- **No Dependencies**: Uses only Python built-in libraries (urllib, json, base64)
- **Universal Compatibility**: Works on Windows, macOS, Linux (including Flatpak/Snap)
- **30+ Premium Voices**: Choose from Google's natural-sounding voice collection
- **Smart Caching**: Avoid redundant API calls with intelligent caching
- **Simple Configuration**: Easy-to-use settings dialog
- **Keyboard Shortcut**: Press Ctrl+G to generate TTS from selected text

## 🚀 Installation

### Method 1: AnkiWeb (Recommended)
1. Open Anki
2. Go to `Tools` > `Add-ons` > `Get Add-ons...`
3. Enter add-on code: `[ANKIWEB_CODE]`
4. Click `OK` and restart Anki

### Method 2: Manual Installation
1. Download the latest release
2. Extract to your Anki add-ons folder:
   - **Windows**: `%APPDATA%\Anki2\addons21\`
   - **macOS**: `~/Library/Application Support/Anki2/addons21/`
   - **Linux**: `~/.local/share/Anki2/addons21/`
3. Restart Anki

## ⚙️ Setup

### 1. Get Gemini API Key
1. Visit [ai.google.dev](https://ai.google.dev/)
2. Click "Get API key" → "Create API key"
3. Copy the generated API key

### 2. Configure Add-on
1. In Anki, go to `Tools` > `Gemini TTS Config...`
2. Paste your API key
3. Choose your preferred voice (default: Zephyr)
4. Set target field name (default: Audio)
5. Click "Test API Key" to verify
6. Click "Save"

## 📖 Usage

### Basic Usage
1. Open the note editor (Add or Edit card)
2. Select the text you want to convert to speech
3. Press `Ctrl+G` or click the TTS button
4. Audio will be automatically added to your target field

### Available Voices
Choose from 30+ natural voices including:
- **Zephyr** - Gentle and flowing (default)
- **Puck** - Playful and mischievous  
- **Charon** - Deep and mysterious
- **Kore** - Clear and articulate
- And many more...

### Caching
- Previously generated audio is cached for 30 days (configurable)
- Same text + same voice = instant playback from cache
- Reduces API costs and improves performance

## 🔧 Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| API Key | Your Gemini API key | (required) |
| Voice | TTS voice name | Zephyr |
| Target Field | Field to add audio | Audio |
| Temperature | Creativity (0.0-1.0) | 0.0 |
| Enable Cache | Cache generated audio | Yes |
| Cache Days | How long to keep cache | 30 days |

## 💡 Tips

- **Field Names**: Make sure your note type has the target field (default: "Audio")
- **Text Length**: Keep text under 5000 characters for best results
- **API Costs**: Very affordable - approximately $0.000016 per character
- **Cache Management**: Use "Clean Cache" button to remove expired files

## 🛠️ Troubleshooting

### "Please configure API key first"
- Add your Gemini API key in `Tools` > `Gemini TTS Config...`
- Test the key using the "Test API Key" button

### "Field not found"
- Ensure your note type has the target field
- Check the field name in configuration (case-sensitive)

### "Rate limited"
- Wait a minute and try again
- Consider upgrading your API quota if needed frequently

### Network/Connection Issues
- Check your internet connection
- Verify firewall isn't blocking the add-on
- Try again in a few minutes

## 🔒 Privacy & Security

- **API Key**: Stored locally in Anki's configuration
- **Text Data**: Sent to Google's Gemini API for processing
- **Audio Cache**: Stored locally in your Anki media folder
- **No Tracking**: This add-on doesn't collect any usage data

## 📊 API Usage & Costs

- **Pricing**: ~$0.000016 per character (very affordable)
- **Example**: 1000 characters ≈ $0.016 (less than 2 cents)
- **Caching**: Eliminates duplicate costs for repeated text
- **Rate Limits**: Respects Google's API limits automatically

## 🆕 Version 2.0 Changes

- **Zero Dependencies**: No more installation issues on any platform
- **Direct HTTP**: Uses Gemini API directly instead of SDK
- **Universal Compatibility**: Works on Linux Flatpak/Snap without issues
- **Simplified Code**: Easier to maintain and troubleshoot
- **Better Error Handling**: Clearer error messages and guidance

## 🤝 Support

- **Issues**: Report bugs on [GitHub Issues](https://github.com/jrherediaramirez/Gemini-TTS-Anki/issues)
- **Documentation**: Check the GitHub repository for detailed guides
- **Feature Requests**: Open an issue with your suggestion

## 📄 License

MIT License - see LICENSE file for details.

---

**Made with ❤️ for the Anki community**

No more dependency hell - just simple, reliable TTS that works everywhere!