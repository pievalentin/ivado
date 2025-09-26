import requests
from typing import List, Dict

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
MUSEUMS_LIST_PAGE = "List of most-visited museums"


def fetch_museum_table() -> List[Dict]:
    """
    Fetch the table of most visited museums from Wikipedia and return as a list of dicts.
    Follows redirects if necessary.
    """
    def get_wikitext(page_title):
        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "wikitext"
        }
        resp = requests.get(WIKIPEDIA_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data["parse"]["wikitext"]["*"]

    wikitext = get_wikitext(MUSEUMS_LIST_PAGE)
    # Check for redirect in wikitext
    if wikitext.strip().startswith("#REDIRECT"):
        import re
        match = re.search(r'\[\[(.*?)\]\]', wikitext)
        if match:
            redirect_title = match.group(1)
            wikitext = get_wikitext(redirect_title)
    print(wikitext[:2000])  # Print first 2000 characters for inspection
    # TODO: Parse the wikitext table into structured data (use mwparserfromhell or regex)
    return []

if __name__ == "__main__":
    museums = fetch_museum_table()
    print(museums)
