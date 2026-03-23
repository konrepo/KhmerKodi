# ────────────────────────────────────────────────
#  VIDEO4KHMER SITE HANDLER 
# ────────────────────────────────────────────────

import re, sys, xbmc, xbmcplugin, xbmcgui
from urllib.parse import quote_plus
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
VIDEO4KHMER = "https://www.video4khmer36.com/"
PLUGIN_HANDLE = int(sys.argv[1])


############## VIDEO4KHMER ****************** 
def INDEX_VIDEO4U(url):
    _render_video4u_listing(url, label_suffix=None, include_pagination=True)

def SEARCH_VIDEO4U(search_term):
    url = f"https://www.video4khmer36.com/search.php?keywords={quote_plus(search_term)}&page=1"
    _render_video4u_listing(url, label_suffix=" [COLOR red]Video4Khmer[/COLOR]", include_pagination=False)

def _render_video4u_listing(url, label_suffix=None, include_pagination=True):
    soup, html = OpenSoup_KH(url, return_html=True)
    
    for item in soup.find_all('div', class_='cover-item'):
        cover_thumb = item.find('div', class_='cover-thumb')
        if not cover_thumb:
            continue
        style = cover_thumb.get('style', '')
        image = style.replace('background-image: url(', '').replace(')', '').strip()
        a_tag = cover_thumb.find('a', class_='hover-cover')
        if not a_tag:
            continue

        title = a_tag.get('title', 'No Title').strip()
        link  = a_tag.get('href', '').strip()

        ep_text = ''
        stats = cover_thumb.find_all('div', class_='video-stats')
        for stat in stats:
            span = stat.find('span')
            if span and "Ep" in span.text:
                ep_text = span.get_text(strip=True)

        label = f"{title} ({ep_text})" if ep_text else title
        if label_suffix:
            label += label_suffix

        addDir(label, link, "episode_players", image)

    # Pagination
    if include_pagination:
        for a in soup.select('ul.pagination a[href]'):
            page_url = a['href']
            page_num = re.sub(r'<i[^>]*></i>', '', a.decode_contents().strip())
            addDir(f"Page {page_num}", page_url, "index_video4u", "")
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
    
def EPISODE_VIDEO4KHMER(url):
    html = OpenURL_KH(url, as_text=True)
    if not html:
        xbmcgui.Dialog().ok("Error", "Failed to load Video4Khmer episode page.")
        return

    # --- Parse episodes ---
    soup = BeautifulSoup(html, "html.parser")
    episodes = {}
    for tr in soup.select("#episode-list tbody tr"):
        td = tr.find("td")
        if not td:
            continue
        a = td.find("a")
        title = a.get_text(strip=True) if a else td.get_text(strip=True)
        link = a["href"] if a else url
        m = re.search(r'(\d+)', title)
        ep_num = int(m.group(1)) if m else 0
        if ep_num and ep_num not in episodes:
            episodes[ep_num] = (title, link)

    # --- Show episodes or fallback ---
    if episodes:
        for ep_num in sorted(episodes):
            title, link = episodes[ep_num]
            addLink(title, link, "videolinks", "")
    else:
        xbmcgui.Dialog().ok("No Episodes Found", "No episode links detected on this page.")

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)  

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
def addDir(name, url, action, icon=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({'thumb': icon, 'icon': icon, 'poster': icon})
    u = f"{sys.argv[0]}?url={quote_plus(url)}&action={quote_plus(action)}&name={quote_plus(name)}"
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=True)

def addLink(name, url, action, icon=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({'thumb': icon, 'icon': icon, 'poster': icon})
    li.setProperty("IsPlayable", "true")
    u = f"{sys.argv[0]}?url={quote_plus(url)}&action={quote_plus(action)}&name={quote_plus(name)}"
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=False)   
