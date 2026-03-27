# ────────────────────────────────────────────────
#  PHUMIKHMER2 SITE HANDLER
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
from resources.lib.handlers_blogid import (
    ADDON_ID,
    extract_all_blogger_json_urls_from_page,
    parse_blogger_video_links,
)
try:
    ADDON_ID
except NameError:
    ADDON_ID = "plugin.video.KDubbed"

# ── Plugin Handle ───────────────────────────────
PHUMIK       = 'https://www.phumikhmer1.club/'
PLUGIN_HANDLE = int(sys.argv[1])

############## phumikhmer2 ****************** 
def INDEX_PHUMIK(url):
    _render_phumik_listing(url, label_suffix=None, include_pagination=True)

def SINDEX_PHUMIK(url, end_directory=True):  # for search
    _render_phumik_listing(
        url,
        label_suffix=" [COLOR green]PhumiKhmer[/COLOR]",
        include_pagination=False,
        end_directory=end_directory
    )

def _render_phumik_listing(url, label_suffix=None, include_pagination=True, end_directory=True):
    soup, html = OpenSoup_KH(url, return_html=True)

    for wrap in soup.find_all('div', class_='post-filter-inside-wrap'):
        a_tag = wrap.find('a', class_='post-filter-link')
        h2_tag = wrap.find('h2', class_=re.compile(r'entry-title'))
        img_tag = wrap.find('img', class_='snip-thumbnail')
        if not (a_tag and h2_tag and img_tag):
            continue

        v_link = a_tag['href']
        v_title = h2_tag.get_text(strip=True)
        v_image = img_tag.get('data-src') or img_tag.get('src', '')
        v_image = re.sub(r'/w\d+-h\d+[^/]+/', '/s1600/', v_image)
        v_image = clean_image_url(v_image)

        xbmc.log(f"[KDUBBED] PHUMIK CLEANED LISTING IMAGE: {v_image}", xbmc.LOGINFO)

        label = f"{v_title}{label_suffix}" if label_suffix else v_title
        addDir(label, v_link, "episode_players", v_image)

    if include_pagination:
        for page_url in re.findall(r"<a[^>]*class='blog-pager-older-link'[^>]*href='([^']+)'", html):
            addDir('NEXT PAGE', page_url, "index_phumik", "")

    if end_directory:
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
 
def EPISODE_PHUMIK(url, v_image=""):
    xbmc.log(f"[KDUBBED] EPISODE_PHUMIK received v_image={v_image}", xbmc.LOGINFO)

    html = OpenURL_KH(url, as_text=True)
    if not html:
        xbmc.log(f"[{ADDON_ID}] Failed to fetch PhumiKhmer page: {url}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Could not load this PhumiKhmer episode page.")
        return

    v_image = clean_image_url(v_image)
    xbmc.log(f"[KDUBBED] PHUMIK CLEANED EPISODE IMAGE: {v_image}", xbmc.LOGINFO)

    blogger_urls = extract_all_blogger_json_urls_from_page(html) or []
    all_links, seen = [], set()
    ep_counter = 1

    for blogger_url in blogger_urls:
        xbmc.log(f"[{ADDON_ID}] PhumiKhmer Blogger URL: {blogger_url}", xbmc.LOGINFO)
        links = parse_blogger_video_links(blogger_url) or []
        for link in links:
            vurl = (link.get("file") or "").strip()
            if not vurl or vurl in seen:
                continue
            seen.add(vurl)
            all_links.append({'file': vurl, 'title': f"Episode {ep_counter:02d}"})
            ep_counter += 1

    if all_links:
        DIRECT_EXT = (".mp4", ".m3u8", ".aaa.mp4", ".gaa.mp4", ".caa.mp4")
        for item in all_links:
            vurl, vtitle = item['file'], item['title']
            if any(h in vurl for h in ("ok.ru", "youtube.com", "youtu.be", "vimeo.com")):
                addLink(vtitle, vurl, "video_hosting", v_image)
            elif any(vurl.split("?", 1)[0].endswith(ext) for ext in DIRECT_EXT):
                addLink(vtitle, vurl, "play_direct", v_image)
            else:
                addLink(vtitle, vurl, "video_hosting", v_image)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmc.log(f"[{ADDON_ID}] No Blogger feeds on PhumiKhmer page, trying fallback parse", xbmc.LOGINFO)

    m = re.search(r"options\.player_list\s*=\s*(\[[\s\S]+?\]);", html) \
        or re.search(r"const\s+videos\s*=\s*(\[[\s\S]+?\]);", html)

    if m:
        try:
            raw = m.group(1)
            raw = re.sub(r",\s*([\]}])", r"\1", raw)
            raw = re.sub(r'([{\s,])(\w+)\s*:', r'\1"\2":', raw)
            raw = raw.replace("'", '"')
            videos = json.loads(raw)
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] JSON parse failed on PhumiKhmer page: {e}", xbmc.LOGERROR)
            videos = []
    else:
        videos = []

    if videos:
        for idx, v in enumerate(videos, start=1):
            vurl = (v.get("file") or "").strip()
            if not vurl:
                continue
            vtitle = f"Episode {idx:02d}"
            if any(h in vurl for h in ("ok.ru", "youtube.com", "youtu.be", "vimeo.com")):
                addLink(vtitle, vurl, "video_hosting", v_image)
            else:
                addLink(vtitle, vurl, "play_direct", v_image)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    xbmcgui.Dialog().ok("No Episodes Found", "Sorry, no playable episodes were detected on this PhumiKhmer page.")
    xbmc.log(f"[{ADDON_ID}] PhumiKhmer: no episode links found at {url}", xbmc.LOGWARNING)
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