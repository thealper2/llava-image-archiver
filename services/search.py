import logging
from typing import List, Tuple

from db.database import Database
from db.models import Image, SearchResult
from services.image_processor import OllamaProcessor
from config import Config

logger = logging.getLogger(__name__)


class ImageSearch:
    """
    Search service for finding images using SQL and semantic search.
    """

    def __init__(self, database: Database, image_processor: OllamaProcessor):
        """
        Initialize the search service.

        Args:
            database (Database): Database instance
            image_processor (OllamaProcessor): Image processor instance
        """
        self.db = database
        self.image_processor = image_processor
        self.threshold = Config.SEMANTIC_SEARCH_THRESHOLD

    def search_by_sql(self, query: str, params: Tuple = ()) -> List[Image]:
        """
        Search images using SQL query.

        Args:
            query (str): SQL query string
            params (Tuple): Query parameters

        Returns:
            List[Image]: List of Image objects
        """
        try:
            results = self.db.get_images_by_sql_query(query, params)

            # Convert dictionary results to Image objects
            images = []
            for result in results:
                image = Image(
                    id=result.get("id"),
                    filepath=result.get("filepath", ""),
                    filename=result.get("filename", ""),
                    file_hash=result.get("file_hash", ""),
                    file_size=result.get("file_size", 0),
                    width=result.get("width"),
                    height=result.get("height"),
                    created_at=result.get("created_at"),
                    processed_at=result.get("processed_at"),
                    description=result.get("description"),
                )
                images.append(image)

            return images

        except Exception as e:
            logger.error(f"Error in SQL search: {e}")
            return []

    def search_by_description(self, description_query: str) -> List[SearchResult]:
        """
        Search images by semantic similarity to a description.

        Args:
            description_query (str): Text query to search for

        Returns:
            List[SearchResult]: List of SearchResult objects sorted by similarity
        """
        try:
            # Get query embedding
            query_embedding = self.image_processor.embedding_model.encode(
                description_query
            )

            # Get all embeddings from the database
            all_embeddings = self.db.get_all_embeddings()

            results = []
            for image_hash, embedding_bytes in all_embeddings:
                # Convert stored embedding back to numpy array
                stored_embedding = self.image_processor.bytes_to_embedding(
                    embedding_bytes
                )

                # Compute similarity
                similarity = self.image_processor.compute_similarity(
                    query_embedding, stored_embedding
                )

                # If similarity exceeds threshold, add to results
                if similarity >= self.threshold:
                    # Get the image data
                    image_data = self.db.get_image_by_hash(image_hash)
                    if image_data:
                        image = Image(
                            id=image_data.get("id"),
                            filepath=image_data.get("filepath", ""),
                            filename=image_data.get("filename", ""),
                            file_hash=image_data.get("file_hash", ""),
                            file_size=image_data.get("file_size", 0),
                            width=image_data.get("width"),
                            height=image_data.get("height"),
                            created_at=image_data.get("created_at"),
                            processed_at=image_data.get("processed_at"),
                            description=image_data.get("description"),
                        )
                        results.append(SearchResult(image=image, similarity=similarity))

            # Sort results by similarity (descending)
            results.sort(key=lambda x: x.similarity, reverse=True)

            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
