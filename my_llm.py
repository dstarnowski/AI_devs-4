import os
import sqlite3
from datetime import datetime

import requests


class MyLLM:
    """Bridge to the OpenRouter API with per-session model pricing cache and usage logging."""

    _BASE_URL = "https://openrouter.ai/api/v1"
    _DB_FILE = "openrouter_logs.db"
    _LOCAL_DB_FILE = "local_llm_logs.db"

    def __init__(self, api_key: str = None, local_llm: bool = True, local_llm_url: str = None, agent_display = None):
        self._local_llm = local_llm
        self._api_key = api_key
        self._local_llm_url = local_llm_url
        self._agent_display = agent_display
        self._models: dict[str, dict[str, float]] = {}
        self._session_stats: dict[str, int | float] = {
            "executions": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_price": 0.0,
        }
        self._init_db()

    def _init_db(self) -> None:
        self._db_file = self._LOCAL_DB_FILE if self._local_llm else self._DB_FILE
        db_exists = os.path.exists(self._db_file)
        conn = sqlite3.connect(self._db_file)
        if not db_exists:
            conn.execute(
                """
                CREATE TABLE llm_logs (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp     TEXT    NOT NULL,
                    model         TEXT    NOT NULL,
                    input_tokens  INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    input_price   REAL    NOT NULL,
                    output_price  REAL    NOT NULL,
                    label         TEXT    NOT NULL DEFAULT ''
                )
                """
            )
            conn.commit()
        conn.close()

    def _log_to_db(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        input_price: float,
        output_price: float,
        label: str,
    ) -> None:
        conn = sqlite3.connect(self._db_file)
        conn.execute(
            """
            INSERT INTO llm_logs
                (timestamp, model, input_tokens, output_tokens, input_price, output_price, label)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                model,
                input_tokens,
                output_tokens,
                input_price,
                output_price,
                label,
            ),
        )
        conn.commit()
        conn.close()

    def _record_usage(self, model: str, data: dict, label: str) -> None:
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        if not self._local_llm:
            pricing = self._models[model]
            input_cost = input_tokens * pricing["prompt"]
            output_cost = output_tokens * pricing["completion"]
            total_cost = input_cost + output_cost
        else:
            input_cost = 0
            output_cost = 0
            total_cost = 0

        self._agent_display.log(
            f"[{label}] "
            f"IN: {input_tokens} tokens (${input_cost:.6f}) | "
            f"OUT: {output_tokens} tokens (${output_cost:.6f}) | "
            f"TOTAL: ${total_cost:.6f}"
        )

        self._log_to_db(model, input_tokens, output_tokens, input_cost, output_cost, label)

        self._session_stats["executions"] += 1
        self._session_stats["total_input_tokens"] += input_tokens
        self._session_stats["total_output_tokens"] += output_tokens
        self._session_stats["total_price"] += total_cost
        self._agent_display.stats(self._session_stats["total_input_tokens"], self._session_stats["total_output_tokens"], self._session_stats["total_price"])

    def get_session_stats(self) -> dict[str, int | float]:
        return dict(self._session_stats)

    def _headers(self) -> dict[str, str]:
        if self._api_key is not None:
            return {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
        else:
            return {
                "Content-Type": "application/json",
            }

    def _fetch_model_pricing(self, model: str) -> None:
        resp = requests.get(
            f"{self._BASE_URL}/models",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()

        for entry in resp.json().get("data", []):
            if entry.get("id") == model:
                pricing = entry.get("pricing", {})
                self._models[model] = {
                    "prompt": float(pricing.get("prompt", 0)),
                    "completion": float(pricing.get("completion", 0)),
                }
                return

        raise ValueError(f"Model '{model}' not found on OpenRouter")

    def chat(
        self,
        messages: list[dict],
        model: str = "openai/gpt-4.1-mini",
        temperature: float = 0,
        label: str = "",
        response_format: dict | None = None,
        reasoning_effort: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | dict:
        """Send a chat completion request.

        Returns the assistant message content as a string, or the full
        assistant message dict when tool_calls are present.
        """
        if model not in self._models and not self._local_llm:
            self._fetch_model_pricing(model)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if reasoning_effort is not None:
            payload["reasoning_effort"] = reasoning_effort
        if tools is not None:
            payload["tools"] = tools
        url = self._local_llm_url if self._local_llm else self._BASE_URL
        resp = requests.post(
            f"{url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        message = data["choices"][0]["message"]
        self._record_usage(model, data, label)

        return message
