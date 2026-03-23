# ── Imports ─────────────────────────────────────────────────────
import time, requests
from bs4 import BeautifulSoup
import xbmc, xbmcaddon

ADDON_ID = xbmcaddon.Addon().getAddonInfo("id")

# ── Logging Helper ──────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

# ── Base URL (for referer header consistency) ───────────────────
BASE_URL = "https://flixhq.to/"

# ── User Agent ─────────────────────────────────────────────────
USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"

# ── Request Headers (default lightweight) ──────────────────────
HEADERS = {
    "User-Agent": USER_AGENT,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL,
}

def OpenURL(url, timeout=10, retries=3, delay=2, headers=None, as_text=False):
    final_headers = {'User-Agent': USER_AGENT}
    if headers:
        final_headers.update(headers)
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=final_headers, timeout=timeout)
            response.raise_for_status()
            return response.text if as_text else response.content
        except Exception as e:
            if attempt >= retries:
                raise e
            time.sleep(delay)
            
headers = {
  'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
  'sec-ch-ua-platform': "\"Windows\"",
  'x-requested-with': "XMLHttpRequest",
  'sec-ch-ua': "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
  'sec-ch-ua-mobile': "?0",
  'sec-fetch-site': "same-origin",
  'sec-fetch-mode': "cors",
  'sec-fetch-dest': "empty",
  'referer': BASE_URL,
  'accept-language': "en-US,en;q=0.9,pt;q=0.8",
  'priority': "u=1, i"
  }
  
def URL(url):
    response = requests.get(url,headers=headers).text
    return response

def OpenSoup(url, return_html=False, **kwargs):
    html = OpenURL(url, as_text=True, **kwargs)
    if not html:
        raise Exception(f"Empty or failed response from URL: {url}")
    soup = BeautifulSoup(html, "html.parser")
    return (soup, html) if return_html else soup
