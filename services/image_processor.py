import base64
import logging
import requests
import numpy as np
import time
from sentence_transformers import SentenceTransformer

from config import Config

logger = logging.getLogger(__name__)


class OllamaProcessor:
    """
    Image processor using the Ollama API with llava model.
    """

    def __init__(
        self,
        base_url: str = None,
        model_name: str = None,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """
        Initialize the Ollama processor.

        Args:
            base_url (str): Base URL of the Ollama API
            model_name (str): Name of the model to use
            embedding_model (str): Name of the sentence transformer model for embeddings
        """
        self.base_url = base_url or Config.OLLAMA_BASE_URL
        self.model_name = model_name or Config.OLLAMA_MODEL
        self.embedding_model = SentenceTransformer(embedding_model)

    def describe_image(self, image_path: str) -> str:
        """
        Get a descriptive caption for an image using the llava model.

        Args:
            image_path (str): Path to the image file

        Returns:
            str: Description of the image
        """
        try:
            # Encode the image as base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # Prepare prompt for detailed image description
            prompt = "Please describe this image in detail. Include information about objects, people, activities, setting, colors and any notable elements."

            # Send request to Ollama API
            api_url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False,
            }

            # Retry mechanism
            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    response = requests.post(api_url, json=payload, timeout=60)
                    response.raise_for_status()
                    break

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Attemp {attempt + 1}/{max_retries} failed: {e}")
                    if attempt == max_retries - 1:
                        raise

                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

            # Parse the response
            result = response.json()
            description = result.get("response", "").strip()

            # Clean up the description
            # Remove any preamble like "Here's a description of the image:"
            lines = description.split("\n")
            cleaned_lines = []
            started = False

            for line in lines:
                line = line.strip()
                if not started and (
                    line.startswith("Here") or line.startswith("This image") or not line
                ):
                    continue

                started = True
                if line:
                    cleaned_lines.append(line)

            cleaned_description = " ".join(cleaned_lines)

            return cleaned_description if cleaned_description else description

        except Exception as e:
            logger.error(f"Error describing image {image_path}: {e}")
            return f"Error processing image: {str(e)}"

    def create_embedding(self, text: str) -> bytes:
        """
        Create an embedding vector for a text description.

        Args:
            text (str): Text to embed

        Returns:
            bytes: Embedding vector as bytes
        """
        try:
            # Create embedding
            embedding = self.embedding_model.encode(text)

            # Convert to bytes for storage
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

            return embedding_bytes

        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            return None

    def bytes_to_embedding(self, embedding_bytes: bytes) -> np.ndarray:
        """
        Convert embedding bytes back to a numpy array.

        Args:
            embedding_bytes: Embedding vector as bytes

        Returns:
            Embedding vector as numpy array
        """
        return np.frombuffer(embedding_bytes, dtype=np.float32)

    def compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1 (np.ndarray): First embedding vector
            embedding2 (np.ndarray): Second embedding vector

        Returns:
            float: Cosine similarity score (0-1)
        """
        # Normalize embedding
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)

        # Compute cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)

        return float(similarity)
