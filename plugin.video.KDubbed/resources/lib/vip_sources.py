"""VIP fallback episode discovery, adapted from the working Stremio source."""

import json
import re
from html import unescape
from urllib.parse import urljoin, urlparse, quote, urlencode
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
S = requests.Session()
S.headers.update({'User-Agent': UA, 'Accept': 'text/html,application/json,*/*;q=0.8'})

def get(url, referer):
    r = S.get(url, headers={'Referer': referer}, timeout=15)
    r.raise_for_status()
    return r

def normalize(html):
    return unescape(str(html or '')).replace('\\/', '/').replace('\\u0026', '&')

def extract_urls(text):
    text = normalize(text)
    out = []
    for pattern in (
        r'https?://[^\s"\'<>;\\]+?\.(?:mp4|m3u8)(?:\?[^\s"\'<>;\\]*)?',
        r'https?://(?:m\.)?ok\.ru/videoembed/\d+',
        r'https?://(?:www\.)?khmer-movie\.org/tv-shows/[^\s"\'<>;\\]+',
        r'https?://[^\s"\'<>;\\]*player\.php\?[^\s"\'<>;\\]+',
    ):
        out.extend(re.findall(pattern, text, re.I))
    out.extend('https://ok.ru/videoembed/' + x for x in re.findall(r'\{ok=(\d+)\}', text, re.I) if re.search(r'\{embed\s*=\s*ok\}', text, re.I))
    out.extend('https://www.dailymotion.com/embed/video/' + x for x in re.findall(r'\{dm=(\w+)\}', text, re.I))
    out.extend('https://drive.google.com/file/d/' + x + '/preview' for x in re.findall(r'\{gd=([\w-]+)\}', text, re.I))
    return list(dict.fromkeys(x.rstrip(').,') for x in out))

def wordpress_id(html):
    for pattern in (r'<link[^>]*rel=["\']shortlink["\'][^>]*href=["\'][^"\']*[?&]p=(\d+)',
                    r'/wp-json/wp/v2/posts/(\d+)', r'<article[^>]*id=["\']post-(\d+)',
                    r'<img[^>]*post-id=["\'](\d+)'):
        m = re.search(pattern, html, re.I)
        if m: return m.group(1)
    return None

def khmerdrama_urls(html):
    m = re.search(r'https?://(?:video4khmer\.khmerdrama\.org|khmermove\.cinaze\.com)/(?:tv-series|movies)/[^\s"\'<>\\]+', normalize(html), re.I)
    if not m: return []
    page = m.group(0)
    parsed = urlparse(page)
    slug = parsed.path.rstrip('/').split('/')[-1]
    api = parsed.scheme + '://' + parsed.netloc + '/api/movies.php?' + urlencode({'find_slug': slug, 'paginated': 1})
    data = get(api, page).json().get('data')
    found = data[0] if isinstance(data, list) and data else data
    if not isinstance(found, dict): return []
    servers = found.get('servers') or []
    if isinstance(servers, str): servers = json.loads(servers)
    eps = {}
    for server in servers:
        for i, ep in enumerate(server.get('episodes') or []):
            key = str(ep.get('episode_name') or i + 1).strip() if isinstance(ep, dict) else str(i + 1)
            url = (ep.get('url') or ep.get('file') or ep.get('src') or '') if isinstance(ep, dict) else ep
            if url and not eps.get(key): eps[key] = url
    def sort_key(k):
        m = re.search(r'\d+', k)
        return (int(m.group()) if m else 10**9, k)
    return [eps[k] for k in sorted(eps, key=sort_key)]

def khmer_movie_pages(series_url):
    slug = urlparse(series_url).path.rstrip('/').split('/')[-1]
    if not slug: return []
    base = 'https://khmer-movie.org/tv-shows/' + quote(slug) + '/'
    html = get(base + '?ep=1', series_url).text
    free = re.search(r'data-freeeps=["\'](\d+)', html, re.I)
    if not free: return []
    return [base + '?ep=' + str(i) for i in range(1, min(int(free.group(1)), 500) + 1)]

def discover_vip(series_url, page_html):
    """Return episode URLs; failures in one source do not block other sources."""
    candidates = []
    def add(label, urls):
        urls = list(dict.fromkeys(u for u in urls if u))
        if urls: candidates.append((label, urls))
    add('page', extract_urls(page_html))
    post_id = wordpress_id(page_html)
    if post_id:
        try:
            api = 'https://phumikhmer.vip/wp-json/wp/v2/posts/' + post_id
            post = get(api, series_url).json()
            add('wordpress', extract_urls((post.get('content') or {}).get('rendered', '')))
        except (requests.RequestException, ValueError, TypeError): pass
    try: add('khmerdrama', khmerdrama_urls(page_html))
    except (requests.RequestException, ValueError, TypeError, KeyError): pass
    # Expand discovered Khmer Movie series links into episode-specific pages.
    movie_links = [u for _, urls in candidates for u in urls if is_khmer_movie(u)]
    for movie_url in dict.fromkeys(movie_links):
        try: add('khmer-movie', khmer_movie_pages(movie_url))
        except (requests.RequestException, ValueError, TypeError): pass
    if not candidates and urlparse(series_url).hostname in ('phumikhmer.vip', 'www.phumikhmer.vip'):
        try: add('khmer-movie', khmer_movie_pages(series_url))
        except (requests.RequestException, ValueError, TypeError): pass
    return max(candidates, key=lambda pair: (len(pair[1]), pair[0] == 'khmer-movie')) if candidates else (None, [])


def is_khmer_movie(url):
    p = urlparse(url)
    return p.hostname in ('khmer-movie.org', 'www.khmer-movie.org') and p.path.startswith('/tv-shows/')

def resolve_khmer_movie(url):
    """Resolve an accessible Khmer Movie episode using its public player AJAX."""
    if not is_khmer_movie(url):
        return None
    from urllib.parse import parse_qs
    ep = int(parse_qs(urlparse(url).query).get('ep', ['1'])[0])
    if ep < 1:
        return None
    page_url = url.split('?', 1)[0] + '?ep=' + str(ep)
    html = get(page_url, url).text
    def field(name):
        m = re.search(r'data-' + name + r'=["\']([^"\']+)', html, re.I)
        return m.group(1) if m else ''
    post_id, access_token = field('postid'), field('access-token')
    free = int(field('freeeps') or '0')
    premium = field('premium').lower() == 'true'
    unlocked = field('unlocked').lower() == 'true'
    if premium and not unlocked and ep - 1 >= free:
        return None
    settings = re.search(r'var\s+PLAYER_SETTINGS\s*=\s*(\{.*?\});', html, re.I | re.S)
    config = settings.group(1) if settings else ''
    nonce_match = re.search(r'["\']nonce["\']\s*:\s*["\']([^"\']+)', config, re.I)
    ajax_match = re.search(r'["\']ajaxUrl["\']\s*:\s*["\']([^"\']+)', config, re.I)
    nonce = nonce_match.group(1) if nonce_match else ''
    ajax = ajax_match.group(1) if ajax_match else 'https://khmer-movie.org/wp-admin/admin-ajax.php'
    if not (post_id and access_token and nonce):
        return None
    response = S.post(ajax, data={
        'action': 'anc_player_resolve_source', 'nonce': nonce,
        'access_token': access_token, 'post_id': post_id, 'episode': str(ep - 1)
    }, headers={'Referer': page_url}, timeout=15)
    response.raise_for_status()
    result = response.json()
    if result.get('success') and isinstance(result.get('data'), dict):
        return result['data'].get('url')
    return None
