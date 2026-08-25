from abc import ABC, abstractmethod
from typing import List

class BaseEmbedding(ABC):
    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single query string.
        """
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embedding vectors for a list of document strings.
        """
        pass
