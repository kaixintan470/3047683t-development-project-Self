"""Direct Ollama adapter for the configured local models."""

from ollama import Client

from core.config import DEFAULT_CONFIG


class OllamaClient:
    def __init__(self, host: str = "http://127.0.0.1:11434") -> None:
        self._client = Client(host=host)

    def generate(self, prompt: str, model: str, json_mode: bool = False) -> str:
        response = self._client.generate(
            model=model,
            prompt=prompt,
            format="json" if json_mode else "",
            options={"temperature": DEFAULT_CONFIG.model_temperature},
        )
        return response.response

    def available_models(self) -> set[str]:
        return {item.model for item in self._client.list().models if item.model}
