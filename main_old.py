from playwright.sync_api import sync_playwright
import requests


def scrape_and_check_links(url: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Launch the browser in headless mode
        page = browser.new_page()
        page.goto(url)

        # Extract all 'a' tags with href that are not id-based links
        links = page.eval_on_selector_all("a[href]:not([href^='#'])", "elements => elements.map(e => e.href)")

        print(f"Found {len(links)} links on the page.")

        broken_links = []

        for link in links:
            try:
                response = requests.head(link, allow_redirects=True, timeout=10)
                if response.status_code >= 400:
                    print(f"Broken link: {link} (Status: {response.status_code})")
                    broken_links.append(link)
                else:
                    print(f"Working link: {link} (Status: {response.status_code})")
            except requests.RequestException as e:
                print(f"Error with link: {link} (Error: {e})")
                broken_links.append(link)

        browser.close()

        print("\nSummary:")
        print(f"Total links checked: {len(links)}")
        print(f"Broken links: {len(broken_links)}")
        if broken_links:
            print("List of broken links:")
            for link in broken_links:
                print(link)


if __name__ == "__main__":
    website_url = input("Enter the URL of the website to scrape: ")
    scrape_and_check_links(website_url)

