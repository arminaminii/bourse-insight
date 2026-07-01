"""
Codal Service — facade over CodalScraper.
Provides a clean API for views to use, with optional DB enrichment.
"""
import logging
from crawler.codal_scraper import CodalScraper

logger = logging.getLogger(__name__)


class CodalService:
    """High-level service for interacting with Codal.ir data."""

    def __init__(self, timeout=20, delay=0.5, max_retries=2, cache_ttl=7200):
        self.timeout = timeout
        self.delay = delay
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl

    def search(self, symbol, page=1, per_page=100, letter_type="6", force_refresh=False):
        """Search Codal.ir for a symbol (single page)."""
        s = CodalScraper(
            timeout=self.timeout,
            delay=self.delay,
            max_retries=self.max_retries,
            cache_ttl=self.cache_ttl,
        )
        r = s.search(
            symbol, page=page, length=per_page,
            letter_type=letter_type, force_refresh=force_refresh,
        )
        self._enrich(r)
        return r

    def search_all(self, symbol, letter_type="6", force_refresh=False, max_pages=50):
        """Fetch ALL pages for a symbol from Codal.ir."""
        s = CodalScraper(
            timeout=self.timeout,
            delay=self.delay,
            max_retries=self.max_retries,
            cache_ttl=self.cache_ttl,
        )
        r = s.search_all_pages(
            symbol, letter_type=letter_type,
            force_refresh=force_refresh, max_pages=max_pages,
        )
        self._enrich(r)
        return r

    def _enrich(self, result):
        """Try to enrich the result with company info from DB."""
        try:
            from companies.models import Company
            sym = result.get("symbol", "")
            if not sym:
                return
            try:
                c = Company.objects.select_related("sector").get(symbol=sym)
                result["company_info"] = {
                    "symbol": c.symbol,
                    "name": c.name,
                    "sector": c.sector.name if c.sector else "",
                }
            except Company.DoesNotExist:
                result["company_info"] = None
        except Exception:
            pass


_inst = None


def get_codal_service():
    """Get singleton CodalService instance."""
    global _inst
    if _inst is None:
        _inst = CodalService()
    return _inst