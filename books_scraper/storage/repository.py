import logging
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class BookRepository(ABC):
    """Interface the pipeline depends on"""

    @abstractmethod
    def open(self, reset: bool = False) -> None:
        """Open the connection and ensure the schema exists."""

    @abstractmethod
    def save(self, book: dict) -> None:
        """Persist one cleaned book."""

    @abstractmethod
    def close(self) -> None:
        """Commit and release resources."""


class SQLiteBookRepository(BookRepository):
    """Stores books in a SQLite table keyed by ``product_url``."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS books (
        product_url  TEXT PRIMARY KEY,
        title        TEXT NOT NULL,
        price        REAL NOT NULL,
        availability INTEGER NOT NULL,
        image_url    TEXT,
        category     TEXT NOT NULL
    )"""
    UPSERT = """
    INSERT INTO books (product_url, title, price, availability, image_url, category)
    VALUES (:product_url, :title, :price, :availability, :image_url, :category)
    ON CONFLICT(product_url) DO UPDATE SET
        title=excluded.title, price=excluded.price,
        availability=excluded.availability, image_url=excluded.image_url,
        category=excluded.category"""

    def __init__(self, path: str) -> None:
        """Remember the database file path."""
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def open(self, reset: bool = False) -> None:
        """Connect, create the schema and optionally empty the table."""
        Path(self.path).resolve().parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(self.SCHEMA)
        if reset:
            self._conn.execute("DELETE FROM books")
        self._conn.commit()
        logger.info("SQLite database ready at %s", self.path)

    def save(self, book: dict) -> None:
        """Insert or update a book (booleans are stored as 0/1)."""
        row = dict(book)
        row["availability"] = int(bool(row["availability"]))
        self._conn.execute(self.UPSERT, row)

    def close(self) -> None:
        """Commit pending writes and close the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
