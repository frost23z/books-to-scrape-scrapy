from urllib.parse import urlparse

import scrapy

from books_scraper.items import BookItem
from books_scraper.services.parsers import (
    CategoryLink,
    CategoryParser,
    CategoryProbe,
    ListingParser,
    ProductParser,
)
from books_scraper.services.selection import RandomSelector


class BooksSpider(scrapy.Spider):
    """Crawl categories, select random books, and scrape their details."""

    name = "books"
    DEFAULT_START_URL = "https://books.toscrape.com/index.html"

    def __init__(
        self,
        start_url: str | None = None,
        min_categories: int = 5,
        max_categories: int = 10,
        books_per_category: int = 5,
        seed: int | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Configure the spider and its collaborators (dependency injection)."""
        super().__init__(*args, **kwargs)
        self.start_url = start_url or self.DEFAULT_START_URL
        self.start_urls = [self.start_url]
        self.allowed_domains = [urlparse(self.start_url).hostname]
        self.min_categories = int(min_categories)
        self.max_categories = int(max_categories)
        self.books_per_category = int(books_per_category)
        self.selector = RandomSelector(int(seed) if seed is not None else None)
        self.category_parser = CategoryParser()
        self.listing_parser = ListingParser()
        self.product_parser = ProductParser()
        self._probes: dict[str, CategoryProbe] = {}
        self._probes_expected = 0
        self._probes_failed = 0

    def parse(self, response):
        """Homepage: discover all categories and probe each one."""
        categories = self.category_parser.parse(response)
        if not categories:
            self.logger.error("No categories found on %s - layout changed?", response.url)
            return
        self._probes_expected = len(categories)
        for category in categories:
            yield scrapy.Request(
                category.url,
                callback=self.parse_probe,
                errback=self.probe_failed,
                cb_kwargs={"category": category},
            )

    def parse_probe(self, response, category: CategoryLink):
        """Record what page 1 of a category looks like; select when all are in."""
        self._probes[category.url] = CategoryProbe(
            category=category,
            book_urls=self.listing_parser.book_urls(response),
            next_url=self.listing_parser.next_page_url(response),
        )
        yield from self._select_when_probed()

    def probe_failed(self, failure):
        """A probe failed: skip that category but keep the crawl going."""
        self.logger.error("Category probe failed: %s", failure.request.url)
        self._probes_failed += 1
        yield from self._select_when_probed()

    def _select_when_probed(self):
        """Once every probe has reported, pick the categories to crawl."""
        if len(self._probes) + self._probes_failed < self._probes_expected:
            return
        # Sorted so a given ``seed`` gives the same result whatever order the
        # responses arrived in.
        eligible = sorted(
            (p for p in self._probes.values() if p.has_at_least(self.books_per_category)),
            key=lambda p: p.category.url,
        )
        self.logger.info(
            "%d/%d categories have at least %d books",
            len(eligible),
            self._probes_expected,
            self.books_per_category,
        )
        chosen = self.selector.pick_between(eligible, self.min_categories, self.max_categories)
        self.logger.info(
            "Selected %d categories: %s", len(chosen), [p.category.name for p in chosen]
        )
        for probe in chosen:
            if probe.next_url:
                yield self._listing_request(probe.next_url, probe.category.name, probe.book_urls)
            else:
                yield from self._sample_books(probe.category.name, probe.book_urls)

    def parse_category(self, response, category_name: str, book_urls: list[str]):
        """Collect book URLs across the remaining listing pages."""
        book_urls = book_urls + self.listing_parser.book_urls(response)
        next_url = self.listing_parser.next_page_url(response)
        if next_url:
            yield self._listing_request(next_url, category_name, book_urls)
        else:
            yield from self._sample_books(category_name, book_urls)

    def _listing_request(self, url: str, category_name: str, book_urls: list[str]):
        """Build the request for the next listing page of a category."""
        return scrapy.Request(
            url,
            callback=self.parse_category,
            errback=self.on_error,
            cb_kwargs={"category_name": category_name, "book_urls": book_urls},
        )

    def _sample_books(self, category_name: str, book_urls: list[str]):
        """Pick the random books of one category and request their pages."""
        selected = self.selector.pick(book_urls, self.books_per_category)
        self.logger.info(
            "Category '%s': %d books found, %d selected",
            category_name,
            len(book_urls),
            len(selected),
        )
        for url in selected:
            yield scrapy.Request(
                url,
                callback=self.parse_book,
                errback=self.on_error,
                cb_kwargs={"category_name": category_name},
            )

    def parse_book(self, response, category_name: str):
        """Product page: yield a raw BookItem (cleaning happens in pipelines)."""
        data = self.product_parser.parse(response)
        data["category"] = category_name or data.get("category")
        yield BookItem(**data)

    def on_error(self, failure):
        """Log failed requests without stopping the crawl."""
        self.logger.error("Request failed: %s (%r)", failure.request.url, failure.value)
