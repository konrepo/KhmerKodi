# ── Imports ─────────────────────────────────────────────────────
import time, random, requests
import xbmc, xbmcaddon, xbmcgui, xbmcplugin
from bs4 import BeautifulSoup

# ── Networking Session ──────────────────────────────────────────
_SESSION = requests.Session()

from resources.lib.handlers_common import USER_AGENT

# ── Negative Cache (prevents re-downloading bad URLs) ───────────
_NEG_CACHE, _NEG_TTL, _NEG_MAX = {}, 300, 512

def _neg_cached(url):
    exp = _NEG_CACHE.get(url)
    if exp and exp > time.time():
        xbmc.log(f"[{xbmcaddon.Addon().getAddonInfo('id')}] NEG-CACHE hit: {url}", xbmc.LOGDEBUG)
        return True
    _NEG_CACHE.pop(url, None) if exp else None
    return False

def _neg_save(url):
    if len(_NEG_CACHE) >= _NEG_MAX:
        _NEG_CACHE.pop(min(_NEG_CACHE, key=_NEG_CACHE.get), None)
    _NEG_CACHE[url] = time.time() + _NEG_TTL


# ── Main OpenURL for Khmer sites ───────────────────────────────────
def OpenURL(url, headers=None, user_agent=None, timeout=(5, 10), retries=2, delay=1.5, as_text=False):
    if _neg_cached(url):
        return "" if as_text else b""

    h = {"User-Agent": user_agent or USER_AGENT, "Accept-Encoding": "gzip, deflate", **(headers or {})}
    for a in range(1, retries + 1):
        try:
            r = _SESSION.get(url, headers=h, timeout=timeout)
            sc = r.status_code
            if sc in (404, 410):
                _neg_save(url)
                return "" if as_text else b""
            if sc == 429 and a < retries:
                time.sleep(1.0)
                continue
            if 400 <= sc < 500:
                return "" if as_text else b""
            r.raise_for_status()
            return r.text if as_text else r.content
        except requests.RequestException as e:
            xbmc.log(f"[{ADDON_ID}] Network error ({a}/{retries}) {url}: {e}", xbmc.LOGWARNING)
            if a == retries:
                return "" if as_text else b""
            time.sleep(delay + random.random() * 0.5)

def OpenSoup(url, return_html=False, **kwargs):
    html = OpenURL(url, as_text=True, **kwargs)
    if not html:
        raise Exception(f"Empty or failed response from URL: {url}")
    soup = BeautifulSoup(html, "html.parser")
    return (soup, html) if return_html else soup
