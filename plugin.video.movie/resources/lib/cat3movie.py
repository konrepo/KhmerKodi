import re
import sys
import json
import xbmc
import xbmcplugin
import xbmcgui

from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, urlunparse, quote, unquote, urljoin

from resources.lib.handlers_khmer import (
    OpenSoup as OpenSoup_KH,
    OpenURL as OpenURL_KH,
)

from resources.lib.handlers_common import USER_AGENT

from resources.lib.handlers_playback import (
    resolve_redirect,
    VIDEOLINKS,
    enable_inputstream_adaptive,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)

ADDON_ID = "plugin.video.movie"
PLUGIN_HANDLE = int(sys.argv[1])

CAT3MOVIE = "https://www.cat3movie.club/"


# ────────────────────────────────────────────────
#  LOGGING
# ────────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] [cat3movie] {msg}", level)


# ────────────────────────────────────────────────
#  INDEX / SEARCH
# ────────────────────────────────────────────────
def INDEX_CAT3MOVIE(url):
    _render_cat3movie_listing(
        url=url,
        label_suffix=None,
        include_pagination=True,
        end_directory=True
    )


def SINDEX_CAT3MOVIE(url, end_directory=True):
    _render_cat3movie_listing(
        url=url,
        label_suffix=" [COLOR green]Cat3Movie[/COLOR]",
        include_pagination=False,
        end_directory=end_directory
    )


def _clean_cat3movie_title(title):
    title = (title or "").strip()

    title = title.replace("&#8211;", "–").replace("&amp;", "&").strip()

    if "|" in title:
        title = title.split("|", 1)[0].strip()

    if "–" in title:
        title = title.split("–", 1)[0].strip()

    title = re.sub(r"[^\x00-\x7F]+", "", title).strip()
    title = re.sub(r"\s+", " ", title).strip()

    return title


def get_post_image(url):
    try:
        html = OpenURL_KH(url, as_text=True)
        if not html:
            return ""

        m = re.search(r'<meta property="og:image" content="([^"]+)"', html, re.I)
        if m:
            return clean_image_url(m.group(1))
    except Exception as e:
        log(f"Failed to fetch fallback image for {url}: {e}", xbmc.LOGWARNING)

    return ""


def _render_cat3movie_listing(url, label_suffix=None, include_pagination=True, end_directory=True):
    try:
        soup, html = OpenSoup_KH(url, return_html=True)
    except Exception as e:
        log(f"Listing fetch failed: {url} :: {e}", xbmc.LOGERROR)
        if end_directory:
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if not soup:
        log(f"No soup returned for listing: {url}", xbmc.LOGERROR)
        if end_directory:
            xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    posts = soup.select("article.listing-item")

    if not posts:
        log(f"No listing items found: {url}", xbmc.LOGWARNING)

    for post in posts:
        try:
            title_link = post.select_one("h2.title a.post-url, p.title a.post-url")
            if not title_link:
                continue

            post_url = (title_link.get("href") or "").strip()
            raw_title = title_link.get_text(" ", strip=True).strip()
            title = _clean_cat3movie_title(raw_title)

            if not post_url or not title:
                continue

            img_tag = post.select_one("a.img-holder")
            image = ""
            if img_tag:
                image = (
                    img_tag.get("data-src")
                    or img_tag.get("data-bsrjs")
                    or img_tag.get("src")
                    or ""
                ).strip()

            image = clean_image_url(image)

            bad_hosts = (
                "photos.hancinema.net",
            )

            if any(host in image.lower() for host in bad_hosts):
                log(f"Blocked hotlink image host: {image}", xbmc.LOGWARNING)
                fallback = get_post_image(post_url)
                image = fallback if fallback else ""

            cat_tag = post.select_one(".term-badges .term-badge a")
            category = cat_tag.get_text(" ", strip=True) if cat_tag else ""

            label = title
            if category:
                label += f" [COLOR gold]({category})[/COLOR]"
            if label_suffix:
                label += label_suffix

            addDir(label, post_url, "episode_cat3movie", image)

        except Exception as e:
            log(f"Failed parsing listing item: {e}", xbmc.LOGWARNING)

    if include_pagination:
        next_page = _find_next_page(soup, html)
        if next_page:
            addDir("NEXT PAGE", next_page, "index_cat3movie", "")

    if end_directory:
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def _find_next_page(soup, html=""):
    next_page = ""

    next_tag = soup.select_one("a.next.page-numbers[href]")
    if next_tag:
        next_page = (next_tag.get("href") or "").strip()

    if not next_page:
        for a in soup.select(".pagination a.page-numbers[href]"):
            text = a.get_text(" ", strip=True).lower()
            href = (a.get("href") or "").strip()
            if text.startswith("next") and href:
                next_page = href
                break

    if not next_page and html:
        m = re.search(
            r'<a[^>]+class="[^"]*next\s+page-numbers[^"]*"[^>]+href="([^"]+)"',
            html,
            re.I
        )
        if m:
            next_page = m.group(1).strip()

    return next_page


# ────────────────────────────────────────────────
#  EPISODE / POST PAGE
# ────────────────────────────────────────────────
def EPISODE_CAT3MOVIE(url, v_image=""):
    log(f"EPISODE_CAT3MOVIE url={url}")

    try:
        html = OpenURL_KH(url, as_text=True)
    except Exception as e:
        log(f"Post fetch failed: {url} :: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Could not load this page.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    if not html:
        log(f"Empty HTML for post page: {url}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Could not load this page.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    soup = BeautifulSoup(html, "html.parser")
    v_image = clean_image_url(v_image)

    page_title = ""
    title_tag = soup.select_one("h1.single-post-title .post-title")
    if title_tag:
        page_title = title_tag.get_text(" ", strip=True)
        page_title = _clean_cat3movie_title(page_title)

    links = extract_video_sources(soup, html, url, page_title)

    if not links:
        xbmcgui.Dialog().ok("No Sources Found", "No playable video sources were detected on this page.")
        log(f"No playable sources found: {url}", xbmc.LOGWARNING)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    direct_ext = (".mp4", ".m3u8", ".mov", ".mkv", ".webm")

    for idx, item in enumerate(links, start=1):
        vurl = (item.get("file") or "").strip()
        if not vurl:
            continue

        vtitle = (item.get("title") or f"Source {idx:02d}").strip()
        base_url = vurl.split("?", 1)[0].lower()

        if any(host in vurl.lower() for host in (
            "ok.ru",
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "drive.google.com",
            "docs.google.com/file/",
            "play.cat3movie.club",
            "playhydrax.com",
            "sooplive.co.kr",
            "afreecatv",
            "play.sooplive.co.kr",
        )):
            addLink(vtitle, vurl, "video_hosting", v_image)
        elif base_url.endswith(direct_ext):
            addLink(vtitle, vurl, "play_direct", v_image)
        else:
            addLink(vtitle, vurl, "video_hosting", v_image)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def extract_video_sources(soup, html, page_url="", page_title=""):
    found = []
    seen = set()

    def clean_link(link):
        link = (link or "").strip()
        if not link:
            return ""

        if page_url:
            link = urljoin(page_url, link)

        link = (
            link.replace("&amp;", "&")
                .replace("\\/", "/")
                .replace("\\u0026", "&")
                .strip()
        )
        return link

    def is_supported_link(link):
        test = (link or "").lower()
        if not test:
            return False

        if "playhydrax.com" in test:
            return False

        if any(ext in test for ext in (".m3u8", ".mp4", ".mov", ".mkv", ".webm")):
            return True

        if any(host in test for host in (
            "ok.ru",
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "drive.google.com",
            "docs.google.com",
            "sooplive.co.kr",
            "afreecatv",
            "play.sooplive.co.kr",
            "play.cat3movie.club",
        )):
            return True

        return False

    def add_found(link, title=None):
        link = clean_link(link)
        if not link or link in seen or not is_supported_link(link):
            return False

        seen.add(link)
        found.append({
            "title": title or f"Source {len(found) + 1:02d}",
            "file": link
        })
        return True

    # 0) explicit server list
    server_links = soup.select("#server-list a[href]")
    if server_links:
        for a in server_links:
            src = (a.get("href") or "").strip()
            label = a.get_text(" ", strip=True).strip()

            if not src:
                continue

            if "playhydrax.com" in src.lower():
                log(f"Skipping unsupported Cat3Movie server: {src}", xbmc.LOGWARNING)
                continue

            if page_title and label:
                add_found(src, f"{page_title} [COLOR grey]({label})[/COLOR]")
            else:
                add_found(src, label or f"Source {len(found) + 1:02d}")

        return found

    # 1) <video> and <source>
    for tag in soup.select("video[src], video source[src]"):
        src = (tag.get("src") or "").strip()
        if src:
            add_found(src, "Direct Video")

    # 2) iframes
    for iframe in soup.select("iframe[src]"):
        src = (iframe.get("src") or "").strip()
        if src:
            add_found(src, "Embedded Player")

    # 3) direct media URLs found anywhere in page source
    for src in re.findall(
        r'https?://[^\s\'"]+\.(?:m3u8|mp4|mov|mkv|webm)(?:\?[^\s\'"]*)?',
        html,
        re.I
    ):
        add_found(src, page_title or f"Source {len(found) + 1:02d}")

    # 4) common embeds
    embed_patterns = [
        (r'https?://(?:www\.)?ok\.ru/[^\s\'"]+', "OK.ru"),
        (r'https?://(?:www\.)?youtube\.com/[^\s\'"]+', "YouTube"),
        (r'https?://youtu\.be/[^\s\'"]+', "YouTube"),
        (r'https?://(?:player\.)?vimeo\.com/[^\s\'"]+', "Vimeo"),
        (r'https?://(?:drive|docs)\.google\.com/[^\s\'"]+', "Google Drive"),
        (r'https?://[^\s\'"]*sooplive\.co\.kr[^\s\'"]*', "SOOP"),
        (r'https?://[^\s\'"]*afreecatv[^\s\'"]*', "AfreecaTV"),
        (r'https?://[^\s\'"]*play\.sooplive\.co\.kr[^\s\'"]*', "SOOP"),
        (r'https?://[^\s\'"]*play\.cat3movie\.club[^\s\'"]*', "Cat3Movie"),
    ]

    for pattern, title in embed_patterns:
        for src in re.findall(pattern, html, re.I):
            add_found(src, title)

    return found


# ────────────────────────────────────────────────
#  IMAGE HELPERS
# ────────────────────────────────────────────────
def clean_image_url(img_url):
    if not img_url:
        return ""

    img_url = img_url.strip().replace("&amp;", "&")
    img_url = img_url.split("?", 1)[0]

    parsed = urlparse(img_url)
    safe_path = quote(unquote(parsed.path), safe="/:._-()")
    return urlunparse((parsed.scheme, parsed.netloc, safe_path, "", "", ""))


# ────────────────────────────────────────────────
#  KODI ITEMS
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