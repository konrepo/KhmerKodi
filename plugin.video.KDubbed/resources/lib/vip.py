# ────────────────────────────────────────────────
#  VIP SITE HANDLER
# ────────────────────────────────────────────────
import re, sys, json, xbmc, xbmcplugin, xbmcgui
from urllib.parse import urljoin, quote_plus, urlparse, urlunparse, quote, unquote
from bs4 import BeautifulSoup

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

VIP = 'https://phumikhmer.vip/'
PLUGIN_HANDLE = int(sys.argv[1])


def INDEX_VIP(url):
    _render_vip_listing(url)

def SINDEX_VIP(url, end_directory=True):
    _render_vip_listing(
        url,
        label_suffix=" [COLOR green]Vip[/COLOR]",
        include_pagination=False,
        end_directory=end_directory
    )

def _render_vip_listing(url, label_color=None, label_suffix="", include_pagination=True, end_directory=True):
    soup, html = OpenSoup_KH(url, return_html=True)

    for art in soup.find_all('article', class_=re.compile(r'listing-item-grid')):
        h2_tag = art.find('h2', class_='title')
        a_tag = h2_tag.find('a') if h2_tag else None
        feat_a = art.select_one('div.featured a')

        if not (a_tag and feat_a):
            continue

        v_link = urljoin(url, a_tag['href'])
        v_title = a_tag.get_text(strip=True)

        img_tag = art.select_one('div.featured img')
        v_image = feat_a.get('data-src') or (img_tag.get('src') if img_tag else "") or ""
        if v_image:
            v_image = urljoin(url, v_image)
            v_image = re.sub(r'/s\d+(?:-[a-z]+)*/', '/s1600/', v_image)
            v_image = clean_image_url(v_image)

        xbmc.log(f"[KDUBBED] VIP CLEANED LISTING IMAGE: {v_image}", xbmc.LOGINFO)

        label = f"{v_title}{label_suffix}" if label_suffix else v_title
        if label_color:
            label = f"[COLOR {label_color}]{label}[/COLOR]"

        addDir(label, v_link, "episode_players", v_image)

    if include_pagination:
        next_link = soup.find('link', rel='next')
        if next_link and next_link.get('href'):
            page_url = urljoin(url, next_link['href'])
            xbmc.log(f"[VIP] Next page URL resolved: {page_url}", xbmc.LOGINFO)
            addDir("[B]NEXT PAGE ›[/B]", page_url, "index_vip", "")

    if end_directory:
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def EPISODE_CRAFT4U(start_url, icon=""):
    html = OpenURL_KH(start_url, as_text=True)
    if not html:
        xbmc.log("[KDUBBED] Failed to fetch Craft4u page", xbmc.LOGERROR)
        return

    m = re.search(r'craft4u\.top/([^/]+)-0*(\d+)/', html)
    if not m:
        xbmc.log("[KDUBBED] Could not extract series base name", xbmc.LOGERROR)
        return

    base_name = m.group(1)
    ep_numbers = re.findall(rf"{base_name}-0*(\d+)", html)
    max_ep = max(map(int, ep_numbers)) if ep_numbers else 1

    icon = clean_image_url(icon)
    xbmc.log(f"[KDUBBED] VIP CLEANED EPISODE IMAGE: {icon}", xbmc.LOGINFO)

    for ep in range(1, max_ep + 1):
        ep_url = f"https://www.craft4u.top/{base_name}-{ep:02d}/"
        addLink(f"Episode {ep}", ep_url, "craft4u_play", icon)

    xbmcplugin.setContent(PLUGIN_HANDLE, "episodes")
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def PLAY_CRAFT4U(ep_url):
    if "tvsabay.com" in ep_url:
        xbmc.log(f"[{ADDON_ID}] WARNING: PLAY_CRAFT4U called with Tvsabay URL ({ep_url}). This should go to play_direct instead.", xbmc.LOGWARNING)
        return

    html = OpenURL_KH(ep_url, as_text=True)
    if not html:
        xbmc.log(f"[{ADDON_ID}] Failed to load Craft4u episode page", xbmc.LOGERROR)
        return

    iframe = re.search(r'<iframe[^>]+src=[\'"]([^\'"]+)', html, re.IGNORECASE)
    if iframe:
        vurl = iframe.group(1)
        xbmc.log(f"[{ADDON_ID}] Craft4u iframe found: {vurl}", xbmc.LOGINFO)
        VIDEO_HOSTING(vurl)
        return

    m = re.search(r'sources\s*:\s*\[\{file\s*:\s*"([^"]+)"', html, re.IGNORECASE)
    if m:
        vurl = m.group(1).replace("\\/", "/")
        xbmc.log(f"[{ADDON_ID}] Craft4u JWPlayer source: {vurl}", xbmc.LOGINFO)
        vurl = f"{vurl}|Referer=https://www.craft4u.top/&User-Agent={USER_AGENT}"
        Play_VIDEO(vurl)
        return

    m = re.search(r'file:\s*"([^"]+\.(?:mp4|m3u8|aaa\.mp4|gaa\.mp4))"', html)
    if m:
        vurl = m.group(1).replace("\\/", "/")
        xbmc.log(f"[{ADDON_ID}] Craft4u direct source: {vurl}", xbmc.LOGINFO)
        vurl = f"{vurl}|Referer=https://www.craft4u.top/&User-Agent={USER_AGENT}"
        Play_VIDEO(vurl)
        return

    xbmc.log(f"[{ADDON_ID}] No video source found in Craft4u page", xbmc.LOGERROR)
    xbmcgui.Dialog().ok("Playback Failed", "No playable video source found.")


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


from resources.lib.handlers_playback import (
    resolve_redirect,
    VIDEOLINKS,
    enable_inputstream_adaptive,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)


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