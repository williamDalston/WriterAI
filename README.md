# WriterAI: AI Novel Generation System

WriterAI is a powerful, unified AI writing assistant that combines a FastAPI web dashboard, a real-time WebSocket engine, and a browser plugin to help you research, outline, and write novels.

![WriterAI Dashboard](https://via.placeholder.com/800x400?text=WriterAI+Dashboard)

## 🚀 Key Features

- **Unified Architecture**: Single-process application combining web server and real-time engine.
- **Real-Time Dashboard**: Live progress updates for long-running generation jobs.
- **Browser Plugin**: Deep integration allows you to "Create Project" or "Save Idea" directly from any webpage.
- **Ideas Manager**: Capture, organize, and instantly convert ideas into full projects.
- **Settings Management**: Configure API keys, models (GPT-4o, Claude 3.5), and themes directly from the UI.
- **Modern UI/UX**: Glassmorphism design, mobile responsiveness, and dark mode support.

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Node.js (for development only)
- OpenAI API Key (or Anthropic API Key)

### Quick Start

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/williamDalston/WriterAI.git
    cd WriterAI
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    ./start_writerai.sh
    ```
    *On Windows, run `start_writerai.bat`*

4.  **Open the Dashboard:**
    Navigate to [http://localhost:8080](http://localhost:8080) in your browser.

## 🧩 Browser Plugin

The WriterAI Browser Plugin allows you to capture inspiration from anywhere on the web.

1.  Open Chrome/Edge and go to `chrome://extensions`.
2.  Enable "Developer mode".
3.  Click "Load unpacked" and select the `browser_plugin` directory.
4.  Pin the extension to your toolbar.

**Usage:**
- Select text on any webpage.
- Click the WriterAI icon.
- Click **"Create New Project"** to start a novel from the selection.
- Click **"Save as Idea"** to store it for later.

## ⚙️ Configuration

You can configure the application via the **Settings** page in the dashboard or by creating a `.env` file:

```env
OPENAI_API_KEY=sk-...
PORT=8080
DEFAULT_MODEL=gpt-4o
```

## 🏗️ Architecture

WriterAI is built with:
- **FastAPI**: High-performance web framework.
- **WebSockets**: Real-time communication for job updates and plugin interaction.
- **Jinja2**: Server-side template rendering.
- **SQLite**: Lightweight database for ideas and project metadata.
- **Vanilla JS/CSS**: Lightweight, dependency-free frontend.

## 🤝 Contributing

Contributions are welcome! Please read `CONTRIBUTING.md` for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
