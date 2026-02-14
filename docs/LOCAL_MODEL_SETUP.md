# Local Model Setup (Ollama) - Zero Cost Writing

WriterAI is now configured to use **local models by default** via [Ollama](https://ollama.com). No API keys or costs required.

## Quick Start

1. **Install Ollama** (if not already installed):
   - Windows/Mac: Download from [ollama.com](https://ollama.com)
   - Linux: `curl -fsSL https://ollama.com/install.sh | sh`

2. **Pull a recommended model for creative writing:**
   ```bash
   ollama run qwen2.5:7b
   ```
   This downloads and runs the model. Press Ctrl+C to stop; it stays available.

3. **Start WriterAI** – it will automatically use your local Ollama:
   ```bash
   .\start_writerai.bat   # Windows
   # or
   ./start_writerai.sh   # Mac/Linux
   ```

## Recommended Models for Writing

| Model | Command | Best For | VRAM |
|-------|---------|----------|------|
| **Qwen 2.5 7B** | `ollama run qwen2.5:7b` | General creative writing (default) | 8GB |
| **Llama 3.1 8B** | `ollama run llama3.1:8b` | Balanced quality/speed | 8GB |
| **Llama 3.2 3B** | `ollama run llama3.2:3b` | Fast, lower VRAM | 4GB |
| **Mistral 7B** | `ollama run mistral:7b` | Strong prose | 8GB |
| **Phi-3 Mini** | `ollama run phi3:mini` | Compact, capable | 4GB |

## Changing the Model

- **Settings page**: Choose a different model from the dropdown (local options listed first)
- **Project config**: Edit `config.yaml` in your project:
  ```yaml
  model_defaults:
    api_model: qwen2.5:7b      # or llama3.1:8b, mistral:7b, etc.
    critic_model: qwen2.5:7b
    fallback_model: qwen2.5:7b
  ```

## Environment Variables

- `OLLAMA_BASE_URL` – Default: `http://localhost:11434/v1`. Change if Ollama runs elsewhere.
- `WRITERAI_DEFAULT_MODEL` – Override the default model (e.g. `llama3.1:8b`).

## Using API Models (Optional)

To use paid APIs (OpenAI, Anthropic, Google), add API keys in Settings and select an API model. Budget tracking applies to API usage; local models always show $0 cost.
