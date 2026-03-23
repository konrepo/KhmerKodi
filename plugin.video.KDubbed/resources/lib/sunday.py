# ────────────────────────────────────────────────
#  SUNDAYDRAMA SITE HANDLER
# ────────────────────────────────────────────────
import re, sys, json, xbmc, xbmcplugin, xbmcgui
from urllib.parse import urljoin, quote_plus, unquote_plus, urlparse, urlunparse, quote, unquote
from html import unescape as html_unescape
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
    
# ── Plugin Handle ───────────────────────────────
SUNDAY       = 'https://www.sundaydrama.com/'
PLUGIN_HANDLE = int(sys.argv[1])


############## SUNDAYDRAMA ****************** 
def INDEX_SUNDAY(url):
    render_sunday_listing(url)

def SINDEX_SUNDAY(url):
    render_sunday_listing(url, label_suffix=" [COLOR green]Sunday[/COLOR]", include_pagination=False)

def render_sunday_listing(url, label_suffix="", include_pagination=True):
    try:
        headers = {'Referer': 'https://www.sundaydrama.com/', 'User-Agent': USER_AGENT}
        html = OpenURL_KH(url, headers=headers, as_text=True)
        if not html:
            xbmc.log(f"[KDUBBED] Empty response from URL: {url}", xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", "Failed to retrieve SundayDrama content.")
            return

        soup = BeautifulSoup(html, 'html.parser')

        main_container = soup.find('div', class_='blog-posts')
        if not main_container:
            xbmc.log("[KDUBBED] Could not find main post container.", xbmc.LOGWARNING)
            return

        for post in main_container.find_all('div', class_='entry-inner'):
            a_tag = post.find('a', class_='entry-image-wrap is-image')
            if not a_tag:
                continue

            v_link = a_tag.get('href', '').strip()
            v_title = a_tag.get('title', 'No Title').strip()

            v_image = ''
            span_tag = a_tag.find('span')
            if span_tag and span_tag.has_attr('data-src'):
                v_image = span_tag['data-src'].strip()
            else:
                img_tag = a_tag.find('img')
                if img_tag and img_tag.has_attr('src'):
                    v_image = img_tag['src'].strip()

            if v_image:
                if "bp.blogspot.com" in v_image or "blogger.googleusercontent.com" in v_image:
                    v_image = re.sub(r'/s\d+(?:-[a-z]+)*/', '/s1600/', v_image)
                v_image = clean_image_url(v_image)
                xbmc.log(f"[KDUBBED] SUNDAY CLEANED LISTING IMAGE: {v_image}", xbmc.LOGINFO)

            label = v_title + label_suffix if label_suffix else v_title

            if v_link:
                addDir(label, v_link, "episode_players", v_image)

        if include_pagination:
            next_page = soup.find('a', class_='blog-pager-older-link')
            if next_page and next_page.has_attr('href'):
                next_url = html_unescape(next_page['href'])
                if "?m=1" not in next_url:
                    next_url += "&m=1" if "?" in next_url else "?m=1"
                addDir('[B]Next Page >>>[/B]', next_url, "index_sunday", '')

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    except Exception as e:
        import traceback
        xbmc.log(f"[KDUBBED] render_sunday_listing failed: {e}\n{traceback.format_exc()}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Could not load SundayDrama page.")

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