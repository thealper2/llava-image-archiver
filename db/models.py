from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass
class Image:
    """
    Model representing an image in the database.
    """

    id: Optional[int] = None
    filepath: str = ""
    filename: str = ""
    file_hash: str = ""
    file_size: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: Optional[str] = None
    processed_at: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        """
        Initialize default values for optional fields.
        """
        if self.tags is None:
            self.tags = []

        if self.processed_at is None:
            self.processed_at = datetime.now().isoformat()


@dataclass
class ImageDescription:
    """
    Model representing an image description.
    """

    id: Optional[int] = None
    image_hash: str = ""
    description: str = ""
    embedding: Optional[bytes] = None


@dataclass
class Tag:
    """
    Model representing an image tag.
    """

    id: Optional[int] = None
    name: str = ""


@dataclass
class SearchResult:
    """
    Model representing a search result.
    """

    image: Image
    similarity: float = 1.0  # For semantic search results
