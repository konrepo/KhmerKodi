import re
import sys
import base64
import requests
import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import resolveurl

from urllib.parse import quote_plus

from resources.lib.handlers_khmer import OpenURL as OpenURL_KH, OpenSoup as OpenSoup_KH
from resources.lib.handlers_common import USER_AGENT

ADDON_ID = "plugin.video.movie"
ADDON = xbmcaddon.Addon()
PLUGIN_HANDLE = int(sys.argv[1])


def resolve_redirect(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        return r.url
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] Redirect resolve failed: {e}", xbmc.LOGERROR)
        return url


def VIDEOLINKS(url):
    content = str(OpenSoup_KH(url))
    blacklist = ['googletagmanager.com', 'facebook.com', 'twitter.com', 'doubleclick.net']

    def is_blacklisted(link):
        return any(bad in link for bad in blacklist)

    def is_direct_media(link):
        base = link.split("?", 1)[0].lower()
        return base.endswith((".m3u8", ".mp4", ".mov", ".mkv", ".webm", ".aaa.mp4", ".gaa.mp4", ".caa.mp4"))

    def try_base64_iframe():
        matches = re.findall(r'Base64.decode\("(.+?)"\)', content)
        if matches:
            try:
                decoded = base64.b64decode(matches[0]).decode("utf-8", errors="ignore")
                iframe = re.search(r'<iframe[^>]+src="(.+?)"', decoded)
                if iframe:
                    VIDEO_HOSTING(iframe.group(1))
                    return True
            except Exception as e:
                xbmc.log(f"[{ADDON_ID}] Base64 decode failed: {e}", xbmc.LOGWARNING)
        return False

    def try_patterns():
        patterns = [
            r'[\'"]?file[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'"file"\s*:\s*"([^"]+)"',
            r'sources\s*:\s*\[\s*\{file\s*:\s*[\'"]([^\'"]+)[\'"]',
            r'<iframe src="(.+?)" class="video allowfullscreen="true">',
            r'<iframe frameborder="0" [^>]*src="(.+?)">',
            r'<IFRAME SRC="(.+?)" [^>]*',
            r'<div class="video_main">\s*<iframe [^>]*src=["\']?([^>"\']+)["\']?[^>]*>',
            r"var flashvars = {file: '(.+?)',",
            r'swfobject\.embedSWF\("(.+?)",',
            r'src="(.+?)" allow="autoplay"',
            r'<iframe [^>]*src=["\']?([^>"\']+)["\']?[^>]*>',
            r'<source [^>]*src="([^"]+?)"',
            r'playlist: "(.+?)"',
            r'<!\[CDATA\[(.*?)\]\]></tvurl>',
            r'https?://[^\s\'"]+\.(?:m3u8|mp4|mov|mkv|webm)(?:\?[^\s\'"]*)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.I)
            for link in matches:
                link = (link or "").strip()
                if not link or is_blacklisted(link):
                    continue

                if is_direct_media(link):
                    Play_VIDEO(link)
                else:
                    VIDEO_HOSTING(link)
                return True
        return False

    if try_base64_iframe() or try_patterns():
        return

    xbmc.log(f"[{ADDON_ID}] No video URL found in VIDEOLINKS()", xbmc.LOGWARNING)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


def enable_inputstream_adaptive():
    try:
        addon_id = "inputstream.adaptive"

        if not xbmc.getCondVisibility(f"System.HasAddon({addon_id})"):
            xbmc.log(f"[{ADDON_ID}] Installing {addon_id}...", xbmc.LOGINFO)
            xbmc.executebuiltin(f"InstallAddon({addon_id})")

        if not xbmc.getCondVisibility(f"System.AddonIsEnabled({addon_id})"):
            xbmc.log(f"[{ADDON_ID}] Enabling {addon_id}...", xbmc.LOGINFO)
            xbmc.executebuiltin(f"EnableAddon({addon_id})")

    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] Failed to enable {addon_id}: {e}", xbmc.LOGWARNING)


def Playloop(video_url):
    xbmc.log(f"[{ADDON_ID}] PLAY VIDEO: {video_url}", xbmc.LOGINFO)

    headers_dict = {
        "verifypeer": "false",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/90 Safari/537.36",
        "Referer": "https://live-ali7.tv360.metfone.com.kh/",
    }
    headers = "&".join(f"{k}={quote_plus(v)}" for k, v in headers_dict.items())
    full_url = f"{video_url}|{headers}"

    item = xbmcgui.ListItem(path=full_url)
    item.setMimeType("application/vnd.apple.mpegurl")
    item.setContentLookup(False)
    item.setProperty("inputstream", "inputstream.adaptive")
    item.setProperty("inputstream.adaptive.stream_selection_type", "adaptive")
    item.setProperty("inputstream.adaptive.heuristicstreamselection", "true")

    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)


def VIDEO_HOSTING(vlink):
    resolved = None
    base_url = vlink.split("?", 1)[0].lower()

    if base_url.endswith((".m3u8", ".mp4", ".mov", ".mkv", ".webm", ".aaa.mp4", ".gaa.mp4", ".caa.mp4")):
        xbmc.log(f"[{ADDON_ID}] Direct media sent to VIDEO_HOSTING, forwarding to Play_VIDEO: {vlink}", xbmc.LOGINFO)
        Play_VIDEO(vlink)
        return

    if "play.cat3movie.club/embed/" in vlink:
        try:
            html = OpenURL_KH(vlink, as_text=True)
            if html:
                m = re.search(r'url:\s*"(https://play\.cat3movie\.club/api/\?[^"]+)"', html, re.I)
                if m:
                    api_url = m.group(1).replace("&amp;", "&")
                    xbmc.log(f"[{ADDON_ID}] Cat3Movie API URL: {api_url}", xbmc.LOGINFO)

                    res = requests.get(
                        api_url,
                        headers={
                            "User-Agent": USER_AGENT,
                            "Referer": vlink,
                        },
                        timeout=15
                    )

                    data = res.json() if res.ok else {}
                    if data.get("status") == "ok":
                        sources = data.get("sources") or []
                        if sources:
                            first = (sources[0].get("file") or "").strip()
                            if first:
                                xbmc.log(f"[{ADDON_ID}] Cat3Movie resolved source: {first}", xbmc.LOGINFO)
                                Play_VIDEO(first)
                                return
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] Cat3Movie embed resolve failed: {e}", xbmc.LOGWARNING)

    resolvable_hosts = (
        "ok.ru",
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "vimeo.com",
        "dailymotion.com",
        "playhydrax.com",
    )

    if any(host in vlink for host in resolvable_hosts):
        try:
            resolved = resolveurl.resolve(vlink)
            if resolved:
                xbmc.log(f"[{ADDON_ID}] Resolved URL via resolveurl: {resolved}", xbmc.LOGINFO)
                Play_VIDEO(resolved)
                return
            xbmc.log(f"[{ADDON_ID}] resolveurl returned None for: {vlink}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] resolveurl error for {vlink}: {e}", xbmc.LOGWARNING)

    if "drive.google.com" in vlink or "docs.google.com/file/" in vlink:
        try:
            resolved = resolveurl.resolve(vlink)
            if resolved:
                xbmc.log(f"[{ADDON_ID}] Resolved Google Drive via resolveurl: {resolved}", xbmc.LOGINFO)
                Play_VIDEO(resolved)
                return
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] resolveurl error on Google Drive: {e}", xbmc.LOGWARNING)

    xbmc.log(f"[{ADDON_ID}] Fallback to Play_VIDEO(): {vlink}", xbmc.LOGINFO)
    xbmc.executebuiltin("Notification(Please Wait!, Cat3Movie is loading...)")
    Play_VIDEO(vlink)


def Play_VIDEO(VideoURL):
    if not VideoURL:
        xbmcgui.Dialog().ok("Playback Error", "No video URL provided.")
        xbmc.log(f"[{ADDON_ID}] Empty video URL passed to Play_VIDEO()", xbmc.LOGWARNING)
        return

    xbmc.log(f"[{ADDON_ID}] Playing video: {VideoURL}", xbmc.LOGINFO)

    if VideoURL.startswith("plugin://"):
        item = xbmcgui.ListItem(path=VideoURL)
        item.setInfo(type="Video", infoLabels={"title": "Playing..."})
        xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
        return

    if "|" in VideoURL:
        VideoURL, header_str = VideoURL.split("|", 1)
        header_parts = header_str.split("|")
        headers = dict(part.split("=", 1) for part in header_parts if "=" in part)
    else:
        headers = {}

    video_url_lower = VideoURL.lower()
    referer = headers.get("Referer", "")

    if not referer:
        if "cat3movie.club" in video_url_lower or "playhydrax.com" in video_url_lower:
            referer = "https://www.cat3movie.club/"
        elif "sooplive.co.kr" in video_url_lower or "afreeca" in video_url_lower:
            referer = "https://www.cat3movie.club/"
        else:
            referer = "https://www.cat3movie.club/"

    headers.setdefault("Referer", referer)
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    if "ok.ru" in VideoURL:
        try:
            resolved = resolveurl.resolve(VideoURL)
            if resolved:
                xbmc.log(f"[{ADDON_ID}] OK.ru resolved via resolveurl: {resolved}", xbmc.LOGINFO)
                VideoURL = resolved
            else:
                xbmc.log(f"[{ADDON_ID}] OK.ru could not be resolved via resolveurl", xbmc.LOGERROR)
        except Exception as e:
            xbmc.log(f"[{ADDON_ID}] resolveurl failed for OK.ru: {e}", xbmc.LOGERROR)

    if any(x in VideoURL.lower() for x in ["okcdn.ru", "vkuseraudio.net", "okcdn.video"]):
        xbmc.log(f"[{ADDON_ID}] OK.ru CDN link already playable", xbmc.LOGINFO)
        item = xbmcgui.ListItem(path=VideoURL)
        item.setInfo(type="Video", infoLabels={"title": "Playing..."})
        xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
        return

    header_string = "&".join([f"{k}={v}" for k, v in headers.items()])
    final_url = f"{VideoURL}|{header_string}"

    xbmc.log(f"[{ADDON_ID}] Final Play URL: {final_url}", xbmc.LOGINFO)

    item = xbmcgui.ListItem(path=final_url)
    item.setInfo(type="Video", infoLabels={"title": "Playing..."})
    item.setContentLookup(False)

    if ".m3u8" in VideoURL or "manifest" in VideoURL:
        item.setMimeType("application/vnd.apple.mpegurl")
        item.setProperty("inputstream", "inputstream.ffmpegdirect")
        item.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "false")
        item.setProperty("inputstream.ffmpegdirect.stream_mode", "timeshift")
    else:
        item.setMimeType("video/mp4")

    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)


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
    xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=u, listitem=li, isFolder=False)