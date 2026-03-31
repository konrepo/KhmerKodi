# ── Compatibility & Imports ─────────────────────────────────────
import os
import sys
import urllib.parse
from urllib.parse import quote_plus

# ── Kodi Modules ────────────────────────────────────────────────
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

# ── Cat3Movie Module ────────────────────────────────────────────
from resources.lib import cat3movie

# ── Playback Handlers ───────────────────────────────────────────
from resources.lib.handlers_playback import (
    VIDEOLINKS,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)

# ── Logging Helper ──────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)


# ── Add-on Constants ────────────────────────────────────────────
ADDON_ID      = 'plugin.video.movie'
ADDON         = xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH    = ADDON.getAddonInfo('path')
DATA_PATH     = xbmcvfs.translatePath(f'special://profile/addon_data/{ADDON_ID}')
PLUGIN_HANDLE = int(sys.argv[1])


# ── Base URL ────────────────────────────────────────────────────
CAT3MOVIE = 'https://www.cat3movie.club/'


# ── Icons and Fanart ────────────────────────────────────────────
IMAGE_PATH     = os.path.join(ADDON_PATH, 'resources', 'images')
ICON_CAT3MOVIE = os.path.join(IMAGE_PATH, 'cat3movie.png')
FANART         = os.path.join(IMAGE_PATH, 'fanart.jpg')


# ── Main Menu ──────────────────────────────────────────────────
def HOME():
    addDir("Cat3Movie", CAT3MOVIE, "index_cat3movie", ICON_CAT3MOVIE)
    addDir("[COLOR yellow][B][I]SEARCH[/I][/B][/COLOR]", CAT3MOVIE, "search_cat3movie", ICON_CAT3MOVIE)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ── Search ─────────────────────────────────────────────────────
def SEARCH_CAT3MOVIE():
    kb = xbmc.Keyboard('', 'Enter Search Text')
    kb.doModal()
    if not kb.isConfirmed():
        return

    query = kb.getText().strip()
    if not query:
        return

    try:
        cat3movie.SINDEX_CAT3MOVIE(
            f'{cat3movie.CAT3MOVIE}?s={quote_plus(query)}',
            end_directory=False
        )
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] Search failed for CAT3MOVIE: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "Search Error",
            "Cat3Movie search failed. Check log.",
            xbmcgui.NOTIFICATION_ERROR
        )

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ── Utility Functions ──────────────────────────────────────────
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

    xbmcplugin.addDirectoryItem(
        handle=PLUGIN_HANDLE,
        url=u,
        listitem=li,
        isFolder=True
    )


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

    xbmcplugin.addDirectoryItem(
        handle=PLUGIN_HANDLE,
        url=u,
        listitem=li,
        isFolder=False
    )


def get_params():
    param = {}
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else sys.argv[2]

    for pair in paramstring.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            param[key] = value

    return param


# ── Parameter Parsing ──────────────────────────────────────────
params = get_params()
icon   = urllib.parse.unquote(params.get("icon", ""))
url    = urllib.parse.unquote(params.get("url", ""))
name   = urllib.parse.unquote_plus(params.get("name", ""))
action = params.get("action", "home")


# ── Routing ────────────────────────────────────────────────────
ROUTES = {
    # Main
    "home":               lambda: HOME(),
    "search_cat3movie":   lambda: SEARCH_CAT3MOVIE(),

    # Cat3Movie
    "index_cat3movie":    lambda: cat3movie.INDEX_CAT3MOVIE(url),
    "sindex_cat3movie":   lambda: cat3movie.SINDEX_CAT3MOVIE(url),
    "episode_cat3movie":  lambda: cat3movie.EPISODE_CAT3MOVIE(url, icon),

    # Playback used by cat3movie.py
    "play_direct":        lambda: Play_VIDEO(url),
    "playloop":           lambda: Playloop(url),
    "video_hosting":      lambda: VIDEO_HOSTING(url),
    "videolinks":         lambda: VIDEOLINKS(url),
}


# ── Execute Action ─────────────────────────────────────────────
ROUTES.get(action, lambda: HOME())()