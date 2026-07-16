import re
import time
from urllib.parse import quote

import requests

from exceptions import (
    OxfordBlockedError,
    OxfordNetworkError,
    OxfordStructureError,
    WordNotFoundError,
)
from models import WordEntry
from parser import parse_entry


BASE_URL = "https://www.oxfordlearnersdictionaries.com/definition/english/"
WORD_PATTERN = re.compile(r"^[A-Za-z]+(?:[-'][A-Za-z]+)*$")
BLOCK_MARKERS = (
    "enable javascript and cookies to continue",
    "cf-chl-",
    "captcha",
    "access denied",
)


def normalize_word(word: str) -> str:
    normalized = word.strip().lower()
    if not WORD_PATTERN.fullmatch(normalized):
        raise ValueError("Enter one English word (letters, apostrophes, or hyphens only).")
    return normalized


class OxfordClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (5.0, 15.0),
        max_attempts: int = 3,
        sleep=time.sleep,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.sleep = sleep
        self.session.headers.update(
            {
                "User-Agent": "Oxford-to-Notion/1.4.3 (+low-frequency personal use)",
                "Accept-Language": "en-GB,en;q=0.9",
            }
        )

    def lookup(self, word: str) -> WordEntry:
        normalized = normalize_word(word)
        url = BASE_URL + quote(normalized, safe="-'")

        for attempt in range(self.max_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt + 1 < self.max_attempts:
                    self.sleep(0.5 * (2**attempt))
                    continue
                raise OxfordNetworkError("Oxford request failed after retrying.") from exc

            if response.status_code == 404:
                raise WordNotFoundError(f"Oxford has no entry for '{normalized}'.")
            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempt + 1 < self.max_attempts:
                    self.sleep(0.5 * (2**attempt))
                    continue
                raise OxfordNetworkError(f"Oxford returned HTTP {response.status_code} after retrying.")
            if response.status_code in (401, 403):
                raise OxfordBlockedError("Oxford refused the request; access may require a browser.")
            if not 200 <= response.status_code < 300:
                raise OxfordNetworkError(f"Oxford returned unexpected HTTP {response.status_code}.")

            lowered = response.text.lower()
            if any(marker in lowered for marker in BLOCK_MARKERS):
                raise OxfordBlockedError("Oxford returned an access challenge instead of a dictionary entry.")
            try:
                return parse_entry(response.text, response.url or url)
            except OxfordStructureError:
                if "did you mean" in lowered or "no exact matches" in lowered:
                    raise WordNotFoundError(f"Oxford has no entry for '{normalized}'.")
                raise

        raise OxfordNetworkError("Oxford request failed.")
