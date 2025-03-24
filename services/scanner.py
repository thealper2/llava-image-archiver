import os
import hashlib
from typing import Dict, Any, Generator
import logging
from pathlib import Path
from datetime import datetime
import PIL.Image
from tqdm import tqdm

from config import Config

logger = logging.getLogger(__name__)


class ImageScanner:
    """
    Scanner for finding and processing image files in directories.
    """

    def __init__(self, supported_extensions: tuple = None):
        """
        Initialize the image scanner.

        Args:
            supported_extensions (tuple): Tuple of supported image file extensions
        """
        self.supported_extensions = supported_extensions or Config.SUPPORTED_EXTENSIONS

    def scan_directory(
        self, directory_path: str
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Scan a directory recursively for image files.

        Args:
            directory_path (str): Path to the directory to scan

        Yields:
            Dictionary with image file information
        """
        try:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                logger.error(
                    f"Directory not found or not a directory: {directory_path}"
                )
                return

            logger.info(f"Scanning directory: {directory_path}")

            # Get all files recursively
            all_files = []
            for root, _, files in os.walk(directory_path):
                for file in files:
                    all_files.append(os.path.join(root, file))

            # Filter image files and process them with progress bar
            image_files = [f for f in all_files if self._is_image_file(f)]
            for filepath in tqdm(image_files, desc="Processing images"):
                try:
                    image_info = self._process_image_file(filepath)
                    if image_info:
                        yield image_info

                except Exception as e:
                    logger.error(f"Error processing image file {filepath}: {e}")

        except Exception as e:
            logger.error(f"Error scanning directory {directory_path}: {e}")

    def _is_image_file(self, filepath: str) -> bool:
        """
        Check if a file is an image based on its extensions.

        Args:
            filepath (str): Path to the file

        Returns:
            bool: True if the file is an image, False otherwise
        """
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.supported_extensions

    def _compute_file_hash(self, filepath: str) -> str:
        """
        Compute SHA-256 hash of a file.

        Args:
            filepath (str): Path to the file

        Returns:
            str: SHA-256 hash as a hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def _process_image_file(self, filepath: str) -> Dict[str, Any]:
        """
        Process an image file to extract its metadata.

        Args:
            filepath (str): Path to the image file

        Returns:
            Dict[str, Any]: Dictionary with image file information
        """
        try:
            # Basic file information
            file_stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            file_hash = self._compute_file_hash(filepath)
            file_size = file_stat.st_size

            # Try to get image dimensions
            width, height = None, None
            try:
                with PIL.Image.open(filepath) as img:
                    width, height = img.size

            except Exception as e:
                logger.warning(f"Could not get dimensions for {filepath}: {e}")

            # Get file creation time
            created_at = datetime.fromtimestamp(file_stat.st_ctime).isoformat()

            return {
                "filepath": filepath,
                "filename": filename,
                "file_hash": file_hash,
                "file_size": file_size,
                "width": width,
                "height": height,
                "created_at": created_at,
            }

        except Exception as e:
            logger.error(f"Error processing image {filepath}: {e}")
            return None
