# ────────────────────────────────────────────────
#  KHMERAVENUE & MERLKON (KHMERDRAMA) SITE HANDLER
# ────────────────────────────────────────────────
import re, sys, json, xbmc, xbmcplugin, xbmcgui
from urllib.parse import urljoin, quote_plus, urlparse, urlunparse, quote, unquote
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

# ── Local Constants ─────────────────────────────
KHMERAVENUE = "https://www.khmeravenue.com/"
MERLKON     = "https://www.khmerdrama.com/"
PLUGIN_HANDLE = int(sys.argv[1])


############## KhmerAve / Merlkon SITE ******************
def INDEX_GENERIC(url, action, site_name='', label_suffix=None):
    try:
        headers = {'User-Agent': USER_AGENT}
        if 'khmeravenue.com' in url or site_name == 'khmeravenue':
            headers['Referer'] = KHMERAVENUE
        elif 'khmerdrama.com' in url or site_name == 'merlkon':
            headers['Referer'] = MERLKON

        soup, html = OpenSoup_KH(url, return_html=True, headers=headers)

        items = soup.select('div.col-6.col-sm-4.thumbnail-container, div.card-content')

        def style_url(style):
            if not style:
                return ""
            m = re.search(r'url\((.*?)\)', style)
            return m.group(1).strip('\'"') if m else ""

        for item in items:
            try:
                classes = item.get('class') or []
                is_thumb = 'thumbnail-container' in classes

                if is_thumb:
                    a_tag   = item.find('a')
                    h3_tag  = item.find('h3')
                    h4_tag  = item.find('h4')
                    v_link  = a_tag.get('href', '') if a_tag else ''
                    v_title = h3_tag.get_text(strip=True) if h3_tag else ''
                    v_title = v_title.replace("&#8217;", "")
                    v_info  = h4_tag.get_text(strip=True) if h4_tag else ''
                    v_info  = v_info.replace("Episode", "").strip()
                    v_image = style_url((item.find('div', style=True) or {}).get('style'))
                else:
                    a_tag   = item.find('a', href=True)
                    v_link  = a_tag['href'] if a_tag else ''
                    h3      = item.find('h3')
                    v_title = h3.get_text(strip=True) if h3 else ''
                    ep_tag  = item.find('span', class_='card-content-episode-number')
                    v_info  = ep_tag.get_text(strip=True) if ep_tag else ''
                    v_info  = v_info.replace("Ep", "").strip()
                    img_div = item.find('div', class_='card-content-image')
                    v_image = style_url(img_div.get('style') if img_div else '')

                if v_image:
                    v_image = urljoin(url, v_image)
                    v_image = re.sub(r'/s\d+(?:-[a-z]+)*/', '/s1600/', v_image)
                    v_image = clean_image_url(v_image)
                    xbmc.log(f"[{ADDON_ID}] KHMERAVE CLEANED LISTING IMAGE: {v_image}", xbmc.LOGINFO)

                if v_link and v_title:
                    v_link = urljoin(url, v_link)
                    name = f"{v_title} {v_info}".strip()
                    label = f"{name}{label_suffix}" if label_suffix else name
                    addDir(label, v_link, "episode_players", v_image)

            except Exception as e:
                xbmc.log(f"[{ADDON_ID}] INDEX_GENERIC ({site_name}) item error: {str(e)}", xbmc.LOGWARNING)

        try:
            nav = soup.select_one('nav.navigation.pagination .nav-links')
            if nav:
                for a in nav.select('a.page-numbers[href]'):
                    text = a.get_text(strip=True)
                    href = urljoin(url, a['href'])
                    classes = a.get('class') or []
                    if 'next' in classes:
                        addDir('Next »', href, action, '')
                    elif 'prev' in classes:
                        addDir('« Previous', href, action, '')
                    elif text.isdigit():
                        addDir(f'Page {text}', href, action, '')
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] INDEX_GENERIC pagination error: {str(e)}", xbmc.LOGWARNING)

        try:
            pnav = soup.select_one("div.wp-pagenavi")
            if pnav:
                for a in pnav.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = urljoin(url, a["href"])
                    classes = a.get("class") or []

                    if "nextpostslink" in classes:
                        addDir('Next »', href, action, '')
                    elif "previouspostslink" in classes:
                        addDir('« Previous', href, action, '')
                    elif "last" in classes:
                        addDir('Last Page →', href, action, '')
                    elif text.isdigit():
                        addDir(f'Page {text}', href, action, '')
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] WP-PageNavi pagination error: {str(e)}", xbmc.LOGWARNING)

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] INDEX_GENERIC ({site_name}) failed: {str(e)}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", f"Failed to load {site_name or 'page'}.")
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return


def EPISODE_GENERIC(url, v_image="", site_name=''):
    html = OpenURL_KH(url, as_text=True)
    if not html:
        xbmc.log(f"[{ADDON_ID}] EPISODE_GENERIC ({site_name}) failed to fetch: {url}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", f"Failed to load {site_name or 'page'} episode list.")
        return

    v_image = clean_image_url(v_image)
    xbmc.log(f"[{ADDON_ID}] KHMERAVE CLEANED EPISODE IMAGE: {v_image}", xbmc.LOGINFO)

    decoded = html.decode("utf-8", errors="ignore") if isinstance(html, bytes) else html
    soup = BeautifulSoup(decoded, "html.parser")

    submitter = ""
    m = re.search(r"Submitter:\s*<b[^>]*>([^<]+)</b>", decoded, re.IGNORECASE)
    if m:
        submitter = m.group(1).strip()
        xbmc.log(f"[{ADDON_ID}] Found submitter: {submitter}", xbmc.LOGINFO)

    episodes = []
    for a in soup.select("table#latest-videos a[href], div.col-xs-6.col-sm-6.col-md-3 a[href]"):
        v_link = urljoin(url, a['href'])
        episodes.append(v_link)

    if episodes:
        episodes.reverse()
        for i, v_link in enumerate(episodes, start=1):
            v_title = f"Episode {i:02d}"
            if submitter:
                v_title += f" [COLOR grey](by {submitter})[/COLOR]"
            addLink(v_title, v_link, "videolinks", v_image)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    player_list = []
    m = re.search(r"options\.player_list\s*=\s*(\[[^\]]+\])\s*;", decoded, re.DOTALL)
    if m:
        try:
            player_list = json.loads(m.group(1))
        except Exception:
            pass

    if not player_list:
        m = re.search(r"const\s+videos\s*=\s*(\[[\s\S]+?\])\s*;", decoded)
        if m:
            raw = m.group(1)
            raw = re.sub(r",\s*([\]}])", r"\1", raw)
            raw = re.sub(r'([{\s,])(\w+)\s*:', r'\1"\2":', raw)
            raw = raw.replace("'", '"')
            try:
                player_list = json.loads(raw)
            except Exception:
                pass

    if player_list:
        for i, item in enumerate(player_list, start=1):
            v_link = (item.get('file') or '').strip()
            if not v_link:
                continue
            v_title = f"Episode {i:02d}"
            if submitter:
                v_title += f" [COLOR grey](by {submitter})[/COLOR]"
            if v_link.endswith((".mp4", ".m3u8")):
                addLink(v_title, v_link, "play_direct", v_image)
            else:
                addLink(v_title, v_link, "video_hosting", v_image)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmc.log(f"[{ADDON_ID}] EPISODE_GENERIC ({site_name}) no episodes found: {url}", xbmc.LOGWARNING)
    xbmcgui.Dialog().ok("No Episodes Found", "Sorry, no playable episodes were detected.")
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