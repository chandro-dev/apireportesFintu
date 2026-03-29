from __future__ import annotations

import json
from urllib import parse, request


class GeminiTextGenerator:
    def __init__(
        self,
        *,
        api_key: str | None,
        models: list[str],
        default_max_output_tokens: int,
        timeout_seconds: int = 20,
    ) -> None:
        self._api_key = api_key
        self._models = [model for model in models if model]
        self._default_max_output_tokens = default_max_output_tokens
        self._timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self._api_key and self._models)

    def generate(
        self,
        *,
        prompt: str,
        temperature: float,
        max_output_tokens: int | None = None,
        preferred_model: str | None = None,
    ) -> tuple[str, str | None]:
        if not self.enabled:
            return "", None

        ordered_models = self._resolve_models(preferred_model)
        token_limit = max_output_tokens or self._default_max_output_tokens
        last_error: Exception | None = None

        for model in ordered_models:
            try:
                text = self._call_model(
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    max_output_tokens=token_limit,
                )
                if text.strip():
                    return text.strip(), model
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        return "", None

    def _resolve_models(self, preferred_model: str | None) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        ordered_candidates = [preferred_model, *self._models] if preferred_model else self._models
        for model in ordered_candidates:
            if not model:
                continue
            if model in seen:
                continue
            seen.add(model)
            result.append(model)

        return result

    def _call_model(
        self,
        *,
        model: str,
        prompt: str,
        temperature: float,
        max_output_tokens: int,
    ) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={parse.quote(self._api_key or '')}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(req, timeout=self._timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        candidates = body.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return ""

        return parts[0].get("text", "")
