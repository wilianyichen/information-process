from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from infoproc.config import APISettings


class OpenAICompatibleClient:
    def __init__(self, settings: APISettings) -> None:
        self.settings = settings

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        api_key = self.settings.resolved_api_key()
        if not self.settings.base_url:
            raise RuntimeError("API base_url is not configured.")
        if not api_key:
            raise RuntimeError(
                f"API key is not configured. Set {self.settings.api_key_env} or api.api_key."
            )

        payload = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
        }
        base = self.settings.base_url.rstrip("/")
        url = f"{base}/chat/completions"
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API returned HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"OpenAI-compatible API request failed: {exc.reason}") from exc

        body: dict[str, Any] = json.loads(raw)
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected API response shape: {body}") from exc
