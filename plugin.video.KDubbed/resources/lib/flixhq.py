# ────────────────────────────────────────────────
#  SERIALGO / FLIXHQ SITE HANDLER
# ────────────────────────────────────────────────

# ── Core Imports ────────────────────────────────
import os, sys, re, json, urllib.parse
import xbmc, xbmcaddon, xbmcgui, xbmcplugin
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse

# ── External Libraries ──────────────────────────
import resolveurl
from html import unescape as html_unescape

# ── Local Handlers ──────────────────────────────
# Force FlixHQ to always use its own handler (ignore global Khmer override)
from resources.lib import handlers_flixhq
OpenURL_SG = handlers_flixhq.OpenURL
OpenSoup_SG = handlers_flixhq.OpenSoup
URL = handlers_flixhq.URL


# ── Kodi Add-on Globals ─────────────────────────
try:
    ADDON_ID
except NameError:
    ADDON_ID = "plugin.video.KDubbed"

PLUGIN_HANDLE = int(sys.argv[1])
BASE_URL = "https://flixhq.to/"


# ── GENRE MENU ────────────────────────────────────────────────
def GENRE_MENU():
    try:
        soup = OpenSoup_SG(BASE_URL)
        seen = {}

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not href or not title:
                continue  # skip blanks
            if "/genre/" in href:
                seen[href] = title

        for href, title in sorted(seen.items(), key=lambda x: x[1].lower()):
            full_url = urllib.parse.urljoin(BASE_URL, href)
            xbmc.log(f"[{ADDON_ID}] GENRE found: {title} → {full_url}", xbmc.LOGINFO)
            addDir(title, full_url, "index_serialgo")

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] GENRE_MENU scrape failed: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", "Failed to load Genres", xbmcgui.NOTIFICATION_ERROR)

# ── Country Menu ────────────────────────────────────────────────
def COUNTRY_MENU():
    try:
        soup = OpenSoup_SG(BASE_URL)
        seen = {}

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not href or not title:
                continue  # skip blanks
            if "/country/" in href:
                seen[href] = title

        # Add Philippines manually if missing
        if "/country/PH" not in seen:
            seen["/country/PH"] = "Philippines"

        for href, title in sorted(seen.items(), key=lambda x: x[1].lower()):
            full_url = urllib.parse.urljoin(BASE_URL, href)
            xbmc.log(f"[{ADDON_ID}] COUNTRY found: {title} → {full_url}", xbmc.LOGINFO)
            addDir(title, full_url, "index_serialgo")

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] COUNTRY_MENU scrape failed: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", "Failed to load Countries", xbmcgui.NOTIFICATION_ERROR)

# ── Listing Handler ─────────────────────────────────────────────
def INDEX_SERIALGO(url, label_suffix=""):
    try:
        xbmc.log(f"[{ADDON_ID}] Fetching index: {url}", xbmc.LOGINFO)
        html = OpenURL_SG(url, as_text=True)  # or OpenURL_SG if that’s your custom wrapper
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.flw-item')

        if not items:
            raise Exception("No movies or shows found on this page.")

        for item in items:
            title_tag = item.select_one('.film-name a[href]')
            img_tag = item.select_one('img')
            year_tag = item.select_one('.fdi-item')
            quality_tag = item.select_one('.film-poster-quality')
            type_tag = item.select_one('.fdi-type')

            if not title_tag or not img_tag:
                continue

            href = title_tag.get('href', '')
            title = title_tag.get_text(strip=True)
            year = year_tag.get_text(strip=True) if year_tag else ''
            quality = quality_tag.get_text(strip=True) if quality_tag else ''
            media_type = type_tag.get_text(strip=True) if type_tag else ''

            extras = " ".join(f"[{x}]" for x in (year, quality, media_type) if x)
            display_title = f"{title} {extras}" if extras else title
            if label_suffix:
                display_title += label_suffix

            image = img_tag.get('data-src') or img_tag.get('src') or ''
            full_url = urllib.parse.urljoin("https://flixhq.to", href)

            addDir(display_title, full_url, "type", iconimage=image)

        # ── Pagination ─────────────────────────────
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        current_page = int(query.get('page', '1'))

        def build_page_url(page_num):
            query['page'] = str(page_num)
            return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))

        if current_page > 1:
            addDir("[B]◀ Previous Page[/B]", build_page_url(current_page - 1), "index_serialgo")

        addDir("[B]Next Page ▶[/B]", build_page_url(current_page + 1), "index_serialgo")

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] INDEX_SERIALGO error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("FlixHQ Error", str(e), xbmcgui.NOTIFICATION_ERROR)

def SEARCH_FLIXHQ():
    search_text = GetInput("Enter Search Text", "Search FlixHQ")
    if not search_text:
        return

    try:
        slug = search_text.strip().lower().replace(" ", "-")
        search_url = f"{BASE_URL}search/{slug}"
        xbmc.log(f"[{ADDON_ID}] Searching FlixHQ: {search_url}", xbmc.LOGINFO)

        INDEX_SERIALGO(search_url) 
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] SEARCH_FLIXHQ error: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Error", f"Search failed: {e}", xbmcgui.NOTIFICATION_ERROR)


def TYPE(url, name):
    html=URL(url)
    if 'data-type="1"' in html:
        vid = re.search(r'[0-9].*', url)[0]
        sid = "https://flixhq.to/ajax/episode/list/"+str(vid)
        return PLAYLOOP_SG(sid, name)
    elif 'data-type="2"' in html:
        vid = re.search(r'[0-9].*', url)[0]
        sid = "https://flixhq.to/ajax/season/list/"+str(vid)
        return SEASON(sid, name)

def SEASON(url, name):
    link = OpenURL_SG(url)
    soup = BeautifulSoup(link, 'html.parser')
    div_index = soup('div',{'class':"dropdown-menu dropdown-menu-new"})
    for link in div_index:
        vLink = link("a")[0]["data-id"]
        vTitle = link('a')[0].text
        addDir(vTitle,'https://flixhq.to/ajax/season/episodes/'+vLink, "episode")

def EPISODE(url, name):
    link = OpenURL_SG(url)
    soup = BeautifulSoup(link, 'html.parser')
    div_index = soup('li',{'class':"nav-item"})
    for link in div_index:
        vLink = link("a")[0]["data-id"]
        vTitle = link('a')[0].text
        addDir(vTitle, f"https://flixhq.to/ajax/episode/servers/{vLink}", "server")
        
def SERVER(url,name):
    link = OpenURL_SG(url)
    soup = BeautifulSoup(link, 'html.parser')
    div_index = soup('li',{'class':"nav-item"})
    for link in div_index:
        vLink = link("a")[0]["data-id"]
        vTitle = link('a')[0].text
        addLink(vTitle, f"http://dodge.eu5.org/go/?url=https://flixhq.to/ajax/episode/sources/{vLink}", "play_server")
        
def PLAYLOOP_SG(url, name):
    link = OpenURL_SG(url)
    soup = BeautifulSoup(link, 'html.parser')
    div_index = soup('li',{'class':"nav-item"})
    for link in div_index:
        vLink = link("a")[0]["data-linkid"]
        vTitle = link('a')[0]['title']
        addLink(vTitle, "http://dodge.eu5.org/go/?url=https://flixhq.to/ajax/episode/sources/"+vLink, "play_server")

def PLAY_SERVER(url, name):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36'
    }
    try:
        html = OpenURL_SG(url, headers=headers)
        text = html.decode("utf-8", "ignore")
        try:
            data = json.loads(text)
            if "link" in data:
                Video = data["link"]
                xbmc.log(f"[KDUBBED] PLAY_SERVER: resolved JSON link = {Video}", xbmc.LOGINFO)
            else:
                raise ValueError("No 'link' field found in JSON")
        except Exception:
            match = re.search(r'</form>(.+)', text, re.DOTALL)
            if not match:
                xbmcgui.Dialog().notification("Error", "No video found", xbmcgui.NOTIFICATION_ERROR)
                xbmc.log(f"[KDUBBED] PLAY_SERVER: failed to extract video from {url}", xbmc.LOGERROR)
                return
            Video = match.group(1)

        if 'AKCloud' in name:
            PlayKA(Video)
        else:
            Play_VIDEO_SG(Video)

    except Exception as e:
        xbmc.log(f"[KDUBBED] PLAY_SERVER ERROR: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Playback Error", str(e), xbmcgui.NOTIFICATION_ERROR)

def Play_VIDEO_SG( VideoURL_SG):
    print ('PLAY VIDEO: %s' % VideoURL_SG)   
    item = xbmcgui.ListItem(path=VideoURL_SG)
    return xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
    
def PlayKA(VideoURL_SG):
    print ('PLAY VIDEO: %s' % VideoURL_SG)   
    item = xbmcgui.ListItem(path=VideoURL_SG)
    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    item.setMimeType('application/dash+xml')
    item.setContentLookup(False)
    return xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)

# ────────────────────────────────────────────────
#  BASIC DIRECTORY HELPERS
# ────────────────────────────────────────────────
def addLink(name, url, action, iconimage=""):
    u = f"{sys.argv[0]}?url={quote_plus(url)}&action={quote_plus(action)}&name={quote_plus(name)}"
    li = xbmcgui.ListItem(label=name)
    li.setArt({'icon': iconimage, 'poster': iconimage, 'thumb': iconimage})
    li.getVideoInfoTag().setTitle(name)
    li.setProperty("IsPlayable", "true")
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=False)

def addDir(name, url, action, iconimage=""):
    u = f"{sys.argv[0]}?url={quote_plus(str(url))}&action={quote_plus(str(action))}&name={quote_plus(str(name))}"
    li = xbmcgui.ListItem(label=name)
    if iconimage:
        li.setArt({'thumb': iconimage, 'icon': iconimage, 'poster': iconimage})
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=True)