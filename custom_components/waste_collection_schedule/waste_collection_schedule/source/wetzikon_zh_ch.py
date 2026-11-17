import re
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from waste_collection_schedule import Collection, Icons
from waste_collection_schedule.exceptions import SourceArgumentNotFoundWithSuggestions
from waste_collection_schedule.service.ICS import ICS

TITLE = "Wetzikon ZH"
DESCRIPTION = "Source for waste collection in Wetzikon ZH, Switzerland."
URL = "https://www.wetzikon.ch/"
COUNTRY = "ch"
SOURCE_CODEOWNERS = ["@danielLutziger"]

TEST_CASES = {
    "Kreis 1": {"region": 1},
    "Kreis 2": {"region": 2},
    "Kreis 3": {"region": 3},
    "Kreis 4": {"region": 4},
}

ICON_MAP = {
    "Abfall": Icons.GENERAL_WASTE,
    "Biogene Abfälle": Icons.ORGANIC,
    "Karton": Icons.PAPER,
    "Papiersammlung": Icons.PAPER,
    "Häckseldienst": Icons.GARDEN,
    "Grubengut": Icons.BULKY,
    "Metall": Icons.METAL,
    "Sonderabfall": Icons.HAZARDOUS,
    "Christbäume": Icons.CHRISTMAS_TREE,
}

PARAM_TRANSLATIONS = {
    "en": {"region": "Region (Kreis)"},
    "de": {"region": "Kreis"},
    "fr": {"region": "Cercle (Kreis)"},
    "it": {"region": "Circolo (Kreis)"},
}

PARAM_DESCRIPTIONS = {
    "en": {"region": "Collection region (Kreis) of Wetzikon: 1, 2, 3 or 4"},
    "de": {"region": "Entsorgungskreis von Wetzikon: 1, 2, 3 oder 4"},
    "fr": {"region": "Cercle de collecte de Wetzikon : 1, 2, 3 ou 4"},
    "it": {"region": "Circolo di raccolta di Wetzikon: 1, 2, 3 o 4"},
}

BASE_URL = "https://m.wetzikon.ch"
# Page id of the "Entsorgungskalender" page. Every calendar page is reachable from here
CALENDAR_HOME_ID = "7215088"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; waste_collection_schedule)"}
TIMEOUT = 30


def _page_links(html: str, page_url: str) -> dict[str, str]:
    """Return {link title: absolute url} for all list entries on a page."""
    soup = BeautifulSoup(html, "html.parser")
    links: dict[str, str] = {}
    for row in soup.select("div.elementLinkRow a[href]"):
        title = row.select_one("div.title")
        if title is None:
            continue
        links[title.get_text(strip=True)] = urljoin(page_url, row["href"])
    return links


class Source:
    def __init__(self, region: int):
        self._region = int(region)
        self._ics = ICS()

    def _get(self, url: str) -> requests.Response:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r

    def _ics_url(self, page_url: str) -> str | None:
        """Extract the ical link from a single waste type page."""
        match = re.search(
            r"https://m\.wetzikon\.ch/appl/ical\.php\?[^'\"<>\s]+",
            self._get(page_url).text,
        )
        return match.group(0).replace("&amp;", "&") if match else None

    def fetch(self) -> list[Collection]:
        home_url = f"{BASE_URL}/index.php?apid={CALENDAR_HOME_ID}"
        regions = _page_links(self._get(home_url).text, home_url)
        region_title = f"Kreis {self._region}"

        if region_title not in regions:
            raise SourceArgumentNotFoundWithSuggestions(
                "region",
                self._region,
                sorted(
                    int(t.split()[1]) for t in regions if re.fullmatch(r"Kreis \d+", t)
                ),
            )

        region_url = regions[region_title]
        waste_types = _page_links(self._get(region_url).text, region_url)

        seen: set[str] = set()
        entries: list[Collection] = []
        for page_url in waste_types.values():
            # only follow pages belonging to the calendar (not e.g. collection points)
            if parse_qs(urlparse(page_url).query).get("apparentid") != [
                parse_qs(urlparse(region_url).query)["apid"][0]
            ]:
                continue
            ics_url = self._ics_url(page_url)
            if not ics_url or ics_url in seen:
                continue
            seen.add(ics_url)
            for date, summary in self._ics.convert(self._get(ics_url).text):
                # "Kreis 2, Abfall" -> "Abfall"
                waste_type = summary.split(",", 1)[-1].strip()
                entries.append(
                    Collection(
                        date=date,
                        t=waste_type,
                        icon=ICON_MAP.get(waste_type),
                    )
                )
        return entries
