from abc import ABC, abstractmethod

class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """
        Generate a text response given a prompt and optional system prompt.
        """
        pass
        
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        Check if the LLM provider endpoint is online and functioning.
        """
        pass
