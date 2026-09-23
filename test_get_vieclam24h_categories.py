import sys
import io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://vieclam24h.vn/'
}

r = requests.get('https://vieclam24h.vn/tim-kiem-viec-lam-nhanh', headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

categories = []
for a in soup.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    # Vieclam24h category links format: /viec-lam-*-o*.html
    if re.match(r'^/viec-lam-[a-zA-Z0-9-]+-o\d+\.html$', href):
        full_url = 'https://vieclam24h.vn' + href
        categories.append({'name': text if text else href, 'url': full_url, 'slug': href})

# Also check province links
provinces = []
for a in soup.find_all('a', href=True):
    href = a['href']
    text = a.get_text(strip=True)
    if re.match(r'^/viec-lam-tai-[a-zA-Z0-9-]+-p\d+\.html$', href) or re.match(r'^/viec-lam-[a-zA-Z0-9-]+-tai-[a-zA-Z0-9-]+-o\d+p\d+\.html$', href):
        provinces.append({'name': text, 'url': 'https://vieclam24h.vn' + href})

print(f"Found {len(categories)} job categories:")
for c in categories:
    print(f"  {c['name']}: {c['url']}")

print(f"\nFound {len(provinces)} province links:")
for p in provinces[:10]:
    print(f"  {p['name']}: {p['url']}")
