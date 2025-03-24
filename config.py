import os
from dataclasses import dataclass


@dataclass
class Config:
    """
    Configuration class for the application settings.
    """

    # Database settings
    DB_PATH: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "image_archive.db"
    )

    # Ollama API settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llava:latest"

    # Image settings
    SUPPORTED_EXTENSIONS: tuple = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

    # Embedding settings
    VECTOR_DIMENSION: int = (
        384  # Default dimension for sentence-transformers embeddings
    )

    # Search settings
    SEARCH_RESULTS_PER_PAGE: int = 20
    SEMANTIC_SEARCH_THRESHOLD: float = 0.5  # Similarity threshold for semantic search
