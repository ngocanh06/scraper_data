import sys
import io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://vieclam24h.vn/'
}

cat_url = 'https://vieclam24h.vn/viec-lam-ban-hang-kinh-doanh-o13.html'
r = requests.get(cat_url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

job_urls = []
for a in soup.find_all('a', href=True):
    href = a['href']
    if 'id200' in href and href.endswith('.html'):
        full = href if href.startswith('http') else 'https://vieclam24h.vn' + href
        clean = full.split('?')[0]
        if clean not in job_urls:
            job_urls.append(clean)

print(f"Sample jobs from Kinh doanh ({len(job_urls)} found):")
for u in job_urls[:5]:
    print("Testing job:", u)
    jr = requests.get(u, headers=headers)
    jsoup = BeautifulSoup(jr.text, 'html.parser')
    for script in jsoup.find_all('script', type='application/ld+json'):
        try:
            jd = json.loads(script.string)
            if jd.get('@type') == 'JobPosting':
                print(f"  - Title: {jd.get('title')}")
                print(f"  - Company: {jd.get('hiringOrganization', {}).get('name')}")
                print(f"  - Category: {jd.get('occupationalCategory')}")
                print(f"  - Industry: {jd.get('industry')}")
                print(f"  - Salary: {jd.get('baseSalary')}")
                print(f"  - Exp: {jd.get('experienceRequirements')}")
                print(f"  - Deadline: {jd.get('validThrough')}")
                print(f"  - Qualifications: {jd.get('qualifications')}")
                print(f"  - EmploymentType: {jd.get('employmentType')}")
                print(f"  - Location: {jd.get('jobLocation')}")
        except Exception as ex:
            print("  - Parse error:", ex)
