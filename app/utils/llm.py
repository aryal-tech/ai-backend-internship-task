import ollama
from app.core.config import get_settings

_SETTINGS = get_settings()

class LLMClient:
    def __init__(self):
        self.provider = _SETTINGS.LLM_PROVIDER
        self.model = _SETTINGS.LLM_MODEL
        if self.provider == "ollama":
            self.client = ollama.AsyncClient(host=_SETTINGS.OLLAMA_HOST)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def generate(self, messages, temperature=0.1, max_tokens=1024):
        response = await self.client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response['message']['content']

    async def generate_with_tools(self, messages, tools):
        response = await self.client.chat(
            model=self.model,
            messages=messages,
            tools=tools,
        )
    
        return response