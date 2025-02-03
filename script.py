import os
import re
import requests # type: ignore
import time
from bs4 import BeautifulSoup # type: ignore
from concurrent.futures import ThreadPoolExecutor

def download_pdf(pdf_url, output_dir, file_name):
    try:
        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{file_name}.pdf")
        with open(file_path, "wb") as file:
            for chunk in response.iter_content(8192):
                file.write(chunk) 
        print(f"Saved PDF: {file_path}")
    except requests.RequestException as e:
        print(f"Failed to download PDF: {pdf_url}\nError: {e}")

def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', "_", filename)

def process_paper(base_url, paper_url, output_dir):
    attempts = 0
    while attempts < 5:
        try:
            print(f"Processing paper: {paper_url} (Attempt {attempts + 1})")
            response = requests.get(paper_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            paper_title = sanitize_filename(soup.title.string or "untitled")
            pdf_link = soup.select_one("a[href$='Paper-Conference.pdf']")
            if pdf_link:
                pdf_url = base_url + pdf_link['href']
                download_pdf(pdf_url, output_dir, paper_title)
            else:
                print(f"No PDF found for: {paper_url}")
            return
        except requests.RequestException as e:
            print(f"Error processing paper: {paper_url} (Attempt {attempts + 1})\n{e}")
            attempts += 1
            time.sleep(2)

def extract_year_from_url(url):
    match = re.search(r"(\d{4})", url)
    return int(match.group(1)) if match else 0

def extract_latest_year(year_links):
    return max((extract_year_from_url(link['href']) for link in year_links), default=0)

def main():
    base_url = "https://papers.nips.cc"
    output_dir = "B:/scraped2-pdfs/"
    response = requests.get(base_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    year_links = soup.select("a[href^='/paper_files/paper/']")
    latest_year = extract_latest_year(year_links)
    print(f"Latest year found: {latest_year}")
    target_years = {latest_year - i for i in range(5)}
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        for link in year_links:
            year_url = base_url + link['href']
            year = extract_year_from_url(year_url)
            if year in target_years:
                print(f"Processing year: {year_url}")
                year_response = requests.get(year_url, timeout=30)
                year_response.raise_for_status()
                year_soup = BeautifulSoup(year_response.text, "html.parser")
                paper_links = year_soup.select("ul.paper-list li a[href$='Abstract-Conference.html']")
                for paper_link in paper_links:
                    paper_url = base_url + paper_link['href']
                    executor.submit(process_paper, base_url, paper_url, output_dir)

if __name__ == "__main__":
    main()
