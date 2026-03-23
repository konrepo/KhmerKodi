# ────────────────────────────────────────────────
#  CKCH7 SITE HANDLER
# ────────────────────────────────────────────────

import re, sys, json, xbmc, xbmcplugin, xbmcgui
from urllib.parse import urljoin, quote_plus, unquote_plus, urlparse, urlunparse, quote, unquote
from bs4 import BeautifulSoup

# ── Local Handlers ──────────────────────────────
from resources.lib.handlers_khmer import (
    OpenSoup as OpenSoup_KH,
    OpenURL as OpenURL_KH,
)
from resources.lib.handlers_common import USER_AGENT
from resources.lib.handlers_blogid import ADDON_ID
try:
    ADDON_ID
except NameError:
    ADDON_ID = "plugin.video.KDubbed"

# ── Local constants ─────────────────────────────
CKCH7 = "https://www.ckh7.com/"
PLUGIN_HANDLE = int(sys.argv[1])


############## ckch7 ****************** 
def INDEX_CKCH7(url):
    _render_ckch7_listing(url)

def SINDEX_CKCH7(url):
    _render_ckch7_listing(url, label_suffix=" [COLOR green]Ckh7[/COLOR]", include_pagination=False)

def _render_ckch7_listing(url, label_suffix="", include_pagination=True):
    soup, _ = OpenSoup_KH(unquote_plus(url), return_html=True)

    for card in soup.select("div.card.shadow-sm[class*='post-']"):
        a   = card.select_one("h3.post-title a[href]") or card.select_one("a[href]")
        img = card.find("img")
        if not a or not img:
            continue

        v_link  = urljoin(CKCH7, a["href"])
        v_title = (a.get("title") or a.get_text(strip=True) or img.get("title") or img.get("alt") or "No Title").strip()
        v_image = img.get("data-echo") or img.get("data-src") or img.get("data-original") or img.get("src") or ""
        if "melody-lzld.png" in v_image:
            v_image = img.get("data-echo") or v_image
        v_image = urljoin(CKCH7, v_image)
        v_image = clean_image_url(v_image)

        addDir(f"{v_title}{label_suffix}", v_link, "episode_players", v_image)

    if include_pagination:
        for a in soup.select("ul.pagination a[href], nav .pagination a[href]"):
            addDir(
               f"Page {a.get_text(strip=True)}", 
               urljoin(CKCH7, a["href"]), 
               "index_ckch7", 
               ""
            )

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

def EPISODE_CKCH7(url, v_image=""):
    html = OpenURL_KH(url, as_text=True)
    if not html:
        xbmc.log(f"[{ADDON_ID}] Failed to fetch CKCH7 page: %s" % url, xbmc.LOGERROR)
        return

    v_image = clean_image_url(v_image)

    m = re.search(r"options\.player_list\s*=\s*(\[[\s\S]+?\]);", html)
    if not m:
        m = re.search(r"const\s+list_vdoiframe\s*=\s*(\[[\s\S]+?\])\s*;", html)
    if not m:
        m = re.search(r"const\s+videos\s*=\s*(\[[\s\S]+?\])\s*;", html)

    if not m:
        xbmcgui.Dialog().ok("Error", "No episodes found on CKCH7.")
        xbmc.log(f"[{ADDON_ID}] CKCH7: no video arrays found", xbmc.LOGERROR)
        return

    try:
        raw = m.group(1)
        raw = re.sub(r",\s*([\]}])", r"\1", raw)
        raw = re.sub(r'([{\s,])(\w+)\s*:', r'\1"\2":', raw)
        raw = raw.replace("'", '"')
        videos = json.loads(raw)
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] CKCH7 JSON parse failed: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to parse CKCH7 episodes.")
        return

    DIRECT_EXT = (".mp4", ".m3u8", ".aaa.mp4", ".gaa.mp4")
    seen = set()
    ep_counter = 1

    for v in videos:
        vurl = (v.get("file") or "").replace("\\", "").strip()
        if not vurl or vurl.lower() in seen:
            continue
        seen.add(vurl.lower())

        if vurl.startswith("https://youtu.be/"):
            vurl = vurl.replace("https://youtu.be/", "https://www.youtube.com/watch?v=")

        vtitle = f"Episode {ep_counter:02d}"
        ep_counter += 1

        if vurl.split("?", 1)[0].endswith(DIRECT_EXT):
            addLink(vtitle, vurl, "play_direct", v_image)
        elif any(host in vurl for host in ["ok.ru", "youtube.com", "youtu.be", "vimeo.com"]):
            addLink(vtitle, vurl, "video_hosting", v_image)
        else:
            addLink(vtitle, vurl, "video_hosting", v_image)  # fallback

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

# ── clean_image_url() ────────────────────
def clean_image_url(img_url):
    if not img_url:
        return ""

    img_url = img_url.strip()

    if re.search(r"^https?://i\d\.wp\.com/blogger\.googleusercontent\.com/", img_url):
        img_url = re.sub(r"^https?://i\d\.wp\.com/", "https://", img_url)

    img_url = img_url.split("?", 1)[0]

    parsed = urlparse(img_url)
    safe_path = quote(unquote(parsed.path), safe="/:._-()")
    return urlunparse((parsed.scheme, parsed.netloc, safe_path, "", "", ""))

# ── Shared playback handlers ────────────────────
from resources.lib.handlers_playback import (
    resolve_redirect,
    VIDEOLINKS,
    enable_inputstream_adaptive,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)

# ────────────────────────────────────────────────
#  BASIC DIRECTORY HELPERS
# ────────────────────────────────────────────────
def addDir(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        'thumb': iconimage,
        'icon': iconimage,
        'poster': iconimage,
        'landscape': iconimage,
        'fanart': iconimage,
        'banner': iconimage,
    })
    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setInfo('video', {'title': name})

    u = (
        f"{sys.argv[0]}?"
        f"url={quote_plus(str(url))}"
        f"&action={quote_plus(str(action))}"
        f"&name={quote_plus(str(name))}"
        f"&icon={quote_plus(str(iconimage))}"
    )
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=True)

def addLink(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        'thumb': iconimage,
        'icon': iconimage,
        'poster': iconimage,
        'landscape': iconimage,
        'fanart': iconimage,
        'banner': iconimage,
    })
    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setProperty("IsPlayable", "true")
    li.setInfo('video', {'title': name})

    u = (
        f"{sys.argv[0]}?"
        f"url={quote_plus(str(url))}"
        f"&action={quote_plus(str(action))}"
        f"&name={quote_plus(str(name))}"
        f"&icon={quote_plus(str(iconimage))}"
    )
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=False) 
