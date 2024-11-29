import os
import platform
import requests
import argparse
import zipfile
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin, urlparse
from queue import Queue
from threading import Lock
import multiprocessing
import time

STABLE_API_URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
DRIVER_FOLDER = "drivers"
CHROMEDRIVER_FILENAME = "chromedriver"
MAX_THREADS = min(multiprocessing.cpu_count(), 16)  # Use up to 16 threads


def get_platform():
    """Determine the platform and architecture."""
    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "windows":
        return "win64"
    elif system == "linux":
        return "linux64"
    elif system == "darwin" and "arm" in arch:
        return "mac-arm64"
    elif system == "darwin":
        return "mac-x64"
    else:
        raise RuntimeError("Unsupported operating system or architecture.")


def fetch_latest_stable_url():
    """Fetch the latest stable ChromeDriver URL from the JSON API."""
    print(f"Fetching the latest ChromeDriver Stable build info from {STABLE_API_URL}...")
    response = requests.get(STABLE_API_URL)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch ChromeDriver Stable info: {response.status_code}")

    data = response.json()
    platform = get_platform()

    # Extract stable channel URL for ChromeDriver
    try:
        for entry in data["channels"]["Stable"]["downloads"]["chromedriver"]:
            if entry["platform"] == platform:
                download_url = entry["url"]
                print(f"ChromeDriver download URL for Stable: {download_url}")
                return download_url
    except KeyError as e:
        raise RuntimeError(f"Error in JSON structure: {e}")

    raise RuntimeError(f"ChromeDriver not available for platform: {platform}")


def download_chromedriver(url):
    """Download the latest ChromeDriver stable build."""
    if not os.path.exists(DRIVER_FOLDER):
        os.makedirs(DRIVER_FOLDER)

    zip_file_path = os.path.join(DRIVER_FOLDER, os.path.basename(url))
    print(f"Downloading ChromeDriver from {url}...")
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download ChromeDriver: {response.status_code}")

    # Save the zip file
    with open(zip_file_path, "wb") as f:
        f.write(response.content)

    print(f"ChromeDriver downloaded to: {zip_file_path}")
    return zip_file_path


def extract_chromedriver(zip_file_path):
    """Extract the ChromeDriver binary from the downloaded zip file."""
    print(f"Extracting ChromeDriver from {zip_file_path}...")
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(DRIVER_FOLDER)

    # Locate the extracted ChromeDriver binary
    driver_path = None
    for root, _, files in os.walk(DRIVER_FOLDER):
        for file in files:
            if file == CHROMEDRIVER_FILENAME or file == CHROMEDRIVER_FILENAME + ".exe":
                driver_path = os.path.abspath(os.path.join(root, file))
                break

    if not driver_path or not os.path.exists(driver_path):
        raise RuntimeError("Failed to locate ChromeDriver in the extracted files.")

    os.chmod(driver_path, 0o755)  # Make it executable
    print(f"ChromeDriver binary ready at: {driver_path}")
    return driver_path


def setup_browser():
    """Set up the browser with ChromeDriver."""
    download_url = fetch_latest_stable_url()
    zip_file_path = download_chromedriver(download_url)
    chromedriver_path = extract_chromedriver(zip_file_path)

    options = Options()
    options.add_argument("--start-maximized")
    options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"  # Stable Chrome binary
    # Uncomment the following line to run in headless mode
    # options.add_argument("--headless")

    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)


def normalize_url(url):
    """Normalize URLs to avoid duplicates."""
    parsed = urlparse(url)
    # Remove fragment (e.g., #section) and normalize
    normalized = urljoin(url, parsed.path.rstrip('/'))
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def extract_links(browser, base_url):
    """Extract all valid links from the current page."""
    links = browser.find_elements(By.XPATH, "//a[@href]")
    urls = set()
    for link in links:
        href = link.get_attribute("href")
        if href:
            absolute_url = urljoin(base_url, href)
            # Only include links from the same domain
            if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                urls.add(absolute_url)
    return urls


def crawl_site(base_url):
    """Crawl a website and check for broken links."""
    browser = setup_browser()
    visited_urls = set()
    broken_links = []
    queue = Queue()
    lock = Lock()

    def process_url(url):
        """Process a single URL."""
        normalized_url = normalize_url(url)
        with lock:
            if normalized_url in visited_urls:
                return
            visited_urls.add(normalized_url)

        try:
            browser.get(normalized_url)
            time.sleep(1)  # Allow time for the page to load
            status = 200
            print(f"Working link: {normalized_url} (Status: {status})")
            links = extract_links(browser, base_url)

            with lock:
                for link in links:
                    if link not in visited_urls:
                        queue.put(link)

        except Exception as e:
            print(f"Broken link: {normalized_url} (Error: {e})")
            with lock:
                broken_links.append(normalized_url)

    # Seed the queue with the base URL
    queue.put(base_url)

    while not queue.empty():
        url = queue.get()
        process_url(url)

    browser.quit()

    # Output broken links to a JSON file
    with open("../broken_links.json", "w") as f:
        json.dump({"broken_links": broken_links}, f, indent=4)
    print(f"\nBroken links saved to broken_links.json")

    print("\nSummary:")
    print(f"Total pages visited: {len(visited_urls)}")
    print(f"Broken links: {len(broken_links)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl a website and check for broken links.")
    parser.add_argument(
        "base_url",
        type=str,
        help="The base URL of the website to scrape. Example: https://example.com"
    )
    args = parser.parse_args()
    crawl_site(args.base_url)