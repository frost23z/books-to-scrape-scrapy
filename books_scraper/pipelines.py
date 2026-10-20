import logging

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

from books_scraper.services.cleaning import (
    normalize_text,
    parse_availability,
    parse_price,
)
from books_scraper.storage.repository import BookRepository, SQLiteBookRepository

logger = logging.getLogger(__name__)

TEXT_FIELDS = ("title", "product_url", "image_url", "category")


class CleaningPipeline:
    """Trims text, converts price to float and availability to bool."""

    def process_item(self, item):
        """Return the item with normalised values; drop it if price is unusable."""
        adapter = ItemAdapter(item)
        for name in TEXT_FIELDS:
            adapter[name] = normalize_text(adapter.get(name))
        try:
            adapter["price"] = parse_price(adapter.get("price"))
        except ValueError as exc:
            raise DropItem(f"Invalid price for {adapter.get('product_url')}: {exc}") from exc
        adapter["availability"] = parse_availability(adapter.get("availability"))
        return item


class ValidationPipeline:
    """Drops items that miss a required field."""

    REQUIRED = ("title", "price", "product_url", "category")

    def process_item(self, item):
        """Raise ``DropItem`` if any required field is empty."""
        adapter = ItemAdapter(item)
        missing = [name for name in self.REQUIRED if adapter.get(name) in (None, "")]
        if missing:
            raise DropItem(f"Missing {missing} in {adapter.get('product_url')}")
        return item


class DuplicatesPipeline:
    """Drops books already seen in this run (same product URL)."""

    def __init__(self) -> None:
        """Initialise the set of seen URLs."""
        self._seen: set[str] = set()

    def process_item(self, item):
        """Drop duplicates by ``product_url``."""
        url = ItemAdapter(item)["product_url"]
        if url in self._seen:
            raise DropItem(f"Duplicate book {url}")
        self._seen.add(url)
        return item


class SQLitePipeline:
    """Persists cleaned items through a ``BookRepository``."""

    def __init__(
        self,
        db_path: str,
        reset: bool = True,
        repository: BookRepository | None = None,
    ) -> None:
        """Build the pipeline; a repository can be injected (e.g. for tests)."""
        self.reset = reset
        self.repository = repository or SQLiteBookRepository(db_path)
        self.count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """Read DATABASE_PATH / DATABASE_RESET_ON_START from the settings."""
        return cls(
            crawler.settings.get("DATABASE_PATH"),
            crawler.settings.getbool("DATABASE_RESET_ON_START", True),
        )

    def open_spider(self):
        """Open the database when the spider starts."""
        self.repository.open(reset=self.reset)

    def process_item(self, item):
        """Save the item and pass it on to the feed exporters unchanged."""
        self.repository.save(ItemAdapter(item).asdict())
        self.count += 1
        return item

    def close_spider(self):
        """Commit and close; log how many rows were stored."""
        self.repository.close()
        logger.info("Stored %d books in the database", self.count)
