"""
NVIDIA NIM LLM Client with Auto-Key Rotation, Model Fallback, and Function Calling.
"""
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Generator, Optional
import config

logger = logging.getLogger("IGIRS.LLM")

class NvidiaLLMClient:
    def __init__(self, api_keys: Optional[List[str]] = None, base_url: str = config.NVIDIA_BASE_URL):
        self.api_keys = api_keys or config.NVIDIA_API_KEYS
        self.base_url = base_url.rstrip("/")
        self.current_key_index = 0
        self.primary_model = config.PRIMARY_LLM_MODEL
        self.fallback_models = config.FALLBACK_LLM_MODELS

    @property
    def current_api_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No NVIDIA API keys configured.")
        return self.api_keys[self.current_key_index % len(self.api_keys)]

    def rotate_key(self):
        """Rotate to next available API key."""
        prev = self.current_key_index
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.warning(f"Rotating NVIDIA API key index from {prev} to {self.current_key_index}")

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = config.LLM_TEMPERATURE,
        max_tokens: int = config.LLM_MAX_TOKENS,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a chat completion with automatic key rotation and model fallback.
        """
        models_to_try = [model or self.primary_model] + [m for m in self.fallback_models if m != (model or self.primary_model)]
        
        last_error = None
        for attempt_model in models_to_try:
            for _ in range(len(self.api_keys)):
                payload = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = tool_choice

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.current_api_key}",
                    "User-Agent": "IGIRS-AI/1.0"
                }

                url = f"{self.base_url}/chat/completions"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )

                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        res_data = resp.read().decode("utf-8")
                        return json.loads(res_data)
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode("utf-8")
                    last_error = f"HTTP {e.code} on model {attempt_model}: {error_body}"
                    logger.error(last_error)
                    if e.code in (401, 403, 429):
                        self.rotate_key()
                        continue
                    else:
                        break
                except Exception as ex:
                    last_error = str(ex)
                    logger.error(f"Network error on model {attempt_model}: {ex}")
                    self.rotate_key()
                    continue

        raise RuntimeError(f"All NVIDIA NIM completion attempts failed. Last error: {last_error}")

    def stream_chat_completion(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = config.LLM_TEMPERATURE,
        max_tokens: int = config.LLM_MAX_TOKENS,
        model: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Streams response chunks from NVIDIA NIM API.
        """
        models_to_try = [model or self.primary_model] + [m for m in self.fallback_models if m != (model or self.primary_model)]

        for attempt_model in models_to_try:
            for _ in range(len(self.api_keys)):
                payload = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.current_api_key}",
                    "User-Agent": "IGIRS-AI/1.0"
                }

                url = f"{self.base_url}/chat/completions"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST"
                )

                try:
                    with urllib.request.urlopen(req, timeout=45) as resp:
                        for line in resp:
                            line_str = line.decode("utf-8").strip()
                            if not line_str or line_str.startswith(":"):
                                continue
                            if line_str.startswith("data: "):
                                data_content = line_str[6:].strip()
                                if data_content == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_content)
                                    choices = chunk.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        content = delta.get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                    return
                except urllib.error.HTTPError as e:
                    if e.code in (401, 403, 429):
                        self.rotate_key()
                        continue
                    else:
                        break
                except Exception:
                    self.rotate_key()
                    continue

    def vision_chat_completion(
        self,
        prompt: str,
        image_base64: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 350
    ) -> str:
        """
        Processes a multimodal vision query with an image using meta/llama-3.2-11b-vision-instruct.
        """
        vision_model = "meta/llama-3.2-11b-vision-instruct"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        })

        for _ in range(len(self.api_keys)):
            payload = {
                "model": vision_model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": max_tokens
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.current_api_key}",
                "User-Agent": "IGIRS-AI/1.0"
            }

            url = f"{self.base_url}/chat/completions"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                    return "No visual description returned."
            except urllib.error.HTTPError as e:
                logger.error(f"Vision API HTTP error {e.code}: {e}")
                self.rotate_key()
                continue
            except Exception as ex:
                logger.error(f"Vision network error: {ex}")
                self.rotate_key()
                continue

        return "Could not process image due to network connectivity issues."
