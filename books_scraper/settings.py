# Scrapy settings for books_scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import os

BOT_NAME = "books_scraper"

SPIDER_MODULES = ["books_scraper.spiders"]
NEWSPIDER_MODULE = "books_scraper.spiders"

ADDONS = {}

# Directories (override with env vars, e.g. in Docker)
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output")
DATABASE_PATH = os.environ.get("DATABASE_PATH", "output/books.db")
DATABASE_RESET_ON_START = os.environ.get("DATABASE_RESET_ON_START", "1") == "1"

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "books_scraper (+http://www.yourdomain.com)"

# User-Agent rotation (see middlewares.py)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BooksScraper/1.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) BooksScraper/1.0",
    "Mozilla/5.0 (X11; Linux x86_64) BooksScraper/1.0",
]

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Concurrency and throttling settings
# CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = float(os.environ.get("DOWNLOAD_DELAY", "1"))
DOWNLOAD_TIMEOUT = 15

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    "books_scraper.middlewares.BooksScraperSpiderMiddleware": 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    "books_scraper.middlewares.RandomUserAgentMiddleware": 400,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    "books_scraper.pipelines.CleaningPipeline": 100,
    "books_scraper.pipelines.ValidationPipeline": 200,
    "books_scraper.pipelines.DuplicatesPipeline": 300,
    "books_scraper.pipelines.SQLitePipeline": 400,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

RETRY_ENABLED = True
RETRY_TIMES = 3
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = "httpcache"
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"


# Feed exports (JSON, CSV, XML), overwritten each run so they match the DB
_FIELDS = [
    "title",
    "price",
    "availability",
    "product_url",
    "image_url",
    "category",
]
FEEDS = {
    f"{OUTPUT_DIR}/books.json": {
        "format": "json",
        "indent": 4,
        "encoding": "utf8",
        "fields": _FIELDS,
        "overwrite": True,
    },
    f"{OUTPUT_DIR}/books.csv": {
        "format": "csv",
        "encoding": "utf8",
        "fields": _FIELDS,
        "overwrite": True,
    },
    f"{OUTPUT_DIR}/books.xml": {
        "format": "xml",
        "encoding": "utf8",
        "indent": 2,
        "item_export_kwargs": {"item_element": "book", "root_element": "books"},
        "fields": _FIELDS,
        "overwrite": True,
    },
}
