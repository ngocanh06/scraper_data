import sys
import io
import time
import os
import json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup
import undetected_chromedriver as uc

options = uc.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--lang=vi-VN')

driver = uc.Chrome(options=options, headless=False)

try:
    url = 'https://vn.indeed.com/jobs?q=Kinh+doanh&l=H%C3%A0+N%E1%BB%99i'
    print(f"Loading {url}...")
    driver.get(url)
    time.sleep(5)
    
    print("Page title:", driver.title)
    print("Final URL:", driver.current_url)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Save a sample of html for inspection if needed
    cards = soup.select('div.job_seen_beacon, div.cardOutline, [data-jk]')
    print(f"Found {len(cards)} cards")
    
    for idx, card in enumerate(cards[:5]):
        jk = card.get('data-jk') or ''
        if not jk:
            jk_el = card.select_one('[data-jk]')
            if jk_el:
                jk = jk_el.get('data-jk')
        
        title_el = card.select_one('h2.jobTitle span, .jobTitle, a[id^="job_"]')
        comp_el = card.select_one('[data-testid="company-name"], .css-63koeb, .companyName')
        loc_el = card.select_one('[data-testid="text-location"], .css-1p0sjhy, .companyLocation')
        salary_el = card.select_one('[data-testid="attribute_snippet_testid"], .metadata, .salary-snippet-container')
        
        print(f"\n--- Card {idx + 1} ---")
        print(f"  JK: {jk}")
        print(f"  Title: {title_el.get_text(strip=True) if title_el else 'None'}")
        print(f"  Company: {comp_el.get_text(strip=True) if comp_el else 'None'}")
        print(f"  Location: {loc_el.get_text(strip=True) if loc_el else 'None'}")
        print(f"  Salary: {salary_el.get_text(strip=True) if salary_el else 'None'}")
        
    if cards:
        # test clicking or opening a job detail directly
        first_jk = cards[0].get('data-jk') or (cards[0].select_one('[data-jk]').get('data-jk') if cards[0].select_one('[data-jk]') else '')
        if first_jk:
            detail_url = f"https://vn.indeed.com/viewjob?jk={first_jk}"
            print(f"\nLoading detail: {detail_url}")
            driver.get(detail_url)
            time.sleep(4)
            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Check JSON-LD
            ld_scripts = detail_soup.find_all('script', type='application/ld+json')
            print(f"Found {len(ld_scripts)} JSON-LD scripts")
            for s in ld_scripts:
                try:
                    data = json.loads(s.string)
                    if data.get('@type') == 'JobPosting':
                        print("JSON-LD JobPosting found:")
                        print(" - Title:", data.get('title'))
                        print(" - HiringOrg:", data.get('hiringOrganization', {}).get('name'))
                        print(" - BaseSalary:", data.get('baseSalary'))
                        print(" - EmploymentType:", data.get('employmentType'))
                        print(" - Location:", data.get('jobLocation'))
                        print(" - Description length:", len(data.get('description', '')))
                except Exception as ex:
                    print("JSON-LD parse err:", ex)

finally:
    driver.quit()
