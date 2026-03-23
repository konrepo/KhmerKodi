# ─────────────────────────────────────────────
# handlers_blogid.py
# SundayDrama Blogger ID cache + parser utils
# ─────────────────────────────────────────────

import os, re, json, requests
import xbmc, xbmcvfs
from html import unescape as html_unescape
from urllib.parse import urlparse
from resources.lib.handlers_khmer import OpenURL as OpenURL_KH

# ── Base constants ────────────────────────────
ADDON_ID = "plugin.video.KDubbed"

# define site constants locally to avoid NameError
VIP = "https://phumikhmer.vip/"
IDRAMA = "https://www.idramahd.com/"

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Mobile Safari/537.36"
)


############## use for sundaydrama episode ****************** 
BLOG_ID_CACHE = {}

BLOG_ID_SEEN = set()

BLOG_ID_BASELINE = {
    "2": "7871281676618369095",
    "4": "596013908374331296",
    "5": "3148232187236550259",    
    "":  "3556626157575058125",
} 

ADDON_DATA_PATH = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.KDubbed")
os.makedirs(ADDON_DATA_PATH, exist_ok=True)
BLOG_ID_CACHE_PATH = os.path.join(ADDON_DATA_PATH, "blog_id_cache.json")

def _log(msg, lvl=xbmc.LOGINFO): xbmc.log(f"[KDUBBED] {msg}", lvl)

def _json_io(path, data=None):
    try:
        if data is None:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f)
    except Exception as e:
        _log(f"JSON I/O failed ({path}): {e}", xbmc.LOGWARNING)
    return {}

def load_blog_id_cache_from_disk():
    global BLOG_ID_CACHE, BLOG_ID_SEEN
    data = _json_io(BLOG_ID_CACHE_PATH)
    BLOG_ID_CACHE = data.get("map", {})
    BLOG_ID_SEEN = set(data.get("seen", []))
    _log(f"Loaded BLOG_ID_CACHE: {BLOG_ID_CACHE}")

def save_blog_id_cache_to_disk():
    _json_io(BLOG_ID_CACHE_PATH, {"map": BLOG_ID_CACHE, "seen": list(BLOG_ID_SEEN)})
    _log("Saved BLOG_ID_CACHE.", xbmc.LOGDEBUG)

load_blog_id_cache_from_disk()

def _learn_mapping(server_index, blog_id, src="unknown"):
    prev = BLOG_ID_CACHE.get(server_index)
    if prev != blog_id:
        BLOG_ID_CACHE[server_index] = blog_id
        _log(f"Learned blog_id mapping: {server_index} -> {blog_id} (src={src}, prev={prev})")
        save_blog_id_cache_to_disk()
    if blog_id not in BLOG_ID_SEEN:
        BLOG_ID_SEEN.add(blog_id)
        save_blog_id_cache_to_disk()

def extract_blog_id_mapping_from_scripts(html):
    mapping = {}
    for blog_id, post_id in re.findall(r'src=["\']https://www\.blogger\.com/feeds/(\d+)/posts/default/(\d+)\?alt=json-in-script', html):
        BLOG_ID_SEEN.add(blog_id)
        m = re.search(fr'data-post-id=["\']{post_id}["\'][^>]*data-server-index=["\']?(\d*)', html)
        if m:
            sid = m.group(1) or ""
            mapping[sid] = blog_id
            _learn_mapping(sid, blog_id, "script-tag")
    if mapping: save_blog_id_cache_to_disk()
    return mapping

def _get_blog_id_for_server_index(sid):
    if sid in BLOG_ID_CACHE: return BLOG_ID_CACHE[sid]
    if sid in BLOG_ID_BASELINE:
        bid = BLOG_ID_BASELINE[sid]; _learn_mapping(sid, bid, "baseline"); return bid
    return None
    
def extract_all_blogger_json_urls_from_page(html):
    extract_blog_id_mapping_from_scripts(html)
    urls = []

    # Find all fanta blocks
    blocks = re.findall(
        r'<[^>]*id=["\']fanta["\'][^>]*>',
        html,
        flags=re.I
    )

    if not blocks:
        return urls

    # Use a set to avoid duplicates
    seen = set()

    for block in blocks:
        pid_m = re.search(r'data-post-id=["\'](\d+)["\']', block)
        sid_m = re.search(r'data-server-index=["\']?(\d*)["\']?', block)

        if not pid_m:
            continue

        pid = pid_m.group(1).strip()
        sid = sid_m.group(1).strip() if sid_m else ""

        if pid in seen:
            continue
        seen.add(pid)

        bid = _get_blog_id_for_server_index(sid)
        if bid:
            urls.append(
                f"https://www.blogger.com/feeds/{bid}/posts/default/{pid}?alt=json"
            )
        else:
            _log(
                f"Unknown server index: {sid} for post {pid} (no mapping)",
                xbmc.LOGWARNING
            )

    return urls



# ── VIP helpers ─────────────────────────────
def _vip_blogid_and_alt_from_scripts(html, pid):
    m = re.search(rf'src=["\']https?://www\.blogger\.com/feeds/(\d+)/posts/default/{pid}\?([^"\']*)["\']', html, re.I)
    if m:
        qs = (m.group(2) or "").lower().replace("&amp;", "&")
        return m.group(1), ("json-in-script" if "json-in-script" in qs or "callback=" in qs else "json")
    m2 = re.search(rf'src=["\']https?://www\.blogger\.com/feeds/(\d+)/posts/default/{pid}["\']', html, re.I)
    return (m2.group(1), "json") if m2 else (None, None)

def is_vip_url(u): return urlparse(u).netloc.lower().lstrip("www.") == urlparse(VIP).netloc.lower().lstrip("www.")
def is_idrama_url(u): return urlparse(u).netloc.lower().lstrip("www.") == urlparse(IDRAMA).netloc.lower().lstrip("www.")

def extract_vip_blogger_json_urls_from_page(html):
    post_ids = re.findall(r'<div[^>]+id=["\']player["\'][^>]*data-post-id=["\'](\d+)["\']', html, re.I) \
               or re.findall(r'\bdata-post-id=["\'](\d+)["\']', html, re.I)
    seen, urls = set(), []
    def uniq(seq):
        out = []
        for x in seq:
            if x and x not in seen:
                seen.add(x); out.append(x)
        return out

    for pid in uniq([p.strip() for p in post_ids if p]):
        bid, alt = _vip_blogid_and_alt_from_scripts(html, pid)
        if bid:
            for a in uniq([alt, "json-in-script" if alt == "json" else "json"]):
                cb = "&callback=fetchBloggerPostContent" if "in-script" in a else ""
                urls.append(f"https://www.blogger.com/feeds/{bid}/posts/default/{pid}?alt={a}{cb}")
            continue
        cands = uniq([BLOG_ID_CACHE.get(x) for x in ("", "4", "2")] + list(BLOG_ID_CACHE.values()) + list(BLOG_ID_BASELINE.values()))
        for bid in cands:
            for a in ("json", "json-in-script&callback=fetchBloggerPostContent"):
                urls.append(f"https://www.blogger.com/feeds/{bid}/posts/default/{pid}?alt={a}")
    return uniq(urls)


# ==== Blogger link parsers ======================================
def parse_blogger_video_links(u):
    if "?alt=" not in u:
        u = u.split("?", 1)[0] + "?alt=json"

    try:
        r = OpenURL_KH(u, as_text=True)
        if not r or not r.strip().startswith("{"):
            _log(f"Invalid feed: {u}", xbmc.LOGWARNING)
            return []

        data = json.loads(r)
        html = html_unescape(data.get("entry", {}).get("content", {}).get("$t", ""))

        # Trim multi-server junk
        if "{nextServer}" in html:
            html = html.split("{nextServer}", 1)[0]

        # OK.RU embed handling
        if "{embed=ok}" in html:
            ids = re.findall(r"\d{10,}", html)
            if ids:
                return [
                    {'file': f"https://ok.ru/videoembed/{i}", 'title': f"Episode {n:02d}"}
                    for n, i in enumerate(ids, 1)
                ]

        links, seen = [], set()

        # ---------------------------------------------------------
        # 1) SundayDrama Sooplive HLS FIRST
        # ---------------------------------------------------------
        for url in re.findall(r"https?://[^\s\"']+?\.mp4(?:/[^\s\"']+\.m3u8)", html):
            if url in seen:
                continue
            seen.add(url)
            links.append({
                'file': url.rstrip(";"),
                'title': f"Episode {len(links)+1}"
            })

        # ---------------------------------------------------------
        # 2) Original MP4 parser (only if not HLS)
        # ---------------------------------------------------------
        for url, ep in re.findall(r"(https?:\/\/[^\s\"']+?\.mp4)(?:\s+(\d{1,3}))?", html):
            if url in seen or any(x in url for x in ["m3u8", "cloudokyo.cloud", "rumble.com/hls-vod"]):
                continue
            seen.add(url)
            links.append({
                'file': url,
                'title': f"Episode {int(ep) if ep else len(links)+1}"
            })

        # ---------------------------------------------------------
        # 3) Standalone .m3u8 fallback
        # ---------------------------------------------------------
        for url in re.findall(r"https?://[^\s\"']+?\.m3u8", html):
            if url in seen:
                continue
            seen.add(url)
            links.append({
                'file': url.rstrip(";"),
                'title': f"Episode {len(links)+1}"
            })

        # ---------------------------------------------------------
        # 4) UNIVERSAL FALLBACK (if still empty)
        # ---------------------------------------------------------
        if not links:
            for url in re.findall(r"https?://[^\s\"']+?(?:\.mp4(?:/[^\"']+)?|\.m3u8)", html):
                if url in seen or any(x in url for x in ["playlist", "master"]):
                    continue
                seen.add(url)
                links.append({
                    'file': url.rstrip(";"),
                    'title': f"Episode {len(links)+1}"
                })

        return links

    except Exception as e:
        _log(f"Error parsing Blogger video links: {e}", xbmc.LOGERROR)
        return []


def parse_blogger_video_links_script(u):
    if "?alt=" not in u:
        u = u.split("?", 1)[0] + "?alt=json-in-script&callback=fetchBloggerPostContent"
    elif "json" in u and "callback=" not in u:
        u = u.replace("alt=json", "alt=json-in-script&callback=fetchBloggerPostContent")

    try:
        r = OpenURL_KH(u, as_text=True)
        if "fetchBloggerPostContent(" not in r:
            _log(f"No script JSON: {u}", xbmc.LOGWARNING)
            return []

        m = re.search(r"fetchBloggerPostContent\((\{.*\})\);?$", r, re.S)
        if not m:
            return []

        data = json.loads(m.group(1))
        html = html_unescape(data.get("entry", {}).get("content", {}).get("$t", ""))

        links, seen = [], set()

        for url in re.findall(r"https?://[^\s\"']+?(?:\.mp4(?:/[^\s\"']+\.m3u8)?|\.m3u8)", html):
            if url in seen:
                continue
            seen.add(url)
            links.append({
                'file': url.strip().rstrip(";"),
                'title': f"Episode {len(links)+1}"
            })

        _log(f"Parsed {len(links)} video links from script feed")
        return links

    except Exception as e:
        _log(f"Error parsing script-based Blogger feed: {e}", xbmc.LOGERROR)
        return []
