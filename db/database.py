import sqlite3
from typing import Optional, Any, List, Dict, Tuple
import logging

from config import Config

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for the image archiver application.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connection.
        """
        self.db_path = db_path or Config.DB_PATH
        self.connection = None

    def connect(self) -> None:
        """
        Establish a database connection.
        """
        try:
            self.connection = sqlite3.connect(self.db_path)
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Configure to return rows as dictionaries
            self.connection.row_factory = sqlite3.Row

        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def disconnect(self) -> None:
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
            self.connection = None

    def initialize_db(self) -> None:
        """
        Create database tables if they don't exist.
        """
        try:
            self.connect()
            cursor = self.connection.cursor()

            # Images table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    file_hash TEXT UNIQUE NOT NULL,
                    file_size INTEGER NOT NULL,
                    width INTEGER,
                    height INTEGER,
                    created_at TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP           
                )
            """)

            # Image descriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_hash TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    embedding BLOB,
                    FOREIGN KEY (image_hash) REFERENCES images(file_hash)           
                )
            """)

            # Image tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL           
                )
            """)

            # Image-tag relationship table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS image_tags (
                    image_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (image_id, tag_id),
                    FOREIGN KEY (image_id) REFERENCES images(id),
                    FOREIGN KEY (tag_id) REFERENCES tags(id)           
                )
            """)

            self.connection.commit()

        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            if self.connection:
                self.connection.rollback()

            raise

        finally:
            self.disconnect()

    def insert_image(self, image_data: Dict[str, Any]) -> int:
        """
        Insert an image record into the database.

        Args:
            image_data (Dict[str, Any]): Dictionary containing image data

        Returns:
            int: The ID of the inserted image
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            columns = ", ".join(image_data.keys())
            placeholders = ", ".join(["?" for _ in image_data])
            values = tuple(image_data.values())

            query = f"""
                INSERT OR IGNORE INTO images ({columns})
                VALUES ({placeholders})
            """

            cursor.execute(query, values)
            self.connection.commit()

            # Get the image ID
            if cursor.lastrowid:
                return cursor.lastrowid
            else:
                # If the image already exists, get its ID
                cursor.execute(
                    "SELECT id FROM images WHERE file_hash = ?",
                    (image_data["file_hash"],),
                )
                return cursor.fetchone()["id"]

        except sqlite3.Error as e:
            logger.error(f"Error inserting image: {e}")
            if self.connection:
                self.connection.rollback()

            raise

        finally:
            self.disconnect()

    def insert_description(
        self, image_hash: str, description: str, embedding: Optional[bytes] = None
    ) -> int:
        """
        Insert or update an image description.

        Args:
            image_hash (str): Hash of the image
            description (str): Textual description of the image
            embedding (Optional[bytes]): Vector embedding of the description

        Returns:
            int: The ID of the inserted description
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            query = """
                INSERT INTO descriptions (image_hash, description, embedding)
                VALUES (?, ?, ?)
                ON CONFLICT(image_hash) DO UPDATE SET
                description = excluded.description,
                embedding = excluded.embedding
            """

            cursor.execute(query, (image_hash, description, embedding))
            self.connection.commit()

            return cursor.lastrowid

        except sqlite3.Error as e:
            logger.error(f"Error inserting description: {e}")
            if self.connection:
                self.connection.rollback()

            raise

        finally:
            self.disconnect()

    def get_image_by_hash(self, file_hash: str) -> Dict[str, Any]:
        """
        Get image information by file hash.

        Args:
            file_hash (str): Hash of the image file

        Returns:
            Dict[str, Any]: Dictionary containing image data
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            query = """
                SELECT i.*, d.description
                FROM images i
                LEFT JOIN descriptions d ON i.file_hash = d.image_hash
                WHERE i.file_hash = ?
            """

            cursor.execute(query, (file_hash,))
            result = cursor.fetchone()

            if result:
                return dict(result)

            return None

        except sqlite3.Error as e:
            logger.error(f"Error retrieving image: {e}")
            raise

        finally:
            self.disconnect()

    def get_images_by_sql_query(
        self, sql_query: str, params: Tuple = ()
    ) -> List[Dict[str, Any]]:
        """
        Get images by executing a SQL query.

        Args:
            sql_query (str): SQL query string
            params (Tuple): Query parameters

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing image data
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            cursor.execute(sql_query, params)
            results = cursor.fetchall()

            return [dict(row) for row in results]

        except sqlite3.Error as e:
            logger.error(f"Error executing SQL query: {e}")
            raise

        finally:
            self.disconnect()

    def get_description_embedding(self, image_hash: str) -> Optional[bytes]:
        """
        Get the embedding for an image description.

        Args:
            image_hash (str): Hash of the image

        Returns:
            Optional[bytes]: Embedding as bytes or None if not found
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            query = """
                SELECT embedding
                FROM descriptions
                WHERE image_hash = ?
            """

            cursor.execute(query, (image_hash,))
            result = cursor.fetchone()

            if result in result["embedding"]:
                return result["embedding"]

            return None

        except sqlite3.Error as e:
            logger.error(f"Error retrieving embedding: {e}")
            raise

        finally:
            self.disconnect()

    def get_all_embeddings(self) -> List[Tuple[str, bytes]]:
        """
        Get all description embeddings.

        Returns:
            List[Tuple[str, bytes]]: List of tuples containing (image_hash, embedding)
        """

        try:
            self.connect()
            cursor = self.connection.cursor()

            query = """
                SELECT image_hash, embedding
                FROM descriptions
                WHERE embedding IS NOT NULL
            """

            cursor.execute(query)
            results = cursor.fetchall()

            return [(row["image_hash"], row["embedding"]) for row in results]

        except sqlite3.Error as e:
            logger.error(f"Error retrieving embeddings: {e}")
            raise

        finally:
            self.disconnect()
