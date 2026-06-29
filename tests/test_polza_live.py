"""Live smoke tests for Polza.ai provider — requires POLZA_API_KEY.

Usage:
    POLZA_API_KEY=*** python -m pytest tests/test_polza_live.py -x -v
"""

from __future__ import annotations

import os

import pytest
from openai import OpenAI

POLZA_API_KEY = os.environ.get("POLZA_API_KEY", "")
REQUIRES_KEY = pytest.mark.skipif(
    not POLZA_API_KEY,
    reason="POLZA_API_KEY environment variable not set",
)


@pytest.fixture
def client():
    return OpenAI(
        base_url="https://polza.ai/api/v1",
        api_key=POLZA_API_KEY,
    )


class TestPolzaLive:
    """Live API tests — requires a valid POLZA_API_KEY."""

    @REQUIRES_KEY
    def test_chat_completion(self, client):
        resp = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Say hello in one word"}],
            max_tokens=10,
        )
        assert resp.choices
        assert resp.choices[0].message.content
        assert resp.usage
        assert resp.usage.total_tokens > 0

    @REQUIRES_KEY
    def test_streaming(self, client):
        stream = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Count to 3"}],
            stream=True,
            max_tokens=20,
        )
        chunks = list(stream)
        assert len(chunks) > 0

    @REQUIRES_KEY
    def test_tool_calling(self, client):
        resp = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "What's the weather in Moscow?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"}
                        },
                        "required": ["city"]
                    }
                }
            }],
            tool_choice="required",
        )
        msg = resp.choices[0].message
        assert msg.tool_calls
        assert msg.tool_calls[0].function.name == "get_weather"

    @REQUIRES_KEY
    def test_provider_routing(self, client):
        resp = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'hi'"}],
            extra_body={
                "provider": {
                    "only": ["OpenAI"],
                    "sort": "price",
                }
            },
            max_tokens=5,
        )
        assert resp.choices[0].message.content

    @REQUIRES_KEY
    def test_reasoning(self, client):
        """Test reasoning effort with a reasoning-capable model."""
        resp = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[{"role": "user", "content": "Solve: 2x + 5 = 13"}],
            max_tokens=250,
            extra_body={
                "reasoning": {
                    "effort": "low",
                    "enabled": True,
                }
            },
        )
        assert resp.choices[0].message.content
