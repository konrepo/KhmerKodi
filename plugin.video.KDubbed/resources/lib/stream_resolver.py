"""Kodi adaptation of KhmerDub Stremio OK.ru resolution."""

import html
import re
from urllib.parse import urljoin
import requests
import xbmc
from resources.lib.handlers_common import USER_AGENT


def normalize_ok_url(url):
    url = (url or '').strip()
    if url.startswith('//'):
        url = 'https:' + url
    return re.sub(r'(?<=//)m\.ok\.ru', 'ok.ru', url, flags=re.I)


def extract_episode_number(link, text=''):
    if '/album/' in link:
        return 1
    match = re.search(r'Episode\s*0*(\d+)', text, re.I)
    if match:
        return int(match.group(1))
    slug = link.split('?', 1)[0].rstrip('/').rsplit('/', 1)[-1]
    for pattern in (r'-(\d+)-end$', r'-(\d+)e(?:-\d+)?$', r'-(\d+)$', r'-(\d+)-\d+$'):
        match = re.search(pattern, slug, re.I)
        if match:
            return int(match.group(1))
    return 1


def _clean(text):
    return html.unescape(str(text)).replace('\\u0026', '&').replace('\\&', '&').replace('\\/', '/')


def _fetch(url):
    response = requests.get(url, headers={'User-Agent': USER_AGENT, 'Referer': 'https://ok.ru/'}, timeout=15)
    response.raise_for_status()
    return _clean(response.text)


def _best_hls(url):
    try:
        lines = _fetch(url).splitlines()
        best = (0, url)
        for i, line in enumerate(lines[:-1]):
            if not line.startswith('#EXT-X-STREAM-INF') or lines[i + 1].startswith('#'):
                continue
            match = re.search(r'RESOLUTION=\d+x(\d+)', line, re.I)
            height = int(match.group(1)) if match else 0
            if height > best[0]:
                best = (height, urljoin(url, lines[i + 1].strip()))
        return best[1]
    except requests.RequestException:
        return url


def resolve_ok_embed(url):
    try:
        page = _fetch(normalize_ok_url(url))
        patterns = (
            r'"hlsMasterPlaylistUrl"\s*:\s*"([^"]+)"',
            r'"ondemandHls"\s*:\s*"([^"]+)"',
            r'"hlsManifestUrl"\s*:\s*"([^"]+)"',
            r'"metadataUrl"\s*:\s*"([^"]+)"',
            r'"videoSrc"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"(https://[^"]+\.m3u8[^"]*)"',
        )
        match = next((m for pattern in patterns if (m := re.search(pattern, page, re.I))), None)
        if not match:
            matches = re.findall(r'"(?:name|url)"\s*:\s*"[^"]+"\s*,\s*"url"\s*:\s*"(https:[^"]+)"', page, re.I)
            return _best_hls(_clean(matches[-1])) if matches else None
        stream = _clean(match.group(1))
        if 'metadata' in stream.lower():
            meta = _fetch(stream)
            for pattern in patterns[:3] + patterns[4:]:
                candidate = re.search(pattern, meta, re.I)
                if candidate:
                    stream = _clean(candidate.group(1))
                    break
            else:
                return None
        if not stream.startswith(('https://', 'http://')):
            return None
        return _best_hls(stream) if '.m3u8' in stream else stream
    except (requests.RequestException, ValueError) as exc:
        xbmc.log('[KDUBBED] OK.ru resolution failed: {}'.format(exc), xbmc.LOGWARNING)
        return None
