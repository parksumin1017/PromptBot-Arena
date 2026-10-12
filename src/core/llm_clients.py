"""Standardized Multi-Provider LLM Clients for PromptBot Arena.

Implements plug-and-play Adapter Pattern for LLM providers:
- BaseLLMClient: Unified abstract interface
- PostechSchoolLLMClient: Postech AI API (Posicube) a1(GPT), a2(Gemini), a3(Claude)
- OpenAIOfficialClient: Official OpenAI Chat Completions API
- GoogleGenAIOfficialClient: Official Google Gemini API
- MockLLMClient: Offline / Unit Test Mock Client
"""

import os
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class BaseLLMClient(ABC):
    """Abstract Base Class for all LLM Client Adapters."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send prompt to LLM and return raw response string.
        Raises RuntimeError or TimeoutError on failure.
        """
        pass


class PostechSchoolLLMClient(BaseLLMClient):
    """
    Adapter for Postech University GenAI Agent API (Posicube).
    Supports a1(gpt), a2(gemini), a3(claude) endpoints.
    """

    ENDPOINTS = {
        "gpt": "https://genai.postech.ac.kr/agent/api/a1/gpt",
        "gemini": "https://genai.postech.ac.kr/agent/api/a2/gemini",
        "claude": "https://genai.postech.ac.kr/agent/api/a3/claude",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_type: Optional[str] = None,
        timeout: float = 25.0
    ):
        self.api_key = api_key or os.getenv("POSTECH_API_KEY", "")
        self.model_type = (model_type or os.getenv("POSTECH_MODEL_TYPE", "gpt")).lower()
        self.timeout = timeout

        if not self.api_key:
            raise ValueError("POSTECH_API_KEY is not set.")
        if self.model_type not in self.ENDPOINTS:
            raise ValueError(f"Unsupported model_type: {self.model_type}. Must be one of {list(self.ENDPOINTS.keys())}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = self.ENDPOINTS[self.model_type]

        # Compose full prompt if system prompt provided
        full_message = f"{system_prompt}\n\n[User Request]\n{prompt}" if system_prompt else prompt

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        # Gemini and Claude require Authorization header without Bearer prefix
        if self.model_type in ("gemini", "claude"):
            headers["Authorization"] = self.api_key

        payload = {
            "message": full_message,
            "stream": False
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                raw_text = resp_bytes.decode("utf-8")
                return self._parse_response(raw_text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Postech API HTTP Error {e.code}: {err_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Postech API Connection Error: {e.reason}") from e
        except Exception as e:
            raise RuntimeError(f"Postech API Call Failed: {e}") from e

    def _parse_response(self, raw_text: str) -> str:
        """Extract text from diverse JSON envelope schemas."""
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text.strip()

        if isinstance(data, str):
            return data.strip()

        if isinstance(data, dict):
            # Check standard fields
            if "content" in data and isinstance(data["content"], str):
                return data["content"].strip()
            if "data" in data:
                d = data["data"]
                if isinstance(d, str):
                    return d.strip()
                if isinstance(d, dict):
                    if "content" in d:
                        return str(d["content"]).strip()
                    if "message" in d:
                        return str(d["message"]).strip()
            if "message" in data and isinstance(data["message"], str):
                return data["message"].strip()
            if "response" in data and isinstance(data["response"], str):
                return data["response"].strip()
            # OpenAI / Gemini choices fallback
            if "choices" in data and data["choices"]:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"].strip()

        return raw_text.strip()


class OpenAIOfficialClient(BaseLLMClient):
    """Adapter for official OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", timeout: float = 15.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = timeout
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI Official API Call Failed: {e}") from e


class GoogleGenAIOfficialClient(BaseLLMClient):
    """Adapter for official Google Gemini API via google-genai library."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Google GenAI Call Failed: {e}") from e


class MockLLMClient(BaseLLMClient):
    """Mock LLM Client for offline automated testing and CI."""

    def __init__(self):
        pass

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        lower = prompt.lower()
        if "사이드" in lower or "우회" in lower or "side" in lower or "flank" in lower:
            return '''```python
def policy_step(state: State) -> ActionCommand:
    # Maneuver via side
    target_pos = (250.0, 80.0)
    return move_to(target_pos)
```'''
        elif "수비" in lower or "방어" in lower or "defense" in lower:
            return '''```python
def policy_step(state: State) -> ActionCommand:
    # Return to home defense position
    home_pos = (100.0, 200.0)
    return move_to(home_pos)
```'''
        else:
            return '''```python
def policy_step(state: State) -> ActionCommand:
    # Push nearest puck to opponent territory
    target_puck = get_closest_puck(state.pucks, state.my_pos)
    if target_puck is None:
        return stop()
    target_x = 450.0 if state.my_team == "red" else 150.0
    action = push(target_puck, (target_x, 200.0))
    if will_collide(action):
        return stop()
    return action
```'''


def create_llm_client(provider: Optional[str] = None, **kwargs) -> BaseLLMClient:
    """
    Factory function for plug-and-play LLM clients.
    Reads provider from argument or LLM_PROVIDER in .env.
    Providers: 'postech' (default), 'openai', 'gemini', 'mock'.
    """
    p = (provider or os.getenv("LLM_PROVIDER", "postech")).lower()

    if p == "postech":
        return PostechSchoolLLMClient(**kwargs)
    elif p == "openai":
        return OpenAIOfficialClient(**kwargs)
    elif p == "gemini":
        return GoogleGenAIOfficialClient(**kwargs)
    elif p == "mock":
        return MockLLMClient()
    else:
        raise ValueError(f"Unknown LLM provider: {p}. Choose from 'postech', 'openai', 'gemini', 'mock'.")
