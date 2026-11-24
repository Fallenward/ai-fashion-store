import json
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import OLLAMA_PROTOCOL, SYSTEM_PROMPT
from app.core.config import get_settings
from app.models import AppSetting


@dataclass
class ToolCall:
    name: str
    arguments: dict
    call_id: str = ""
    thought_signature: str = ""


@dataclass
class Completion:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider:
    configured = True
    reason = ""
    name = "base"

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        raise NotImplementedError


class UnconfiguredProvider(LLMProvider):
    configured = False

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.name = "unconfigured"

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        return Completion(text=self.reason)


def ai_config(db: Session) -> dict:
    settings = get_settings()
    row = db.scalar(select(AppSetting).where(AppSetting.key == "ai"))
    override = row.value if row else {}
    provider = str(override.get("provider") or settings.llm_provider or "none").strip().lower()
    return {
        "provider": provider,
        "gemini_model": str(override.get("gemini_model") or settings.gemini_model),
        "ollama_base_url": str(override.get("ollama_base_url") or settings.ollama_base_url).rstrip("/"),
        "ollama_model": str(override.get("ollama_model") or settings.ollama_model),
        "embedding_provider": str(override.get("embedding_provider") or settings.embedding_provider or "local"),
        "gemini_configured": bool(settings.gemini_api_key.strip()),
    }


def public_ai_config(db: Session) -> dict:
    config = ai_config(db)
    config.pop("gemini_configured", None)
    public = dict(config)
    settings = get_settings()
    public["gemini_key_present"] = bool(settings.gemini_api_key.strip())
    public["stripe_enabled"] = settings.stripe_enabled
    public["payments"] = "stripe" if settings.stripe_enabled else "mock"
    return public


def save_ai_config(db: Session, payload: dict) -> dict:
    allowed = ("provider", "gemini_model", "ollama_base_url", "ollama_model", "embedding_provider")
    row = db.scalar(select(AppSetting).where(AppSetting.key == "ai"))
    value = dict(row.value) if row else {}
    for key in allowed:
        if key in payload and payload[key] is not None:
            value[key] = str(payload[key]).strip()
    if value.get("provider") and value["provider"] not in {"gemini", "ollama", "none"}:
        from app.core.exceptions import AppError

        raise AppError("Provider must be gemini, ollama, or none.")
    if value.get("embedding_provider") and value["embedding_provider"] not in {"local", "gemini", "ollama"}:
        from app.core.exceptions import AppError

        raise AppError("Embedding provider must be local, gemini, or ollama.")
    if row is None:
        row = AppSetting(key="ai", value=value)
        db.add(row)
    else:
        row.value = value
    db.commit()
    return public_ai_config(db)


def build_provider(db: Session) -> LLMProvider:
    config = ai_config(db)
    settings = get_settings()
    provider = config["provider"]
    if provider == "gemini":
        if not settings.gemini_api_key.strip():
            return UnconfiguredProvider(
                "The shopping assistant is set to Gemini, but GEMINI_API_KEY is empty. Add a key on the server, or switch the provider to Ollama. You can still browse and shop."
            )
        return GeminiProvider(settings.gemini_api_key.strip(), config["gemini_model"])
    if provider == "ollama":
        if not config["ollama_model"]:
            return UnconfiguredProvider(
                "The shopping assistant is set to Ollama, but OLLAMA_MODEL is empty. Set a local model name in the environment or the admin AI settings."
            )
        return OllamaProvider(config["ollama_base_url"], config["ollama_model"])
    return UnconfiguredProvider(
        "The shopping assistant is not configured. Set LLM_PROVIDER to gemini or ollama. The rest of the shop works without it."
    )


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        contents = []
        for message in messages:
            role = message["role"]
            if role == "tool":
                payload = _as_dict(message.get("content"))
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": message.get("tool_name") or "tool",
                                    "response": payload,
                                }
                            }
                        ],
                    }
                )
                continue
            if role == "assistant" and message.get("tool_calls"):
                parts = []
                if message.get("content"):
                    parts.append({"text": message["content"]})
                for call in message["tool_calls"]:
                    part = {"functionCall": {"name": call.name, "args": call.arguments or {}}}
                    if call.thought_signature:
                        part["thoughtSignature"] = call.thought_signature
                    parts.append(part)
                contents.append({"role": "model", "parts": parts})
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": message.get("content") or ""}]})
        body: dict = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents or [{"role": "user", "parts": [{"text": "Hello"}]}],
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
        }
        if tools:
            body["tools"] = [{"functionDeclarations": [_gemini_declaration(tool) for tool in tools]}]
        response = self._post(body)
        if response is None:
            raise RuntimeError("Gemini could not complete that request.")
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return Completion(text="I couldn't complete that. Please rephrase your question.")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text: list[str] = []
        calls: list[ToolCall] = []
        for part in parts:
            if part.get("text"):
                text.append(part["text"])
            if part.get("functionCall"):
                call = part["functionCall"]
                calls.append(
                    ToolCall(
                        name=call.get("name", ""),
                        arguments=call.get("args") or {},
                        thought_signature=part.get("thoughtSignature") or "",
                    )
                )
        return Completion(text="\n".join(text).strip() or None, tool_calls=calls)

    def _post(self, body: dict) -> httpx.Response | None:
        models = [self.model]
        for name in ("gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-lite-latest"):
            if name not in models:
                models.append(name)
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                response = httpx.post(url, json=body, headers={"x-goog-api-key": self.api_key}, timeout=60)
            except httpx.HTTPError:
                continue
            if response.status_code >= 400:
                continue
            self.model = model
            return response
        return None


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url
        self.model = model

    def complete(self, messages: list[dict], tools: list[dict]) -> Completion:
        payload_messages = [{"role": "system", "content": SYSTEM_PROMPT + "\n" + OLLAMA_PROTOCOL}]
        for message in messages:
            if message["role"] == "tool":
                payload_messages.append(
                    {"role": "tool", "content": message.get("content") or "{}", "name": message.get("tool_name") or "tool"}
                )
            elif message["role"] == "assistant" and message.get("tool_calls"):
                payload_messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": [
                            {"function": {"name": call.name, "arguments": call.arguments}} for call in message["tool_calls"]
                        ],
                    }
                )
            else:
                payload_messages.append({"role": message["role"], "content": message.get("content") or ""})
        body: dict = {"model": self.model, "messages": payload_messages, "stream": False}
        if tools:
            body["tools"] = [
                {"type": "function", "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["parameters"]}}
                for tool in tools
            ]
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=90)
        except httpx.HTTPError as exc:
            raise RuntimeError("Ollama is not reachable.") from exc
        if response.status_code >= 400:
            raise RuntimeError("Ollama could not complete that request.")
        message = response.json().get("message") or {}
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            calls.append(ToolCall(name=function.get("name", ""), arguments=arguments))
        content = (message.get("content") or "").strip()
        if calls:
            return Completion(text=content or None, tool_calls=calls)
        parsed = _parse_json_protocol(content)
        if parsed is not None:
            return parsed
        return Completion(text=content or "I couldn't complete that.")


def _parse_json_protocol(content: str) -> Completion | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and data.get("tool"):
        arguments = data.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        return Completion(tool_calls=[ToolCall(name=str(data["tool"]), arguments=arguments)])
    if isinstance(data, dict) and data.get("message"):
        return Completion(text=str(data["message"]))
    return None


def _as_dict(content: str | None) -> dict:
    if not content:
        return {"result": ""}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"result": content}
    if isinstance(parsed, dict):
        return parsed
    return {"result": parsed}


def _gemini_declaration(tool: dict) -> dict:
    return {"name": tool["name"], "description": tool["description"], "parameters": _upper_schema(tool["parameters"])}


def _upper_schema(schema: dict) -> dict:
    converted = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            converted[key] = value.upper()
        elif key == "properties" and isinstance(value, dict):
            converted[key] = {name: _upper_schema(child) for name, child in value.items()}
        elif key == "items" and isinstance(value, dict):
            converted[key] = _upper_schema(value)
        else:
            converted[key] = value
    return converted
