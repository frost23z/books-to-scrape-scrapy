import random


class RandomUserAgentMiddleware:
    """Picks a User-Agent per request from the ``USER_AGENTS`` setting."""

    def __init__(self, user_agents: list[str]) -> None:
        """Store the pool of User-Agent strings."""
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        """Build the middleware from settings; fall back to ``USER_AGENT``."""
        pool = crawler.settings.getlist("USER_AGENTS") or [crawler.settings.get("USER_AGENT")]
        return cls(pool)

    def process_request(self, request):
        """Set a random User-Agent header on the outgoing request."""
        request.headers["User-Agent"] = random.choice(self.user_agents)
