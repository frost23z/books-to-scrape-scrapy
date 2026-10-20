import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CategoryLink:
    """A discovered category: its display name and absolute URL."""

    name: str
    url: str


@dataclass
class CategoryProbe:
    """A discovered category listing page, with its book URLs and next-page URL."""

    category: CategoryLink
    book_urls: list[str] = field(default_factory=list)
    next_url: str | None = None

    def has_at_least(self, count: int) -> bool:
        """Return whether the category holds at least ``count`` books."""
        return len(self.book_urls) >= count or self.next_url is not None


class CategoryParser:
    """Discovers categories from the homepage sidebar."""

    LINK_SELECTOR = "div.side_categories ul li ul li a"

    def parse(self, response) -> list[CategoryLink]:
        """Return every category found on the page, with absolute URLs."""
        categories = []
        for link in response.css(self.LINK_SELECTOR):
            name = " ".join(link.css("::text").get(default="").split())
            href = link.attrib.get("href")
            if name and href:
                categories.append(CategoryLink(name=name, url=response.urljoin(href)))
        logger.info("Discovered %d categories on %s", len(categories), response.url)
        return categories


class ListingParser:
    """Parses a category listing page (book links + pagination)."""

    BOOK_LINK_SELECTOR = "article.product_pod h3 a::attr(href)"
    NEXT_PAGE_SELECTOR = "li.next a::attr(href)"

    def book_urls(self, response) -> list[str]:
        """Return absolute product URLs listed on this page."""
        hrefs = response.css(self.BOOK_LINK_SELECTOR).getall()
        return [response.urljoin(href) for href in hrefs]

    def next_page_url(self, response) -> str | None:
        """Return the absolute next-page URL, or ``None`` on the last page."""
        href = response.css(self.NEXT_PAGE_SELECTOR).get()
        return response.urljoin(href) if href else None


class ProductParser:
    """Extracts the raw (uncleaned) book fields from a product detail page."""

    def parse(self, response) -> dict:
        """Return raw field values; cleaning is the pipelines' job."""
        return {
            "title": response.css("div.product_main h1::text").get(),
            "price": response.css("p.price_color::text").get(),
            "availability": " ".join(response.css("p.availability ::text").getall()),
            "product_url": response.url,
            "image_url": self._image_url(response),
            "category": response.css("ul.breadcrumb li:nth-child(3) a::text").get(),
        }

    @staticmethod
    def _image_url(response) -> str | None:
        """Return the absolute cover-image URL, if present."""
        src = (
            response.css("div.item.active img::attr(src)").get()
            or response.css("#product_gallery img::attr(src)").get()
        )
        return response.urljoin(src) if src else None
