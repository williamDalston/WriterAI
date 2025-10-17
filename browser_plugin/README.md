# Blooming Rewrite Engine 2.0 - Browser Plugin

**Chrome Extension for Real-Time Writing Assistance**

## Features

- 🌸 Real-time writing suggestions
- 🔄 Live connection to Blooming server
- ✨ One-click accept/reject
- 🎯 Multiple suggestion types (style, dialogue, pacing)
- 🛠️ Customizable settings

## Installation

### Development Mode

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `browser_plugin/` directory
5. The extension should now be installed!

## Usage

1. **Start the WebSocket server:**
   ```bash
   cd /Users/williamalston/Desktop/WriterAI/prometheus_novel
   python -m prometheus_lib.rewrite.websocket_server
   ```

2. **Click the extension icon** in Chrome toolbar

3. **Click "Connect to Server"**

4. **Select text** on any web page

5. **Click "Get Suggestions"**

6. **Review suggestions** and accept/reject

## Server Connection

**Default:** `ws://localhost:8765`

Make sure the WebSocket server is running before connecting.

## Settings

- **Authenticity Level:** Basic, Enhanced, Premium, Expert
- **Rewrite Mode:** Draft, Enhance, Polish, Experimental

## Supported Sites

Works on any website with editable content:
- Google Docs (partial support)
- Medium
- WordPress
- Any `contenteditable` element
- Text areas

## Future Enhancements

- [ ] Google Docs full integration
- [ ] Scrivener integration
- [ ] Custom keyboard shortcuts
- [ ] Suggestion history
- [ ] Offline mode

## Phase 3 Implementation

This browser plugin is part of Phase 3 of the Blooming Rewrite Engine 2.0.

**Status:** Foundation complete, ready for enhancement

---

*Browser Plugin - Version 1.0*  
*Phase 3 - Blooming Rewrite Engine 2.0*

