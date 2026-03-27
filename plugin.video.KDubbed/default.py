# ── Compatibility & Imports ─────────────────────────────────────
import os, sys, re, ast, json, gzip, time, random, base64, string, requests, urllib.parse
import xml.dom.minidom, xml.etree.ElementTree as ET

# ── Kodi Modules ────────────────────────────────────────────────
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs

# ── External Libraries ──────────────────────────────────────────
import resolveurl
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus, unquote_plus, urljoin
from html import unescape as html_unescape
from resources.lib.handlers_common import USER_AGENT
from resources.lib.constants import khmertv

from resources.lib import (
    idrama,
    vip,
    ckch7,
    phumikhmer,
    khmerav,
    sunday,
    flixhq,
    lookmovie,
)

from resources.lib.handlers_blogid import (
    extract_all_blogger_json_urls_from_page,
    extract_vip_blogger_json_urls_from_page,
    parse_blogger_video_links,
    parse_blogger_video_links_script,
    is_vip_url,
    is_idrama_url,
)

from resources.lib.handlers_playback import (
    EPISODE_PLAYERS,
    resolve_redirect,
    VIDEOLINKS,
    enable_inputstream_adaptive,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)

# ── Imports ────────────────────────────────────────────────
from resources.lib.handlers_flixhq import OpenURL as OpenURL_SG, OpenSoup as OpenSoup_SG, URL
from resources.lib.handlers_khmer import OpenURL as OpenURL_KH, OpenSoup as OpenSoup_KH

# ── SerialGo specific aliases (defined first) ──────────────
OpenURL = OpenURL_SG
OpenSoup = OpenSoup_SG

# ── Global fallback (legacy Khmer default) ─────────────────
OpenURL = OpenURL_KH
OpenSoup = OpenSoup_KH

# USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"

# --- HTTP session & tiny negative cache ---
_SESSION = requests.Session()

# ── Logging Helper ──────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)
    
# ── Add-on Constants ────────────────────────────────────────────
ADDON_ID      = 'plugin.video.KDubbed'
ADDON         = xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH    = ADDON.getAddonInfo('path')
DATA_PATH     = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}')
PLUGIN_HANDLE = int(sys.argv[1])


# ── Base URLs ───────────────────────────────────────────────────
PHUMIK       = 'https://www.phumikhmer1.club/'
KHMERAVENUE  = 'https://www.khmeravenue.com/'
MERLKON      = 'https://www.khmerdrama.com/'
CKCH7        = 'http://www.ckh7.com/'
SUNDAY       = 'https://www.sundaydrama.com/'
VIP          = 'https://phumikhmer.vip/'
IDRAMA       = 'https://www.idramahd.com/'

# ── Icons and Fanart ────────────────────────────────────────────
IMAGE_PATH     = os.path.join(ADDON_PATH, 'resources', 'images')
ICON_JOLCHET   = os.path.join(IMAGE_PATH, 'icon.png')
ICON_SEARCH    = os.path.join(IMAGE_PATH, 'search1.png')
ICON_KHMERTV   = os.path.join(IMAGE_PATH, 'khmertv.png')
FANART         = os.path.join(IMAGE_PATH, 'fanart.jpg')
ICON_KHMERAVE  = os.path.join(IMAGE_PATH, 'khmerave.png')
ICON_MERLKON   = os.path.join(IMAGE_PATH, 'merlkon.png')
ICON_VIP       = os.path.join(IMAGE_PATH, 'vip.png')
ICON_SUNDAY    = os.path.join(IMAGE_PATH, 'sunday.png')
ICON_IDRAMA    = os.path.join(IMAGE_PATH, 'idrama.png')
ICON_PHUMIK2    = os.path.join(IMAGE_PATH, 'phumik2.png')


# ── Virtual Keyboard Input ──────────────────────────────────────
def GetInput(message, heading, is_hidden=False):
    keyboard = xbmc.Keyboard('', message, is_hidden)
    keyboard.setHeading(heading)
    keyboard.doModal()
    return keyboard.getText() if keyboard.isConfirmed() else ""

# Main Menu
def HOME():
    addDir("[COLOR yellow][B][I]SEARCH[/I][/B][/COLOR]", MERLKON, "search", ICON_SEARCH)
    addDir("Khmer Live TV", khmertv, "khmer_livetv", ICON_KHMERTV) 

    # ── Structured site definitions ─────────────────────────────
    sites = [
        {
            "title": "Vip • Sunday • iDrama • KhmerAve • Merlkon",
            "categories": [
                ("VIP", f"{VIP}", ICON_VIP, "index_vip"),            
                ("Sunday", f"{SUNDAY}", ICON_SUNDAY, "index_sunday"),
                ("iDrama", f"{IDRAMA}", ICON_IDRAMA, "index_idrama"),                
                ("KhmerAve", f"{KHMERAVENUE}album/", ICON_KHMERAVE, "index_khmeravenue"),
                ("Merlkon", f"{MERLKON}album/", ICON_MERLKON, "index_merlkon")
            ]
        },       
        {
            "title": "PhumiKhmer",
            #"logo": "https://phumikhmer2.com/home/img/logo.png",
            "action": "index_phumik",
            "categories": [
                ("Khmer", f"{MERLKON}country/cambodia/", ICON_MERLKON, "index_merlkon"),
                ("Korean", f"{KHMERAVENUE}country/korea/", ICON_KHMERAVE, "index_khmeravenue"),  
                ("Chinese", f"{PHUMIK}search/label/Chinese?&max-results=24", ICON_PHUMIK2),
                ("Korean1", f"{PHUMIK}search/label/Korea?&max-results=24", ICON_PHUMIK2),
                ("Thai", f"{PHUMIK}search/label/Thai?&max-results=24", ICON_PHUMIK2)                
            ]
        }
        #{
        #    "title": "Ckh7",
        #    "logo": "https://www.ckh7.com/uploads/custom-logo.png",
        #    "action": "index_ckch7",
        #    "categories": [
        #        ("Khmer", f"{CKCH7}category.php?cat=khmer"),
        #        ("Thai", f"{CKCH7}category.php?cat=thai"),
        #        ("Chinese", f"{CKCH7}category.php?cat=chinese")
        #    ]
        #},       
    ]

    # ── Render all site headers and categories ─────────────────
    for site in sites:
        header = f"**** [COLOR red]{site['title']}[/COLOR] ****"
        addDir(header, "", site.get('action', ''), site.get('logo', ''))

        for cat in site.get('categories', []):
            label = cat[0]
            url = cat[1] if len(cat) > 1 else ""
            icon = cat[2] if len(cat) > 2 else site.get('logo', '')
            action = cat[3] if len(cat) > 3 else site.get('action', '')
            addDir(label, url, action, icon)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

# Search function    
def SEARCH():
    kb = xbmc.Keyboard('', 'Enter Search Text')
    kb.doModal()
    if not kb.isConfirmed():
        return

    query = kb.getText().strip()
    if not query:
        return

    sources = [
        ("IDRAMA", ICON_IDRAMA, lambda q: idrama.SINDEX_IDRAMA(
            f'{idrama.IDRAMA}?s={quote_plus(q)}',
            end_directory=False
        )),
        ("KHMERAVE", ICON_KHMERAVE, lambda q: khmerav.INDEX_GENERIC(
            f'{khmerav.KHMERAVENUE}?s={quote_plus(q)}',
            'index_khmeravenue',
            'khmeravenue',
            label_suffix=" [COLOR yellow]KHMERAVE[/COLOR]",
            end_directory=False,
            include_pagination=False
        )),
        ("MERLKON", ICON_MERLKON, lambda q: khmerav.INDEX_GENERIC(
            f'{khmerav.MERLKON}?s={quote_plus(q)}',
            'index_merlkon',
            'merlkon',
            label_suffix=" [COLOR cyan]MERLKON[/COLOR]",
            end_directory=False,
            include_pagination=False
        )),
        ("PHUMIKHMER", ICON_PHUMIK2, lambda q: phumikhmer.SINDEX_PHUMIK(
            f'{phumikhmer.PHUMIK}search?q={quote_plus(q)}',
            end_directory=False
        )),
        ("SUNDAY", ICON_SUNDAY, lambda q: sunday.SINDEX_SUNDAY(
            f'{sunday.SUNDAY}search?q={quote_plus(q)}',
            end_directory=False
        )),
        ("VIP", ICON_VIP, lambda q: vip.SINDEX_VIP(
            f'{vip.VIP}?s={quote_plus(q)}',
            end_directory=False
        )),
        # ("CKCH7", ICON_WHATEVER, lambda q: ckch7.SINDEX_CKCH7(
        #     f'{ckch7.CKCH7}search.php?keywords={quote_plus(q)}',
        #     end_directory=False
        # )),
    ]

    errors = []

    for label, icon, search_func in sources:
        try:
            addDir(f"[B][COLOR red]----- {label} -----[/COLOR][/B]", "", "", icon)
            search_func(query)
        except Exception as e:
            errors.append(f"{label}: {e}")
            xbmc.log(f"[{ADDON_ID}] Search failed for {label}: {e}", xbmc.LOGERROR)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    if errors:
        xbmcgui.Dialog().notification(
            "Search Warning",
            f"{len(errors)} source(s) failed. Check log.",
            xbmcgui.NOTIFICATION_WARNING
        )


# KhmerTV
def KHMER_LIVETV():
    try:
        # Decode KhmerTV XML feed
        xml_data = OpenURL_KH(base64.b64decode(khmertv).decode("utf-8"))
        if isinstance(xml_data, bytes):
            xml_data = xml_data.decode("utf-8", errors="ignore")

        # Clean malformed XML
        xml_data = "\n".join(line.strip() for line in xml_data.splitlines() if line.strip())
        xml_data = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', xml_data)

        # Parse XML
        root = ET.fromstring(xml_data)
        items = root.findall(".//channel/item") or root.findall(".//item")
        if not items:
            raise Exception("No <item> found")

        xbmc.log(f"[{ADDON_ID}] Loaded {len(items)} KhmerTV channels", xbmc.LOGINFO)

        # Loop through items
        for item in items:
            title = item.findtext("title", "No Title").strip()
            url   = item.findtext("link", "").strip()
            icon  = item.findtext("thumbnail", "").strip() or ICON_KHMERTV
            resolve = item.findtext("resolve", "false").strip().lower() == "true"

            if not url:
                xbmc.log(f"[{ADDON_ID}] Missing URL for: {title}", xbmc.LOGWARNING)
                continue

            li = xbmcgui.ListItem(label=title)
            li.setArt({'thumb': icon, 'icon': icon, 'poster': icon})
            li.getVideoInfoTag().setTitle(title)
            li.setProperty('IsPlayable', 'true' if resolve else 'false')

            # use centralized playback modes
            action = "playloop" if resolve else "video_hosting"

            plugin_url = f"{sys.argv[0]}?action={action}&url={quote_plus(url)}"
            xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, plugin_url, li, not resolve)

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] KHMER_LIVETV load failed: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to load Live TV feed.")


# ----- Utility Functions -----
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

def get_params():
    param = {}
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else sys.argv[2]
    for pair in paramstring.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            param[key] = value 
    return param

# ----- Parameter Parsing -----
params = get_params()
icon = urllib.parse.unquote(params.get("icon", ""))
url  = urllib.parse.unquote(params.get("url", ""))
name = urllib.parse.unquote_plus(params.get("name", ""))
action = params.get("action", "home")

# ----- Routing -----
ROUTES = {
    # ── General & Core ───────────────────────────────
    "home":                lambda: HOME(),
    "episode_players":     lambda: EPISODE_PLAYERS(url, name, icon),
    "play_direct":         lambda: Play_VIDEO(url),
    "playloop":            lambda: Playloop(url),
    "video_hosting":       lambda: VIDEO_HOSTING(url),
    "videolinks":          lambda: VIDEOLINKS(url),
    "khmer_livetv":        lambda: KHMER_LIVETV(),
    "search":              lambda: SEARCH(),

    # ── iDrama Site (Tvsabay / OneLegend) ─────────────
    "index_idrama":        lambda: idrama.INDEX_IDRAMA(url),
    "sindex_idrama":       lambda: idrama.SINDEX_IDRAMA(url),
    "episode_tvsabay":     lambda: idrama.EPISODE_TVSABAY(url, icon),
    "episode_onelegend":   lambda: idrama.EPISODE_ONELEGEND(url, icon),

    # ── VIP / Craft4U Site ────────────────────────────
    "index_vip":           lambda: vip.INDEX_VIP(url),
    "sindex_vip":          lambda: vip.SINDEX_VIP(url),
    "episode_craft4u":     lambda: vip.EPISODE_CRAFT4U(url, icon),
    "craft4u_play":        lambda: vip.PLAY_CRAFT4U(url, icon),

    # ── CKCH7 Site ───────────────────────────────────
    "index_ckch7":         lambda: ckch7.INDEX_CKCH7(url),
    "sindex_ckch7":        lambda: ckch7.SINDEX_CKCH7(url),
    "episode_ckch7":       lambda: ckch7.EPISODE_CKCH7(url, icon),

    # ── PhumiKhmer2 Site ─────────────────────────────
    "index_phumik":        lambda: phumikhmer.INDEX_PHUMIK(url),
    "sindex_phumik":       lambda: phumikhmer.SINDEX_PHUMIK(url),
    "episode_phumik":      lambda: phumikhmer.EPISODE_PHUMIK(url, icon),

    # ── KhmerAvenue / Merlkon (Generic) ──────────────
    "index_khmeravenue":   lambda: khmerav.INDEX_GENERIC(url, "index_khmeravenue", "khmeravenue"),
    "index_merlkon":       lambda: khmerav.INDEX_GENERIC(url, "index_merlkon", "merlkon"),
    "index_korean":        lambda: khmerav.INDEX_GENERIC(url, "index_korean", "korean"),
    "episode_generic":     lambda: khmerav.EPISODE_GENERIC(url, icon),

    # ── SundayDrama Site ─────────────────────────────
    "index_sunday":        lambda: sunday.INDEX_SUNDAY(url),
    "sindex_sunday":       lambda: sunday.SINDEX_SUNDAY(url),

    # ── FlixHQ Site ───────────────────────
    "genre_menu":          lambda: flixhq.GENRE_MENU(),
    "country_menu":        lambda: flixhq.COUNTRY_MENU(),
    "index_serialgo":      lambda: flixhq.INDEX_SERIALGO(url),
    "search_serialgo":     lambda: flixhq.SEARCH_SERIALGO(),
    "type":                lambda: flixhq.TYPE(url, name),
    "playloop_sg":         lambda: flixhq.PLAYLOOP_SG(url, name),
    "season":              lambda: flixhq.SEASON(url, name),
    "episode":             lambda: flixhq.EPISODE(url, name),
    "server":              lambda: flixhq.SERVER(url, name),
    "play_server":         lambda: flixhq.PLAY_SERVER(url, name),
    
    # ── LookMovie Site ───────────────────────
    "genre_lmenu":         lambda: lookmovie.GENRE_LMENU(),
    "country_lmenu":       lambda: lookmovie.COUNTRY_LMENU(),
    "index_lookm":         lambda: lookmovie.INDEX_LOOKM(url),
    "search_lookm":        lambda: lookmovie.SEARCH_LOOKM() 
}

# ────────────────────────────────────────────────
#  MAIN DISPATCHER
# ────────────────────────────────────────────────

# ----- Execute Action -----
ROUTES.get(action, lambda: HOME())()