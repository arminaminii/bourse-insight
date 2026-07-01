"""
Codal.ir scraper — uses system curl for TLS fingerprint bypass.
Based on: https://github.com/arminaminii/financial-terminal-codal

Endpoint: GET https://search.codal.ir/api/search/v2/q
Returns: XML (NOT JSON)
No authentication needed.
"""
import re
import subprocess
import time
import math
import logging
from typing import List, Dict, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)

CODAL_BASE = "https://search.codal.ir/api/search/v2/q"

HEADERS = [
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept: application/xml, text/xml, */*",
    "Accept-Language: fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer: https://search.codal.ir/",
    "Origin: https://search.codal.ir",
    "X-Requested-With: XMLHttpRequest",
    "Connection: keep-alive",
]


def normalize(text):
    """Remove ZWNJ and extra spaces for fuzzy matching."""
    if not text:
        return ""
    return text.replace("\u200c", "").replace(" ", "").strip()


def classify_report(title):
    """Classify a report by its title into types and categories."""
    t = title or ""
    r = {
        "report_type": "سایر",
        "period_type": "سایر",
        "is_audited": False,
        "is_consolidated": False,
    }
    if "حسابرسي شده" in t or "حسابرسی" in t:
        r["is_audited"] = True
    if "تلفیقی" in t:
        r["is_consolidated"] = True

    # Period type
    if "میانی" in t:
        r["period_type"] = "میانی"
    elif "سالانه" in t or "پایان دوره" in t:
        r["period_type"] = "سالانه"

    # Report type classification
    if "صورت مالی" in t or "صورت‌های مالی" in t:
        r["report_type"] = "صورت‌های مالی"
    elif "تفسیری" in t:
        r["report_type"] = "گزارش تفسیری"
    elif "سود و زیان" in t:
        r["report_type"] = "سود و زیان"
    elif "ترازنامه" in t:
        r["report_type"] = "ترازنامه"
    elif "جریان نقد" in t or "جریان وجوه نقد" in t:
        r["report_type"] = "جریان وجوه نقد"
    elif "تغییرات" in t and "صاحبان" in t:
        r["report_type"] = "تغییرات حقوق صاحبان"
    elif "شفافیت" in t:
        r["report_type"] = "گزارش شفافیت"
    elif "تغییرات سرمایه" in t or "افزایش سرمایه" in t:
        r["report_type"] = "تغییرات سرمایه"
    elif "اطلاعیه مهم" in t:
        r["report_type"] = "اطلاعیه مهم"
    elif "دعوت مجمع" in t:
        r["report_type"] = "آگهی دعوت مجمع"
    elif "هیئت مدیره" in t:
        r["report_type"] = "گزارش هیئت مدیره"
    elif "بازنگری" in t or "اصلاحیه" in t:
        r["report_type"] = "بازنگری/اصلاحیه"
    elif "پیش‌بینی" in t:
        r["report_type"] = "پیش‌بینی سودآوری"
    elif "ماهانه" in t:
        r["report_type"] = "گزارش فعالیت ماهانه"

    return r


def parse_codal_xml(xml_text):
    """Parse Codal.ir XML response into list of letter dicts."""
    results = []
    blocks = re.split(r"<Letter\b", xml_text)
    for block in blocks[1:]:
        letter = {}

        def ext(tag):
            m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", block, re.IGNORECASE)
            return m.group(1).strip() if m else ""

        letter["title"] = ext("Title")
        letter["url"] = ext("Url")
        letter["excel_url"] = ext("ExcelUrl")
        letter["letter_code"] = ext("LetterCode")
        letter["tracing_no"] = ext("TracingNo")
        letter["publish_datetime"] = ext("PublishDateTime")
        letter["symbol"] = ext("Symbol")
        letter["company_name"] = ext("CompanyName")
        letter["period"] = ext("Period")
        letter["fiscal_year"] = ext("FiscalYear")
        letter["auditor"] = ext("Auditor")

        # Classify the report
        cls = classify_report(letter["title"])
        letter.update(cls)

        # Fix relative URLs
        if letter["url"] and not letter["url"].startswith("http"):
            letter["url"] = "https://codal.ir" + letter["url"]
        if letter["excel_url"] and not letter["excel_url"].startswith("http"):
            letter["excel_url"] = "https://codal.ir" + letter["excel_url"]

        # Extract Persian date
        dm = re.match(r"(\d{4}/\d{2}/\d{2})", letter["publish_datetime"])
        letter["date_persian"] = dm.group(1) if dm else letter["publish_datetime"]

        results.append(letter)
    return results


def extract_total_count(xml_text):
    """Extract total count from Codal XML response."""
    for tag in ["TotalCount", "Total", "Count", "totalcount"]:
        m = re.search(rf"<{tag}>([\s\S]*?)</{tag}>", xml_text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).strip())
            except (ValueError, TypeError):
                continue
    return 0


def codal_api_url(symbol, page=1, length=100, letter_type="6", category="1"):
    """Build the full Codal.ir API URL with all required parameters."""
    e = quote(symbol)
    return (
        f"{CODAL_BASE}?Symbol={e}&LetterType={letter_type}&Category={category}"
        f"&Audited=true&NotAudited=true&search=true"
        f"&PageNumber={page}&Length={length}"
        f"&Mains=true&Childs=true&Publisher=true"
        f"&Consolidatable=true&IsNotAudited=true"
        f"&AuditorRef=-1&CompanyState=0&CompanyType=-1"
    )


def _curl_get(url, timeout=20):
    """Make HTTP GET using system curl command for TLS fingerprint bypass."""
    cmd = [
        "curl", "-s", "-S",
        "--max-time", str(timeout),
        "--connect-timeout", "10",
        "-L",  # follow redirects
    ]
    for h in HEADERS:
        cmd += ["-H", h]
    cmd.append(url)

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        if r.returncode != 0:
            logger.error("curl failed (code %d): %s", r.returncode, (r.stderr or '')[:500])
            return {
                "ok": False,
                "text": r.stderr or "",
                "error": f"curl exit {r.returncode}: {(r.stderr or '')[:200]}",
                "method": "curl",
            }
        if not r.stdout or len(r.stdout) < 10:
            logger.warning("curl returned empty/short response (%d bytes)", len(r.stdout) if r.stdout else 0)
            return {
                "ok": False,
                "text": r.stdout or "",
                "error": "empty response from Codal",
                "method": "curl",
            }
        return {"ok": True, "text": r.stdout, "error": None, "method": "curl"}
    except FileNotFoundError:
        logger.error("curl not found, falling back to requests")
        return {"ok": False, "text": "", "error": "curl_not_found", "method": "none"}
    except subprocess.TimeoutExpired:
        logger.error("curl timed out after %ds", timeout)
        return {"ok": False, "text": "", "error": f"timeout after {timeout}s", "method": "curl"}
    except Exception as e:
        logger.error("curl exception: %s", e)
        return {"ok": False, "text": "", "error": str(e), "method": "curl"}


def _requests_fallback(url, timeout=20):
    """Fallback HTTP GET using Python requests library."""
    import requests
    headers = {h.split(": ", 1)[0]: h.split(": ", 1)[1] for h in HEADERS}
    try:
        r = requests.get(url, headers=headers, timeout=timeout, verify=False)
        ok = r.status_code == 200
        if not ok:
            logger.error("requests returned HTTP %d", r.status_code)
        return {
            "ok": ok,
            "text": r.text,
            "error": f"HTTP {r.status_code}" if not ok else None,
            "method": "requests",
        }
    except requests.Timeout:
        return {"ok": False, "text": "", "error": "requests timeout", "method": "requests"}
    except Exception as e:
        return {"ok": False, "text": "", "error": f"requests: {str(e)}", "method": "requests"}


def _http_get(url, timeout=20):
    """Try curl first, fall back to requests if curl fails."""
    r = _curl_get(url, timeout)
    if r["ok"] and r["text"]:
        return r
    if r.get("error") == "curl_not_found":
        return _requests_fallback(url, timeout)
    # Try requests as last resort
    logger.warning("curl failed (%s), trying requests fallback", r.get("error"))
    return _requests_fallback(url, timeout)


class CodalScraper:
    """
    Main scraper class for Codal.ir.
    Uses system curl for TLS fingerprint bypass with in-memory cache (2h TTL).
    """

    def __init__(self, timeout=20, delay=0.5, max_retries=2, cache_ttl=7200):
        self.timeout = timeout
        self.delay = delay
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl
        self._cache = {}

    def search(self, symbol, page=1, length=100, letter_type="6", force_refresh=False):
        """Search Codal.ir for a symbol (single page)."""
        import time as _t
        start = _t.time()
        norm = normalize(symbol)
        key = f"{norm}_lt{letter_type}_p{page}_l{length}"

        # Cache check
        if not force_refresh and key in self._cache:
            c = self._cache[key]
            if (_t.time() - c["ts"]) < self.cache_ttl:
                r = dict(c["data"])
                r["cached"] = True
                r["fetch_time_ms"] = 0
                logger.info("Cache hit for %s", symbol)
                return r

        url = codal_api_url(symbol, page=page, length=length, letter_type=letter_type)
        result = {
            "letters": [],
            "total": 0,
            "page": page,
            "pages": 1,
            "symbol": symbol,
            "cached": False,
            "error": None,
            "fetch_time_ms": 0,
        }

        # Fetch with retry
        http = None
        for attempt in range(self.max_retries + 1):
            logger.info(
                "Fetching %s (attempt %d/%d, method: %s)",
                symbol, attempt + 1, self.max_retries + 1, "curl"
            )
            http = _http_get(url, timeout=self.timeout)
            if http["ok"]:
                logger.info("Success! Got %d bytes from Codal", len(http["text"]))
                break
            if attempt < self.max_retries:
                wait = self.delay * (attempt + 1)
                logger.warning(
                    "Attempt %d failed (%s), retrying in %.1fs...",
                    attempt + 1, http.get("error"), wait,
                )
                time.sleep(wait)

        if not http or not http["ok"]:
            err = http["error"] if http else "unknown"
            logger.error("All attempts failed for %s: %s", symbol, err)
            result["error"] = err
            result["fetch_time_ms"] = int((_t.time() - start) * 1000)
            self._cache[key] = {"data": result, "ts": _t.time()}
            return result

        xml = http["text"]
        letters = parse_codal_xml(xml)
        total = extract_total_count(xml)

        # Filter by symbol match
        norm_sym = normalize(symbol)
        filtered = [
            l for l in letters
            if norm_sym in normalize(l.get("symbol", ""))
            or norm_sym in normalize(l.get("company_name", ""))
            or normalize(l.get("symbol", "")) == norm_sym
        ]

        pages = max(1, math.ceil(total / length)) if total > 0 else 1
        result["letters"] = filtered
        result["total"] = total
        result["pages"] = pages
        result["fetch_time_ms"] = int((_t.time() - start) * 1000)

        self._cache[key] = {"data": result, "ts": _t.time()}
        logger.info(
            "Codal search for '%s': %d letters, total=%d, %.0fms",
            symbol, len(filtered), total, result["fetch_time_ms"],
        )
        return result

    def search_all_pages(self, symbol, letter_type="6", force_refresh=False, max_pages=50):
        """Fetch ALL pages for a symbol from Codal.ir."""
        import time as _t
        start = _t.time()
        norm = normalize(symbol)
        key = f"{norm}_lt{letter_type}_all"

        if not force_refresh and key in self._cache:
            c = self._cache[key]
            if (_t.time() - c["ts"]) < self.cache_ttl:
                r = dict(c["data"])
                r["cached"] = True
                r["fetch_time_ms"] = 0
                return r

        result = {
            "letters": [],
            "total": 0,
            "pages": 0,
            "symbol": symbol,
            "cached": False,
            "error": None,
            "fetch_time_ms": 0,
        }

        # Page 1
        url = codal_api_url(symbol, page=1, length=100, letter_type=letter_type)
        http = None
        for attempt in range(self.max_retries + 1):
            http = _http_get(url, timeout=self.timeout)
            if http["ok"]:
                break
            if attempt < self.max_retries:
                time.sleep(self.delay * (attempt + 1))

        if not http or not http["ok"]:
            result["error"] = http["error"] if http else "unknown"
            result["fetch_time_ms"] = int((_t.time() - start) * 1000)
            return result

        letters = parse_codal_xml(http["text"])
        total = extract_total_count(http["text"])
        norm_sym = normalize(symbol)
        all_letters = [
            l for l in letters
            if norm_sym in normalize(l.get("symbol", ""))
            or norm_sym in normalize(l.get("company_name", ""))
            or normalize(l.get("symbol", "")) == norm_sym
        ]
        pages = max(1, math.ceil(total / 100)) if total > 0 else 1

        # Remaining pages
        if total > 100 and max_pages > 1:
            for pg in range(2, min(pages + 1, max_pages + 1)):
                time.sleep(self.delay)
                purl = codal_api_url(symbol, page=pg, length=100, letter_type=letter_type)
                ph = _http_get(purl, timeout=self.timeout)
                if not ph or not ph["ok"]:
                    break
                pl = parse_codal_xml(ph["text"])
                pf = [
                    l for l in pl
                    if norm_sym in normalize(l.get("symbol", ""))
                    or norm_sym in normalize(l.get("company_name", ""))
                    or normalize(l.get("symbol", "")) == norm_sym
                ]
                if not pf:
                    break
                all_letters.extend(pf)
                logger.info("Page %d/%d: got %d letters", pg, pages, len(pf))

        result["letters"] = all_letters
        result["total"] = len(all_letters)
        result["pages"] = pages
        result["fetch_time_ms"] = int((_t.time() - start) * 1000)
        self._cache[key] = {"data": result, "ts": _t.time()}
        return result


_inst = None


def get_scraper():
    """Get singleton CodalScraper instance."""
    global _inst
    if _inst is None:
        _inst = CodalScraper()
    return _inst