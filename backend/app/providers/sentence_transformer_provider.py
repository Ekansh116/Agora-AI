from typing import List
from sentence_transformers import SentenceTransformer
from app.providers.base_embedding import BaseEmbedding
from app.core.config import settings

class SentenceTransformerProvider(BaseEmbedding):
    def __init__(self):
        # Loads sentence-transformer model (cached locally)
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text, show_progress_bar=False)
        return embedding.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
