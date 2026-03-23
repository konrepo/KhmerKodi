# ────────────────────────────────────────────────
#  IDRAMA SITE HANDLER
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

# ── Kodi Plugin Handle ──────────────────────────
IDRAMA = "https://www.idramahd.com/"
PLUGIN_HANDLE = int(sys.argv[1])

############## idrama ****************** 
def INDEX_IDRAMA(url):
    _render_idrama_listing(url)

def SINDEX_IDRAMA(url):
    _render_idrama_listing(url, label_suffix=" [COLOR green]iDrama[/COLOR]", include_pagination=False)

def _render_idrama_listing(url, label_suffix="", include_pagination=True):
    soup, _ = OpenSoup_KH(url, return_html=True)
    grid = soup.select_one('div.posts-wrap.th-grid-3') or soup

    for art in grid.select('article.hitmag-post'):
        a = art.select_one('h3.entry-title a[href]')
        if not a:
            continue
        v_link, v_title = urljoin(url, a['href']), a.get_text(strip=True)

        img = art.select_one('.archive-thumb img')
        v_image = ""
        if img:
            v_image = img.get('data-src') or img.get('src') or ""
            if not v_image and img.get('srcset'):
                v_image = img['srcset'].split(',')[0].split()[0]
            if v_image:
                v_image = urljoin(url, v_image)
                v_image = re.sub(r'/s\d+(?:-[a-z]+)*/', '/s1600/', v_image)
                v_image = clean_image_url(v_image)
                xbmc.log(f"[KDUBBED] CLEANED LISTING IMAGE: {v_image}", xbmc.LOGINFO)

        label = v_title + label_suffix  # suffix only shows in search
        addDir(label, v_link, "episode_players", v_image)

    if include_pagination:
        nxt = soup.find('link', rel='next')
        if nxt and nxt.get('href'):
            addDir("[B]NEXT PAGE ›[/B]", urljoin(url, nxt['href']), "index_idrama", "")

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
 
def EPISODE_TVSABAY(start_url, v_image=""):  # iDrama --> t.co --> tvsabay
    xbmc.log(f"[KDUBBED] EPISODE_TVSABAY received v_image={v_image}", xbmc.LOGINFO)

    html = OpenURL_KH(start_url, as_text=True)
    if not html:
        xbmc.log("[KDUBBED] Failed to fetch Tvsabay page", xbmc.LOGERROR)
        return

    m = re.search(r'data-post-id=["\']?(\d+)', html)
    if not m:
        xbmc.log("[KDUBBED] No post-id found in Tvsabay page", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("No Episodes Found", "Tvsabay post-id not found.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    post_id = m.group(1)
    xbmc.log(f"[KDUBBED] Found Tvsabay post-id: {post_id}", xbmc.LOGINFO)

    blog_id = "8016412028548971199"
    feed_url = f"https://www.blogger.com/feeds/{blog_id}/posts/default/{post_id}?alt=json"
    xbmc.log(f"[KDUBBED] Fetching Blogger feed: {feed_url}", xbmc.LOGINFO)

    json_text = OpenURL_KH(feed_url, as_text=True)
    try:
        data = json.loads(json_text)
    except Exception as e:
        xbmc.log(f"[KDUBBED] Failed to parse Tvsabay JSON: {e}", xbmc.LOGERROR)
        return

    content = data["entry"]["content"]["$t"]

    streams = re.findall(r"https?://[^\s\"']+\.m3u8", content)

    if not streams:
        xbmcgui.Dialog().ok("No Video", "No playable source found on Tvsabay.")
        return

    v_image = clean_image_url(v_image)
    xbmc.log(f"[KDUBBED] CLEANED EPISODE IMAGE: {v_image}", xbmc.LOGINFO)

    for idx, s in enumerate(streams, 1):
        addLink(f"Episode {idx}", s, "play_direct", v_image)
    xbmcplugin.setContent(PLUGIN_HANDLE, "episodes")           
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

def EPISODE_ONELEGEND(start_url, v_image=""):  # iDrama --> t.co --> OneLegend
    xbmc.log(f"[KDUBBED] EPISODE_ONELEGEND received v_image={v_image}", xbmc.LOGINFO)

    html = OpenURL_KH(start_url, as_text=True)
    if not html:
        xbmc.log("[KDUBBED] Failed to fetch OneLegend page", xbmc.LOGERROR)
        return

    m = re.search(r'data-post-id=["\']?(\d+)', html)
    if not m:
        xbmc.log("[KDUBBED] No post-id found in OneLegend page", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("No Episodes Found", "OneLegend post-id not found.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    post_id = m.group(1)
    xbmc.log(f"[KDUBBED] Found OneLegend post-id: {post_id}", xbmc.LOGINFO)

    # OneLegend uses a different Blogger blog_id
    blog_id = "596013908374331296"
    feed_url = f"https://www.blogger.com/feeds/{blog_id}/posts/default/{post_id}?alt=json"
    xbmc.log(f"[KDUBBED] Fetching OneLegend Blogger feed: {feed_url}", xbmc.LOGINFO)

    json_text = OpenURL_KH(feed_url, as_text=True)
    try:
        data = json.loads(json_text)
    except Exception as e:
        xbmc.log(f"[KDUBBED] Failed to parse OneLegend JSON: {e}", xbmc.LOGERROR)
        return

    content = data["entry"]["content"]["$t"]

    streams = re.findall(r"https?://[^\s\"']+\.(?:m3u8|mp4)", content)

    if not streams:
        xbmcgui.Dialog().ok("No Video", "No playable source found on OneLegend.")
        return

    v_image = clean_image_url(v_image)
    xbmc.log(f"[KDUBBED] CLEANED EPISODE IMAGE: {v_image}", xbmc.LOGINFO)

    for idx, s in enumerate(streams, 1):
        addLink(f"Episode {idx}", s, "play_direct", v_image)
    xbmcplugin.setContent(PLUGIN_HANDLE, "episodes")    
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

# ── clean_image_url() ────────────────────
def clean_image_url(img_url):
    if not img_url:
        return ""

    img_url = img_url.strip()

    # Convert wp.com proxy URLs back to direct blogger image URLs
    if re.search(r"^https?://i\d\.wp\.com/blogger\.googleusercontent\.com/", img_url):
        img_url = re.sub(r"^https?://i\d\.wp\.com/", "https://", img_url)

    # Strip query string
    img_url = img_url.split("?", 1)[0]

    # Encode spaces and unsafe chars in path only
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