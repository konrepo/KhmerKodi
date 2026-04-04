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

# ── Site Modules ────────────────────────────────────────────────
from resources.lib import cat3movie, xvideos

# ── Playback Handlers ───────────────────────────────────────────
from resources.lib.handlers_playback import (
    VIDEOLINKS,
    Playloop,
    VIDEO_HOSTING,
    Play_VIDEO,
)

# ── Add-on Constants ────────────────────────────────────────────
ADDON_ID      = "plugin.video.movie"
ADDON         = xbmcaddon.Addon(id=ADDON_ID)
ADDON_PATH    = ADDON.getAddonInfo("path")
DATA_PATH     = xbmcvfs.translatePath(f"special://profile/addon_data/{ADDON_ID}")
PLUGIN_HANDLE = int(sys.argv[1])

# ── Logging Helper ──────────────────────────────────────────────
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

# ── Base URL ────────────────────────────────────────────────────
CAT3MOVIE = "https://www.cat3movie.club/"
XVIDEOS   = "https://www.xvideos.com/"

# ── Icons and Fanart ────────────────────────────────────────────
IMAGE_PATH     = os.path.join(ADDON_PATH, "resources", "images")
ICON_CAT3MOVIE = os.path.join(IMAGE_PATH, "cat3movie.png")
ICON_XVIDEOS   = os.path.join(IMAGE_PATH, "xvideos.png")
ICON_SEARCH    = os.path.join(IMAGE_PATH, "search.png")
FANART         = os.path.join(IMAGE_PATH, "fanart.jpg")


# ── Main Menu ──────────────────────────────────────────────────
def HOME():
    addDir("Search", "", "search", ICON_SEARCH)
    addDir("Cat3Movie", CAT3MOVIE, "index_cat3movie", ICON_CAT3MOVIE)
    addDir("xVideos", XVIDEOS, "index_xvideos", ICON_XVIDEOS)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ── Search ─────────────────────────────────────────────────────
def SEARCH():
    kb = xbmc.Keyboard("", "Enter Search Text")
    kb.doModal()
    if not kb.isConfirmed():
        return

    query = kb.getText().strip()
    if not query:
        return

    errors = []

    # Cat3Movie
    try:
        addDir("[B][COLOR gold]----- Cat3Movie -----[/COLOR][/B]", "", "noop", ICON_CAT3MOVIE)
        cat3movie.SINDEX_CAT3MOVIE(
            f"{CAT3MOVIE}?s={quote_plus(query)}",
            end_directory=False
        )
    except Exception as e:
        errors.append(f"Cat3Movie: {e}")
        log(f"Search failed for Cat3Movie: {e}", xbmc.LOGERROR)

    # xVideos
    try:
        addDir("[B][COLOR deepskyblue]----- xVideos -----[/COLOR][/B]", "", "noop", ICON_XVIDEOS)
        xvideos.SINDEX_XVIDEOS(
            f"{XVIDEOS}?k={quote_plus(query)}",
            end_directory=False
        )
    except Exception as e:
        errors.append(f"xVideos: {e}")
        log(f"Search failed for xVideos: {e}", xbmc.LOGERROR)

    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    if errors:
        xbmcgui.Dialog().notification(
            "Search Warning",
            f"{len(errors)} source(s) failed. Check log.",
            xbmcgui.NOTIFICATION_WARNING
        )


# ── Utility Functions ──────────────────────────────────────────
def addDir(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        "thumb": iconimage,
        "icon": iconimage,
        "poster": iconimage,
        "landscape": iconimage,
        "fanart": iconimage,
        "banner": iconimage,
    })

    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setInfo("video", {"title": name})

    if action == "noop":
        xbmcplugin.addDirectoryItem(
            handle=PLUGIN_HANDLE,
            url=f"{sys.argv[0]}?action=noop",
            listitem=li,
            isFolder=False
        )
        return

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
        "thumb": iconimage,
        "icon": iconimage,
        "poster": iconimage,
        "landscape": iconimage,
        "fanart": iconimage,
        "banner": iconimage,
    })

    if iconimage:
        li.setProperty("Fanart_Image", iconimage)

    li.setProperty("IsPlayable", "true")
    li.setInfo("video", {"title": name})

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


def addLink(name, url, action, iconimage=""):
    li = xbmcgui.ListItem(label=name)
    li.setArt({
        "thumb": iconimage,
        "icon": iconimage,
        "poster": iconimage,
        "landscape": iconimage,
        "fanart": FANART,
        "banner": iconimage,
    })

    li.setProperty("Fanart_Image", FANART)
    li.setProperty("IsPlayable", "true")
    li.setInfo("video", {"title": name})

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
    paramstring = sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith("?") else sys.argv[2]

    for pair in paramstring.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            param[key] = value

    return param


# ── Parameter Parsing ──────────────────────────────────────────
params = get_params()
icon   = urllib.parse.unquote_plus(params.get("icon", ""))
url    = urllib.parse.unquote_plus(params.get("url", ""))
name   = urllib.parse.unquote_plus(params.get("name", ""))
action = urllib.parse.unquote_plus(params.get("action", "home"))


# ── Routing ────────────────────────────────────────────────────
ROUTES = {
    # Main
    "home":               lambda: HOME(),
    "search":             lambda: SEARCH(),
    "noop":               lambda: None,

    # Cat3Movie
    "index_cat3movie":    lambda: cat3movie.INDEX_CAT3MOVIE(url),
    "sindex_cat3movie":   lambda: cat3movie.SINDEX_CAT3MOVIE(url),
    "episode_cat3movie":  lambda: cat3movie.EPISODE_CAT3MOVIE(url, icon),

    # xVideos
    "index_xvideos":      lambda: xvideos.INDEX_XVIDEOS(url),
    "sindex_xvideos":     lambda: xvideos.SINDEX_XVIDEOS(url),
    "episode_xvideos":    lambda: xvideos.EPISODE_XVIDEOS(url, icon),

    # Playback
    "play_direct":        lambda: Play_VIDEO(url),
    "playloop":           lambda: Playloop(url),
    "video_hosting":      lambda: VIDEO_HOSTING(url),
    "videolinks":         lambda: VIDEOLINKS(url),
}


# ── Execute Action ─────────────────────────────────────────────
ROUTES.get(action, HOME)()