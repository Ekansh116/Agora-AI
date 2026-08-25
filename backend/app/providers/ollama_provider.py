import requests
from app.providers.base_llm import BaseLLM
from app.core.config import settings

class OllamaProvider(BaseLLM):
    def __init__(self):
        self.base_url = settings.OLLAMA_URL.rstrip('/')
        self.model = settings.LLM_MODEL

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    def is_healthy(self) -> bool:
        try:
            # Check if base URL is responding
            response = requests.get(self.base_url, timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if tags endpoint lists our configured model
            list_response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if list_response.status_code == 200:
                models = [m["name"] for m in list_response.json().get("models", [])]
                if self.model in models or any(self.model in m for m in models):
                    return True
                print(f"Configured model '{self.model}' not found in Ollama. Available: {models}")
            return True
        except Exception as e:
            print(f"Ollama health check failed: {str(e)}")
            return False
