import re
import sys
import requests
import json
import xbmc
import xbmcplugin
import xbmcgui

from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse, urlunparse, quote, unquote

from resources.lib.handlers_khmer import (
    OpenSoup as OpenSoup_KH,
    OpenURL as OpenURL_KH,
)

ADDON_ID = "plugin.video.movie"
PLUGIN_HANDLE = int(sys.argv[1])

XVIDEOS = "https://www.xvideos.com/"


# ────────────────────────────────────────────────
# LOGGING
# ────────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] [xvideos] {msg}", level)


# ────────────────────────────────────────────────
# INDEX / SEARCH
# ────────────────────────────────────────────────
def INDEX_XVIDEOS(url):
    _render_xvideos_listing(
        url=url,
        label_suffix=None,
        include_pagination=True,
        end_directory=True
    )


def SINDEX_XVIDEOS(url, end_directory=True):
    _render_xvideos_listing(
        url=url,
        label_suffix=" [COLOR green]xVideos[/COLOR]",
        include_pagination=False,
        end_directory=end_directory
    )


def _render_xvideos_listing(url, label_suffix=None, include_pagination=True, end_directory=True):
    try:
        soup, _ = OpenSoup_KH(url, return_html=True)
    except Exception as e:
        log(f"Listing fetch failed: {url} :: {e}", xbmc.LOGERROR)
        if end_directory:
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if not soup:
        if end_directory:
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    for post in soup.select("div.thumb-block"):
        try:
            title_link = post.select_one("p.title a[href]")
            if not title_link:
                continue

            href = (title_link.get("href") or "").strip()
            title = clean_title(title_link.get("title") or title_link.get_text(" ", strip=True))

            if not href or not title:
                continue

            img = post.select_one("img")
            thumb = ""
            if img:
                thumb = (
                    img.get("data-sfwthumb")
                    or img.get("data-src")
                    or img.get("src")
                    or ""
                ).strip()

            addDir(
                f"{title}{label_suffix or ''}",
                urljoin(XVIDEOS, href),
                "episode_xvideos",
                clean_image_url(thumb)
            )

        except Exception as e:
            log(f"Failed parsing item: {e}", xbmc.LOGWARNING)

    if include_pagination:
        next_page = _find_next_page(soup)
        if next_page:
            addDir("NEXT PAGE", next_page, "index_xvideos", "")

    if end_directory:
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def _find_next_page(soup):
    next_tag = (
        soup.select_one("div.pagination a.next-page[href]")
        or soup.select_one(".pagination a[rel='next'][href]")
    )
    if not next_tag:
        return ""

    href = (next_tag.get("href") or "").strip()
    if not href or href == "#":
        return ""

    return urljoin(XVIDEOS, href)


# ────────────────────────────────────────────────
# EPISODE
# ────────────────────────────────────────────────
def EPISODE_XVIDEOS(url, v_image=""):
    try:
        html = OpenURL_KH(url, as_text=True)
    except Exception as e:
        log(f"Post fetch failed: {url} :: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Could not load page.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if not html:
        xbmcgui.Dialog().ok("Error", "Could not load page.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("h2.page-title") or soup.select_one("title")
    page_title = clean_title(title_tag.get_text(" ", strip=True) if title_tag else "Video")

    if not v_image:
        og = soup.select_one("meta[property='og:image']")
        if og:
            v_image = og.get("content", "")

    v_image = clean_image_url(v_image)

    best_url, quality_label = extract_best_video_source(html)

    if not best_url:
        xbmcgui.Dialog().ok("No Sources", "No playable video found.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    label = f"[COLOR lime]PLAY[/COLOR] [COLOR gold]{quality_label}[/COLOR]"

    base_url = best_url.split("?", 1)[0].lower()
    if ".m3u8" in best_url or base_url.endswith((".mp4", ".mov", ".mkv", ".webm")):
        addLink(label, best_url, "play_direct", v_image)
    else:
        addLink(label, best_url, "video_hosting", v_image)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ────────────────────────────────────────────────
# SOURCE EXTRACTION
# ────────────────────────────────────────────────
def get_hls_resolution(m3u8_url):
    try:
        r = requests.get(
            m3u8_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": XVIDEOS,
            },
            timeout=10
        )
        if not r.ok:
            return "HLS"

        heights = []

        for line in r.text.splitlines():
            if "RESOLUTION=" in line:
                m = re.search(r"RESOLUTION=\d+x(\d+)", line)
                if m:
                    heights.append(int(m.group(1)))

        if heights:
            return f"{max(heights)}p"

    except Exception as e:
        log(f"HLS resolution detect failed: {e}", xbmc.LOGWARNING)

    return "HLS"

def extract_best_video_source(html):
    hls = ""
    high = ""
    low = ""

    m = re.search(r'html5player\.setVideoHLS\([\'"]([^\'"]+)[\'"]\)', html, re.I)
    if m:
        hls = decode_escaped_url(m.group(1))

    m = re.search(r'html5player\.setVideoUrlHigh\([\'"]([^\'"]+)[\'"]\)', html, re.I)
    if m:
        high = decode_escaped_url(m.group(1))

    m = re.search(r'html5player\.setVideoUrlLow\([\'"]([^\'"]+)[\'"]\)', html, re.I)
    if m:
        low = decode_escaped_url(m.group(1))

    if hls:
        res = get_hls_resolution(hls)
        return hls, res
    if high:
        return high, "HD"
    if low:
        return low, "SD"

    for block in re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', html, re.I):
        try:
            data = json.loads(block)
            src = decode_escaped_url(data.get("contentUrl", ""))
            if src:
                return src, "SD"
        except Exception:
            pass

    return "", ""


# ────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────
def clean_title(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def decode_escaped_url(url=""):
    return (url or "").replace("\\u0026", "&").replace("\\/", "/").replace("&amp;", "&").strip()


def clean_image_url(img_url):
    if not img_url:
        return ""

    img_url = img_url.strip().replace("&amp;", "&")
    parsed = urlparse(img_url)
    safe_path = quote(unquote(parsed.path), safe="/:._-()")
    return urlunparse((parsed.scheme, parsed.netloc, safe_path, "", "", ""))


# ────────────────────────────────────────────────
# KODI ITEMS
# ────────────────────────────────────────────────
def addDir(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        "thumb": iconimage,
        "icon": iconimage,
        "poster": iconimage,
        "landscape": iconimage,
        "fanart": iconimage,
        "banner": iconimage,
    })

    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setInfo("video", {"title": name})

    plugin_url = (
        f"{sys.argv[0]}?"
        f"url={quote_plus(str(url))}"
        f"&action={quote_plus(str(action))}"
        f"&name={quote_plus(str(name))}"
        f"&icon={quote_plus(str(iconimage))}"
    )

    xbmcplugin.addDirectoryItem(
        handle=PLUGIN_HANDLE,
        url=plugin_url,
        listitem=li,
        isFolder=True
    )


def addLink(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        "thumb": iconimage,
        "icon": iconimage,
        "poster": iconimage,
        "landscape": iconimage,
        "fanart": iconimage,
        "banner": iconimage,
    })

    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setProperty("IsPlayable", "true")
    li.setInfo("video", {"title": name})

    plugin_url = (
        f"{sys.argv[0]}?"
        f"url={quote_plus(str(url))}"
        f"&action={quote_plus(str(action))}"
        f"&name={quote_plus(str(name))}"
        f"&icon={quote_plus(str(iconimage))}"
    )

    xbmcplugin.addDirectoryItem(
        handle=PLUGIN_HANDLE,
        url=plugin_url,
        listitem=li,
        isFolder=False
    )