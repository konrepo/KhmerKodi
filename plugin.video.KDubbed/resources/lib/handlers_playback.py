import re, sys, json, base64, requests, xbmc, xbmcaddon, xbmcplugin, xbmcgui, resolveurl, urllib.request, urllib.error
from urllib.parse import urlparse, quote_plus, urljoin
from html import unescape as html_unescape
from bs4 import BeautifulSoup

# ── Base networking utils ────────────────
from resources.lib.handlers_khmer import OpenURL as OpenURL_KH, OpenSoup as OpenSoup_KH
from resources.lib.handlers_common import USER_AGENT

# ── Shared Blogger utilities ─────────────
from resources.lib.handlers_blogid import (
    ADDON_ID,
    is_vip_url,
    is_idrama_url,
    extract_vip_blogger_json_urls_from_page,
    extract_all_blogger_json_urls_from_page,
    parse_blogger_video_links,
    parse_blogger_video_links_script,
)
try:
    ADDON_ID
except NameError:
    ADDON_ID = "plugin.video.KDubbed"

# ── UI helpers ───────────────────────────
ADDON = xbmcaddon.Addon()
PLUGIN_HANDLE = int(sys.argv[1])


def EPISODE_PLAYERS(url, name, icon=""):
    from resources.lib import idrama, vip, ckch7, phumikhmer, khmerav, video4khmer, sunday
    from resources.lib.video4khmer import VIDEO4KHMER

    EPISODE_TVSABAY     = getattr(idrama, "EPISODE_TVSABAY", None)
    EPISODE_ONELEGEND   = getattr(idrama, "EPISODE_ONELEGEND", None)
    EPISODE_CRAFT4U     = getattr(vip, "EPISODE_CRAFT4U", None)
    EPISODE_CKCH7       = getattr(ckch7, "EPISODE_CKCH7", None)
    EPISODE_PHUMIK      = getattr(phumikhmer, "EPISODE_PHUMIK", None)
    EPISODE_GENERIC     = getattr(khmerav, "EPISODE_GENERIC", None)
    EPISODE_VIDEO4KHMER = getattr(video4khmer, "EPISODE_VIDEO4KHMER", None)
    EPISODE_SUNDAY      = getattr(sunday, "EPISODE_SUNDAY", None)

    if not url:
        xbmc.log(f"[{ADDON_ID}] Empty URL passed to EPISODE_PLAYERS", xbmc.LOGERROR)
        return

    def fetch_decoded(u, as_text=False):
        h = OpenURL_KH(u, as_text=as_text)
        return h.decode("utf-8", errors="ignore") if isinstance(h, bytes) else h

    def no_eps(msg="No playable episodes found."):
        xbmcgui.Dialog().ok("No Episodes Found", msg)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    def sort_by_num(items, key=lambda x: x[1]):
        def num(it):
            m = re.search(r'\b(?:Ep(?:isode)?|Part)\s*(\d+)\b', key(it), re.I)
            return int(m.group(1)) if m else 0
        return sorted(items, key=num)

    SITE_HANDLERS = {
        "tvsabay.com": EPISODE_TVSABAY,
        "craft4u.top": EPISODE_CRAFT4U,
        "onelegend.asia": EPISODE_ONELEGEND,
        "ckh7.com": EPISODE_CKCH7,
        "phumikhmer1.club": EPISODE_PHUMIK,
        "khmeravenue.com": lambda u, i="": EPISODE_GENERIC(u, i, site_name="khmerave/merlkon"),
        "khmerdrama.com": lambda u, i="": EPISODE_GENERIC(u, i, site_name="khmerave/merlkon"),
        VIDEO4KHMER: EPISODE_VIDEO4KHMER,
    }

    PASS_ICON_DOMAINS = (
        "tvsabay.com",
        "onelegend.asia",
        "phumikhmer.vip",
        "phumikhmer1.club",
        "sundaydrama.com",
        "khmeravenue.com",
        "khmerdrama.com",
        "ckh7.com",
        "idramahd.com",
    )

    for k, fn in SITE_HANDLERS.items():
        if k in url:
            xbmc.log(f"[{ADDON_ID}] Detected {k}: {url}", xbmc.LOGINFO)
            if any(domain in url for domain in PASS_ICON_DOMAINS):
                return fn(url, icon)
            return fn(url)

    html = fetch_decoded(url, as_text=True)
    if not html:
        xbmc.log(f"[{ADDON_ID}] Failed to fetch page for: {url}", xbmc.LOGERROR)
        return

    for pattern, fn in {
        r'href="(https://www\.tvsabay\.com/[^"]+)":': EPISODE_TVSABAY,
        r'href="(https://www\.craft4u\.top/[^"]+)":': EPISODE_CRAFT4U,
        r'(https://onelegend\.asia/[^"\']+)': EPISODE_ONELEGEND
    }.items():
        m = re.search(pattern, html, re.I)
        if m:
            u = m.group(1)
            xbmc.log(f"[{ADDON_ID}] Redirecting: {u}", xbmc.LOGINFO)
            if fn in (EPISODE_TVSABAY, EPISODE_ONELEGEND):
                return fn(u, icon)
            return fn(u)

    # ── VIDEO4KHMER episode listing ─────────────────────────
    if VIDEO4KHMER in url:
        decoded = fetch_decoded(url, as_text=True)
        if ADDON.getSetting("summary_url") != url:
            m = re.search(r'<h2 class="h3">Summary:</h2>\s*<p class="justified-text">(.*?)</p>', decoded, re.S | re.I)
            if m:
                try:
                    s = re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', '\n', m.group(1))).strip()
                    xbmcgui.Dialog().textviewer("Summary", s)
                    ADDON.setSetting("summary_url", url)
                except Exception as e:
                    xbmc.log(f"[{ADDON_ID}] Summary popup failed: {e}", xbmc.LOGWARNING)

        soup, eps = BeautifulSoup(decoded, "html.parser"), {}
        for tr in soup.select("#episode-list tbody tr"):
            td, a = tr.find("td"), tr.find("a")
            if not td: continue
            title, link = (a.get_text(strip=True), a["href"]) if a else (td.get_text(strip=True), url)
            m = re.search(r'(\d+)', title)
            if m and int(m.group(1)) not in eps:
                eps[int(m.group(1))] = (title, link)
        for _, (t, l) in sorted(eps.items()):
            addLink(t, l, "videolinks", icon)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # ── SUNDAYDRAMA handler ─────────────────────────────────
    if "sundaydrama.com" in url:
        html = fetch_decoded(url, as_text=True)
        blogger_urls = extract_all_blogger_json_urls_from_page(html)
        if "fetchBloggerPostContent({" in html and "{embed=ok}" in html:
            m = re.search(r'"content":\{"type":"html","\$t":"([^"]+)"\}', html)
            if m:
                content = html_unescape(m.group(1))
                ids = re.findall(r"\d{10,}", content)
                if ids:
                    for i, vid in enumerate(ids, 1):
                        addLink(f"Episode {i:02d}", f"https://ok.ru/videoembed/{vid}", "video_hosting", icon)
                    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
                    return
        all_links, c = [], 1

        for bu in blogger_urls:
            eps = parse_blogger_video_links(bu) or []
            if not eps:
                continue

            # Detect if this Blogger post contains sooplive streams
            has_sooplive = any("sooplive.co.kr" in e['file'] for e in eps)

            for l in eps:
                v = l.get("file", "").strip()

                # If this post has sooplive, only select sooplive HLS
                if has_sooplive:
                    if "sooplive.co.kr" not in v:
                        continue
                    if not v.endswith("manifest.m3u8") and ".m3u8" not in v:
                        continue

                # Prevent duplicates
                if any(v == x["file"] for x in all_links):
                    continue

                l["title"] = f"Episode {c}"
                all_links.append(l)
                c += 1


        if not all_links: return no_eps("No Blogger posts found.")
        DIRECT_EXT = (".mp4", ".m3u8", ".aaa.mp4", ".gaa.mp4", ".caa.mp4")
        for it in all_links:
            vurl, vtitle = it['file'], it['title']
            if any(h in vurl for h in ["ok.ru", "youtube.com", "youtu.be", "vimeo.com"]):
                addLink(vtitle, vurl, "video_hosting", icon)
            elif any(vurl.split('?')[0].endswith(ext) for ext in DIRECT_EXT):
                addLink(vtitle, vurl, "play_direct", icon)
            else:
                addLink(vtitle, vurl, "video_hosting", icon)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # ── VIP / iDrama ─────────────────────────────────────────
    if is_vip_url(url) or is_idrama_url(url):
        decoded = fetch_decoded(url, as_text=True)

        def extract_max_ep(text):
            if not text:
                return None
            text = str(text)
            patterns = [
                r'\[\s*EP\s*(\d+)\s*(?:END)?\s*\]',
                r'\bEP\s*(\d+)\b',
                r'\bEpisode\s*(\d+)\b',
            ]
            for pat in patterns:
                m = re.search(pat, text, re.I)
                if m:
                    try:
                        return int(m.group(1))
                    except Exception:
                        pass
            return None

        def is_better_source(new_url, old_url):
            def score(u):
                u = (u or "").lower()
                return (
                    4 if ".m3u8" in u else
                    3 if u.split('?', 1)[0].endswith((".mp4", ".aaa.mp4", ".gaa.mp4", ".caa.mp4")) else
                    2 if any(h in u for h in ("ok.ru", "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")) else
                    1
                )
            return score(new_url) > score(old_url)

        # get correct max episode from page title / og:title
        page_title = ""
        m = re.search(r"<title>(.*?)</title>", decoded, re.I | re.S)
        if m:
            page_title = html_unescape(m.group(1)).strip()

        if not page_title:
            m = re.search(
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
                decoded, re.I
            )
            if m:
                page_title = html_unescape(m.group(1)).strip()

        max_ep = extract_max_ep(page_title)
        xbmc.log(f"[{ADDON_ID}] VIP page title: {page_title} | max_ep={max_ep}", xbmc.LOGINFO)

        blogger_urls = extract_vip_blogger_json_urls_from_page(decoded)

        if not blogger_urls:
            craft = re.search(
                r'href=["\']?(https?://(?:t\.co|(?:www\.)?(craft4u\.top|tvsabay\.com))/[^"\']+)',
                decoded, re.I
            )
            if craft:
                craft_url = craft.group(1)
                if "t.co" in craft_url:
                    try:
                        craft_url = requests.head(craft_url, allow_redirects=True, timeout=5).url
                    except Exception as e:
                        return no_eps(f"Failed to resolve t.co link: {e}")

                for domain, fn in [("tvsabay.com", EPISODE_TVSABAY), ("onelegend.asia", EPISODE_ONELEGEND)]:
                    if domain in craft_url:
                        return fn(craft_url, icon)

                return EPISODE_CRAFT4U(craft_url)

            return no_eps("No blogger feeds were found on this VIP page.")

        # collect in feed order, dedupe, keep one best source per URL
        ordered_links = []
        seen_urls = set()

        for bu in blogger_urls:
            links = parse_blogger_video_links(bu) or []
            if not links:
                links = parse_blogger_video_links_script(bu) or []

            xbmc.log(f"[{ADDON_ID}] VIP feed {bu} -> {len(links)} links", xbmc.LOGINFO)

            for l in links:
                vurl = l.get("file", "").strip()
                if not vurl:
                    continue

                if vurl in seen_urls:
                    continue

                seen_urls.add(vurl)
                ordered_links.append(vurl)

        if not ordered_links:
            return no_eps("No playable episodes found on this VIP page.")

        # remove extra mirrors/overflow using title max episode count
        if max_ep and len(ordered_links) > max_ep:
            xbmc.log(
                f"[{ADDON_ID}] VIP trimming links from {len(ordered_links)} to max_ep={max_ep}",
                xbmc.LOGINFO
            )
            ordered_links = ordered_links[:max_ep]

        # final display numbering should follow preserved order
        for i, vurl in enumerate(ordered_links, 1):
            vtitle = f"Episode {i}"

            if any(h in vurl for h in ("ok.ru", "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")):
                addLink(vtitle, vurl, "video_hosting", icon)
            elif any(vurl.split('?', 1)[0].endswith(ext) for ext in (".mp4", ".m3u8", ".aaa.mp4", ".gaa.mp4", ".caa.mp4")):
                addLink(vtitle, vurl, "play_direct", icon)
            else:
                addLink(vtitle, vurl, "video_hosting", icon)

        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # ── Blogger JSON direct ──────────────────────────────────
    if "blogger.com/feeds/" in url:
        bl = parse_blogger_video_links(url)
        if not bl: return no_eps("No playable episodes found in Blogger feed.")
        for it in bl: addLink(it['title'], it['file'], "play_direct", icon)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)
        return

    # ── Generic HTML episode list ────────────────────────────
    decoded = fetch_decoded(url)

    def show_about():
        if ADDON.getSetting("about_url") == url: return
        m = re.search(r'id=["\']about["\'].*?album-content-description["\'][^>]*>(.*?)</p>', decoded, re.S | re.I)
        if m:
            try:
                xbmcgui.Dialog().textviewer("About", re.sub(r'\s+', ' ', re.sub(r'<br\s*/?>', '\n', m.group(1))).strip())
                ADDON.setSetting("about_url", url)
            except Exception as e:
                xbmc.log(f"[{ADDON_ID}] About popup failed: {e}", xbmc.LOGWARNING)

    def get_submitter():
        m = re.search(r'Submitter:\s*<b[^>]*>([^<]+)</b>', decoded, re.I)
        return m.group(1).strip() if m else ""

    def parse_table():
        t = re.search(r'<table id="latest-videos"[^>]*>(.*?)</table>', decoded, re.S)
        return re.findall(r'<td>\s*<a href="([^"]+)".*?>(?:<i[^>]*></i>)?\s*([^<]+)\s*</a>', t.group(1)) if t else \
               re.findall(r'<div class="col[^>]*>.*?<a href="([^"]+)".*?>(?:<i[^>]*></i>)?\s*([^<]+)</a>', decoded, re.S)

    show_about()
    subm = get_submitter()
    eps = sort_by_num(parse_table())
    found = False
    for i, (v_link, _) in enumerate(eps, 1):
        v_title = f"Episode {i}"
        if subm: v_title += f" [COLOR grey](by {subm})[/COLOR]"
        addLink(v_title, urljoin(url, v_link), "videolinks", icon)
        found = True

    if not found:
        for func in (try_player_list_json, try_player_list_eval, try_videos_list_const, try_fallback_player_list):
            player_list = func()
            if player_list: break
        if player_list:
            player_list = sort_by_num(player_list, key=lambda x: x.get("title", ""))
            for i, it in enumerate(player_list, 1):
                try:
                    v_link = it.get('file', '').strip()
                    if not v_link: continue
                    v_title = f"Episode {i}" + (f" [COLOR grey](by {subm})[/COLOR]" if subm else "")
                    mode = "play_direct" if ("1a-1791.com" in v_link or v_link.endswith(".aaa.mp4") or any(d in v_link for d in ["ckh7.com", "sundaydrama.com"])) else "video_hosting"
                    addLink(v_title, v_link, mode, icon)
                    found = True
                except Exception as e:
                    xbmc.log(f"[{ADDON_ID}] Failed to parse item: {e}", xbmc.LOGWARNING)
    if not found:
        xbmc.log(f"[{ADDON_ID}] No episode links found at: {url}", xbmc.LOGWARNING)
        no_eps()


def resolve_redirect(url): # Craft4u
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)
        return r.url
    except Exception as e:
        xbmc.log(f"[{ADDON_ID}] Redirect resolve failed: {e}", xbmc.LOGERROR)
        return url

def VIDEOLINKS(url):
    content = str(OpenSoup_KH(url))  # Ensure string format
    blacklist = ['googletagmanager.com', 'facebook.com', 'twitter.com', 'doubleclick.net']

    def is_blacklisted(link):
        return any(bad in link for bad in blacklist)

    def try_base64_iframe():
        matches = re.findall(r'Base64.decode\("(.+?)"\)', content)
        if matches:
            try:
                decoded = base64.b64decode(matches[0]).decode('utf-8', errors='ignore')
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
            r'<iframe src="(.+?)" class="video allowfullscreen="true">',
            r'<iframe frameborder="0" [^>]*src="(.+?)">',
            r'<IFRAME SRC="(.+?)" [^>]*',
            r'<div class="video_main">\s*<iframe [^>]*src=["\']?([^>^"^\']+)["\']?[^>]*>',
            r"var flashvars = {file: '(.+?)',",
            r'swfobject\.embedSWF\("(.+?)",',
            r'src="(.+?)" allow="autoplay"',
            r'<iframe [^>]*src=["\']?([^>^"^\']+)["\']?[^>]*>',
            r'<source [^>]*src="([^"]+?)"',
            r'playlist: "(.+?)"',
            r'<!\[CDATA\[(.*?)\]\]></tvurl>'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for url in matches:
                if not is_blacklisted(url):
                    VIDEO_HOSTING(url)
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
            xbmc.log(f"[KDUBBED] Installing {addon_id}...", xbmc.LOGINFO)
            xbmc.executebuiltin(f"InstallAddon({addon_id})")

        if not xbmc.getCondVisibility(f"System.AddonIsEnabled({addon_id})"):
            xbmc.log(f"[KDUBBED] Enabling {addon_id}...", xbmc.LOGINFO)
            xbmc.executebuiltin(f"EnableAddon({addon_id})")

    except Exception as e:
        xbmc.log(f"[KDUBBED] Failed to enable {addon_id}: {e}", xbmc.LOGWARNING)

def Playloop(video_url):
    xbmc.log(f"[KDUBBED] PLAY VIDEO: {video_url}", xbmc.LOGINFO)

    headers_dict = {
        'verifypeer': 'false',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/90 Safari/537.36',
        'Referer': 'https://live-ali7.tv360.metfone.com.kh/',
    }
    headers = '&'.join(f'{k}={quote_plus(v)}' for k, v in headers_dict.items())
    full_url = f"{video_url}|{headers}"

    item = xbmcgui.ListItem(path=full_url)

    item.setMimeType('application/vnd.apple.mpegurl')
    item.setContentLookup(False)
    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
    item.setProperty('inputstream.adaptive.heuristicstreamselection', 'true')
    
    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)

def VIDEO_HOSTING(vlink):
    resolved = None
    RESOLVABLE_HOSTS = (
        'ok.ru', 'youtube.com', 'youtu.be',
        'youtube-nocookie.com', 'vimeo.com', 'dailymotion.com'
    )

    if any(host in vlink for host in RESOLVABLE_HOSTS):
        try:
            resolved = resolveurl.resolve(vlink)
            if resolved:
                xbmc.log(f"[KDUBBED] Resolved URL via resolveurl: {resolved}", xbmc.LOGINFO)
                Play_VIDEO(resolved)
                return
            else:
                xbmc.log(f"[KDUBBED] resolveurl returned None for: {vlink}", xbmc.LOGWARNING)
        except Exception as e:
            xbmc.log(f"[KDUBBED] resolveurl error for {vlink}: {e}", xbmc.LOGWARNING)

    if "drive.google.com" in vlink or "docs.google.com/file/" in vlink:
        try:
            resolved = resolveurl.resolve(vlink)
            if resolved:
                xbmc.log(f"[KDUBBED] Resolved Google Drive via resolveurl: {resolved}", xbmc.LOGINFO)
                Play_VIDEO(resolved)
                return
        except Exception as e:
            xbmc.log(f"[KDUBBED] resolveurl error on Google Drive: {e}", xbmc.LOGWARNING)

    xbmc.log(f"[KDUBBED] Fallback to Play_VIDEO(): {vlink}", xbmc.LOGINFO)
    xbmc.executebuiltin("Notification(Please Wait!, KhmerDubbed is loading...)")
    Play_VIDEO(vlink)      

def Play_VIDEO(VideoURL):
    if not VideoURL:
        xbmcgui.Dialog().ok("Playback Error", "No video URL provided.")
        xbmc.log("[KDUBBED] Empty video URL passed to Play_VIDEO()", xbmc.LOGWARNING)
        return

    xbmc.log(f"[KDUBBED] Playing video: {VideoURL}", xbmc.LOGINFO)

    if VideoURL.startswith("plugin://"):
        item = xbmcgui.ListItem(path=VideoURL)
        item.setInfo(type="Video", infoLabels={"title": "Playing..."})
        xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
        return

    # Parse embedded headers if any (ckch7/sunday)
    if "|" in VideoURL:
        VideoURL, header_str = VideoURL.split("|", 1)
        header_parts = header_str.split("|")
        headers = dict(part.split("=", 1) for part in header_parts if "=" in part)
    else:
        headers = {}

    # === Automatically Set Proper Referer ===
    referer = headers.get("Referer", "")
    if not referer:
        if "1a-1791.com" in VideoURL:
            # Heuristic fallback: prefer sundaydrama.com if unsure
            referer = "https://sundaydrama.com/" if "sundaydrama.com" in VideoURL else "https://www.ckh7.com/"
        elif "sundaydrama.com" in VideoURL:
            referer = "https://sundaydrama.com/"
        elif "ckh7.com" in VideoURL:
            referer = "https://www.ckh7.com/"
        else:
            referer = "https://www.ckh7.com/"  # Default fallback

    headers.setdefault("Referer", referer)
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    # === Optional: Resolve OK.ru links ===
    if "ok.ru" in VideoURL:
        try:
            resolved = resolveurl.resolve(VideoURL)
            if resolved:
                xbmc.log(f"[KDUBBED] OK.ru resolved via resolveurl: {resolved}", xbmc.LOGINFO)
                VideoURL = resolved
            else:
                xbmc.log("[KDUBBED] OK.ru could not be resolved via resolveurl", xbmc.LOGERROR)
        except Exception as e:
            xbmc.log(f"[KDUBBED] resolveurl failed for OK.ru: {e}", xbmc.LOGERROR)

    # === Skip if already a direct CDN link ===
    if any(x in VideoURL.lower() for x in ["okcdn.ru", "vkuseraudio.net", "okcdn.video"]):
        xbmc.log("[KDUBBED] OK.ru CDN link already playable — skipping header modifications", xbmc.LOGINFO)
        item = xbmcgui.ListItem(path=VideoURL)
        item.setInfo(type="Video", infoLabels={"title": "Playing..."})
        xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
        return

    # === Reconstruct Final URL ===
    header_string = "&".join([f"{k}={v}" for k, v in headers.items()])
    final_url = f"{VideoURL}|{header_string}"

    xbmc.log(f"[KDUBBED] Final Play URL: {final_url}", xbmc.LOGINFO)

    item = xbmcgui.ListItem(path=final_url)
    item.setInfo(type="Video", infoLabels={"title": "Playing..."})
    item.setContentLookup(False)

    # Enable inputstream.ffmpegdirect if applicable
    if ".m3u8" in VideoURL or "manifest" in VideoURL:
        item.setMimeType("application/vnd.apple.mpegurl")
        item.setProperty("inputstream", "inputstream.ffmpegdirect")
        item.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "false")
        item.setProperty("inputstream.ffmpegdirect.stream_mode", "timeshift")
    else:
        item.setMimeType("video/mp4")

    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, item)
    
# ── Basic UI Helpers (avoid circular import) ────────────
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
    