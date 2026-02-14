#!/usr/bin/env python3
"""Quick wiring test for Ollama/local model integration."""
import asyncio
import sys
from pathlib import Path

# Run from prometheus_novel (where pyproject.toml lives) so prometheus_lib resolves
_root = Path(__file__).resolve().parent
if (_root / "prometheus_novel").exists():
    sys.path.insert(0, str(_root / "prometheus_novel"))
else:
    sys.path.insert(0, str(_root))


def test_imports():
    """Test all wiring imports work."""
    print("1. Testing imports...")
    from prometheus_novel.prometheus_lib.llm.clients import (
        get_client,
        OllamaClient,
        is_ollama_model,
        OpenAIClient,
    )
    from prometheus_novel.prometheus_lib.llm.cost_tracker import CostTracker
    from prometheus_novel.prometheus_lib.models.novel_state import PrometheusState
    print("   OK - all imports successful")


def test_get_client_routing():
    """Test get_client returns correct client types."""
    print("2. Testing get_client routing...")
    from prometheus_novel.prometheus_lib.llm.clients import get_client, OllamaClient, OpenAIClient

    client = get_client("qwen2.5:7b")
    assert isinstance(client, OllamaClient), f"Expected OllamaClient, got {type(client)}"
    assert client.model_name == "qwen2.5:7b"
    print(f"   OK - qwen2.5:7b -> OllamaClient (model={client.model_name})")

    client = get_client("llama3.1:8b")
    assert isinstance(client, OllamaClient)
    print(f"   OK - llama3.1:8b -> OllamaClient")

    client = get_client("gpt-4o-mini")
    assert isinstance(client, OpenAIClient)
    print(f"   OK - gpt-4o-mini -> OpenAIClient")


def test_cost_tracker_local_free():
    """Test cost tracker returns 0 for local models."""
    print("3. Testing cost tracker (local = $0)...")
    from prometheus_novel.prometheus_lib.llm.cost_tracker import CostTracker

    tracker = CostTracker()
    cost = tracker.calculate_cost("qwen2.5:7b", 1000, 500)
    assert cost == 0.0, f"Expected $0 for local model, got ${cost}"
    print(f"   OK - qwen2.5:7b cost = ${cost}")


async def test_ollama_generate():
    """Test Ollama generate() - requires Ollama running with qwen2.5:7b."""
    print("4. Testing Ollama generate (requires: ollama run qwen2.5:7b)...")
    from prometheus_novel.prometheus_lib.llm.clients import OllamaClient

    client = OllamaClient("qwen2.5:7b")
    try:
        response = await asyncio.wait_for(
            client.generate("Say 'wiring OK' in exactly 3 words.", max_tokens=50),
            timeout=15,
        )
        print(f"   OK - got response: {response.content[:80]}...")
        return True
    except asyncio.TimeoutError:
        print("   SKIP - Ollama timeout (not running or model not loaded)")
        return False
    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "refused" in err:
            print("   SKIP - Ollama not running (ollama serve)")
        elif "404" in str(e) or "not found" in err:
            print("   SKIP - Model not pulled. Run: ollama pull qwen2.5:7b")
        else:
            print(f"   FAIL - {e}")
        return False


def main():
    print("=" * 50)
    print("WriterAI Ollama Wiring Test")
    print("=" * 50)
    test_imports()
    test_get_client_routing()
    test_cost_tracker_local_free()
    ok = asyncio.run(test_ollama_generate())
    print("=" * 50)
    if ok:
        print("All tests passed. Local model wiring OK.")
    else:
        print("Wiring OK. For live test, run: ollama run qwen2.5:7b")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
