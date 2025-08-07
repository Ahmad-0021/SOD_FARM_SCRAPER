"""This script serves as an example on how to use Python
   & Playwright to scrape/extract data from Google Maps"""

from patchright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field
from review_scraper import scrape_reviews
from image_scraper import scrape_images
import pandas as pd
import argparse
import os
import sys
import time

@dataclass
class Business:
    """holds business data"""

    name: str = None
    address: str = None
    website: str = None
    phone_number: str = None
    reviews_count: int = None
    reviews_average: float = None
    latitude: float = None
    longitude: float = None


@dataclass
class BusinessList:
    """holds list of Business objects,
    and save to both excel and csv
    """
    business_list: list[Business] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """transform business_list to pandas dataframe

        Returns: pandas dataframe
        """
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file

        Args:
            filename (str): filename
        """

        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"output/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file

        Args:
            filename (str): filename
        """

        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"output/{filename}.csv", index=False)


def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""

    coordinates = url.split('/@')[-1].split('/')[0]
    # return latitude, longitude
    return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])


def reset_to_search_results(page, search_term=None):
    """Reset the page to show search results list view - ENHANCED VERSION"""
    try:
        print("🔄 Resetting page state...")

        # Method 1: Multiple Escape presses (most reliable)
        for i in range(3):
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)

        page.wait_for_timeout(2000)

        # Check if we're back to search results
        listings_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
        if listings_count > 0:
            print(f"✅ Reset with Escape key - found {listings_count} listings")
            return True

        # Method 2: Click on the sidebar/search results area
        print("🔄 Trying to click on search results sidebar...")
        sidebar_selectors = [
            '[role="main"]',
            '.m6QErb.DxyBCb.kA9KIf.dS8AEf',  # Search results container
            '[data-pane="search-overview"]',
            '.section-layout.section-scrollbox',
            'div[role="region"][aria-label*="Results"]'
        ]

        for selector in sidebar_selectors:
            try:
                if page.locator(selector).count() > 0:
                    page.locator(selector).first.click()
                    page.wait_for_timeout(2000)

                    listings_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                    if listings_count > 0:
                        print(f"✅ Reset by clicking sidebar - found {listings_count} listings")
                        return True
            except:
                continue

        # Method 3: Navigate back using browser history
        print("🔄 Trying browser back...")
        page.go_back()
        page.wait_for_timeout(3000)

        listings_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
        if listings_count > 0:
            print(f"✅ Reset with browser back - found {listings_count} listings")
            return True

        # Method 4: Refresh search if we have search term
        if search_term:
            print("🔄 Refreshing search...")
            try:
                # Click on search box and re-search
                search_box = page.locator('//input[@id="searchboxinput"]')
                search_box.click()
                page.wait_for_timeout(1000)
                search_box.press("Control+a")
                search_box.fill(search_term.strip())
                page.keyboard.press("Enter")
                page.wait_for_timeout(5000)

                # Wait for results to load and scroll a bit to ensure they're loaded
                page.wait_for_timeout(3000)
                if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() > 0:
                    page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
                    page.mouse.wheel(0, 3000)  # Small scroll to activate the results
                    page.wait_for_timeout(2000)

                    listings_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                    print(f"✅ Reset with search refresh - found {listings_count} listings")
                    return True
            except Exception as e:
                print(f"⚠️ Search refresh failed: {e}")

        # Method 5: Force page reload as last resort
        print("🔄 Force reloading page...")
        current_url = page.url
        page.reload()
        page.wait_for_timeout(5000)

        # If we were on a business page, go back to search
        if "/place/" in current_url and search_term:
            try:
                page.goto("https://www.google.com/maps", timeout=30000)
                page.wait_for_timeout(3000)

                search_box = page.locator('//input[@id="searchboxinput"]')
                search_box.fill(search_term.strip())
                page.keyboard.press("Enter")
                page.wait_for_timeout(5000)

                listings_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                if listings_count > 0:
                    print(f"✅ Reset with full page reload - found {listings_count} listings")
                    return True
            except Exception as e:
                print(f"⚠️ Full reload failed: {e}")

        print("⚠️ All reset methods attempted")
        return False

    except Exception as e:
        print(f"⚠️ Error resetting to search results: {e}")
        return False


def click_overview_tab(page):
    """Clicks the 'Overview' tab to return to main view - FIXED VERSION"""
    try:
        # FIXED: Proper Playwright selectors without :has-text()
        overview_selectors = [
            "button[role='tab'] >> text=Overview",
            "div[role='tab'] >> text=Overview",
            "button[data-value='Overview']",
            "//button[@role='tab' and contains(text(), 'Overview')]",
            "//div[@role='tab' and contains(text(), 'Overview')]",
            "//button[contains(text(), 'Overview')]",
            "[data-tab-index='0']",  # First tab is usually Overview
            "div[role='tablist'] button:first-child"  # First button in tab list
        ]

        for selector in overview_selectors:
            try:
                if page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    if element.is_visible():
                        element.click()
                        page.wait_for_timeout(1000)
                        print(f"✅ Clicked 'Overview' tab with: {selector}")
                        return True
            except Exception:
                continue

        print("⚠️ 'Overview' tab not found with any selector")
        return False

    except Exception as e:
        print(f"⚠️ Error clicking Overview tab: {e}")
        return False


def safe_click_with_retry(page, element, max_retries=3):
    """Safely click an element with retry logic - FIXED VERSION"""
    for attempt in range(max_retries):
        try:
            # Method 1: Use Playwright's built-in scroll method
            try:
                element.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
            except:
                # Method 2: Use hover as fallback
                try:
                    element.hover()
                    page.wait_for_timeout(1000)
                except:
                    # Method 3: Use JavaScript with proper syntax
                    try:
                        page.evaluate("(el) => el.scrollIntoView({block: 'center'})", element.element_handle())
                        page.wait_for_timeout(1000)
                    except:
                        # No scrolling, just try to click
                        pass

            # Click the element
            element.click(timeout=5000)
            page.wait_for_timeout(2000)

            return True

        except Exception as e:
            print(f"⚠️ Click attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                page.wait_for_timeout(2000)

    return False


def main():
    ########
    # input
    ########

    # read search from arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--search", type=str)
    parser.add_argument("-t", "--total", type=int)
    args = parser.parse_args()

    if args.search:
        search_list = [args.search]

    if args.total:
        total = args.total
    else:
        # if no total is passed, we set the value to random big number
        total = 1_000_000

    if not args.search:
        search_list = []
        # read search from input.txt file
        input_file_name = 'input.txt'
        # Get the absolute path of the file in the current working directory
        input_file_path = os.path.join(os.getcwd(), input_file_name)
        # Check if the file exists
        if os.path.exists(input_file_path):
            # Open the file in read mode
            with open(input_file_path, 'r') as file:
                # Read all lines into a list
                search_list = file.readlines()

        if len(search_list) == 0:
            print('Error occured: You must either pass the -s search argument, or add searches to input.txt')
            sys.exit()

    ###########
    # scraping
    ###########
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        # wait is added for dev phase. can remove it in production
        page.wait_for_timeout(5000)

        for search_for_index, search_for in enumerate(search_list):
            print(f"-----\n{search_for_index} - {search_for}".strip())

            page.locator('//input[@id="searchboxinput"]').fill(search_for)
            page.wait_for_timeout(3000)

            page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            # scrolling
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')

            # this variable is used to detect if the bot
            # scraped the same number of listings in the previous iteration
            previously_counted = 0
            while True:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)

                if (
                        page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count()
                        >= total
                ):
                    listings = page.locator(
                        '//a[contains(@href, "https://www.google.com/maps/place")]'
                    ).all()[:total]
                    listings = [listing.locator("xpath=..") for listing in listings]
                    print(f"Total Scraped: {len(listings)}")
                    break
                else:
                    # logic to break from loop to not run infinitely
                    # in case arrived at all available listings
                    if (
                            page.locator(
                                '//a[contains(@href, "https://www.google.com/maps/place")]'
                            ).count()
                            == previously_counted
                    ):
                        listings = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).all()
                        print(f"Arrived at all available\nTotal Scraped: {len(listings)}")
                        break
                    else:
                        previously_counted = page.locator(
                            '//a[contains(@href, "https://www.google.com/maps/place")]'
                        ).count()
                        print(
                            f"Currently Scraped: ",
                            page.locator(
                                '//a[contains(@href, "https://www.google.com/maps/place")]'
                            ).count(),
                        )

            business_list = BusinessList()

            # scraping
            for index, listing in enumerate(listings):
                try:
                    print(f"\n🏢 Processing business {index + 1}/{len(listings)}")

                    # ENHANCED: Reset page state before clicking listing (skip first)
                    if index > 0:
                        reset_success = reset_to_search_results(page, search_for.strip())

                        # Get fresh listings reference after reset
                        try:
                            page.wait_for_timeout(2000)  # Increased wait time

                            # Try to re-scroll to ensure all listings are loaded
                            try:
                                page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
                                page.mouse.wheel(0, 5000)  # Scroll to load more listings
                                page.wait_for_timeout(2000)
                            except:
                                pass

                            current_listings = page.locator(
                                '//a[contains(@href, "https://www.google.com/maps/place")]'
                            ).all()[:total]
                            current_listings = [listing.locator("xpath=..") for listing in current_listings]

                            if index < len(current_listings):
                                listing = current_listings[index]
                                print(f"✅ Updated to fresh listing reference")
                            else:
                                print(f"⚠️ Listing {index} no longer available, skipping")
                                continue

                        except Exception as e:
                            print(f"⚠️ Could not get fresh listings: {e}")
                            continue

                    # IMPROVED: Click the listing with better retry logic
                    if not safe_click_with_retry(page, listing):
                        print(f"❌ Failed to click listing {index + 1}, skipping")
                        continue

                    # Verify we're on a business page
                    page.wait_for_timeout(3000)  # Increased wait time
                    if page.locator("//h1[contains(@class, 'DUwDvf')]").count() == 0:
                        print(f"⚠️ Business details not loaded properly, skipping")
                        continue

                    name_xpath = "//h1[contains(@class, 'DUwDvf')]"
                    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
                    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
                    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
                    review_count_xpath = '//button[contains(@jsaction, "reviewChart")]//span'
                    reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'

                    business = Business()

                    # Get business name from H1 element directly
                    if page.locator(name_xpath).count() > 0:
                        business.name = page.locator(name_xpath).first.inner_text().strip()
                    else:
                        business.name = ""

                    if page.locator(address_xpath).count() > 0:
                        business.address = page.locator(address_xpath).all()[0].inner_text()
                    else:
                        business.address = ""
                    if page.locator(website_xpath).count() > 0:
                        business.website = page.locator(website_xpath).all()[0].inner_text()
                    else:
                        business.website = ""
                    if page.locator(phone_number_xpath).count() > 0:
                        business.phone_number = page.locator(phone_number_xpath).all()[0].inner_text()
                    else:
                        business.phone_number = ""

                    # Extract review count
                    if page.locator(review_count_xpath).count() > 0:
                        try:
                            review_text = page.locator(review_count_xpath).first.inner_text().strip()
                            print(f"DEBUG: Review text found: '{review_text}'")

                            # Extract number from text like "37 reviews"
                            import re
                            numbers = re.findall(r'\d+', review_text.replace(',', ''))
                            if numbers:
                                business.reviews_count = int(numbers[0])
                                print(f"DEBUG: Extracted review count: {business.reviews_count}")
                            else:
                                business.reviews_count = ""
                                print("DEBUG: No numbers found in review text")
                        except Exception as e:
                            print(f"DEBUG: Error extracting review count: {e}")
                            business.reviews_count = ""
                    else:
                        business.reviews_count = ""
                        print("DEBUG: No review count elements found")

                    if page.locator(reviews_average_xpath).count() > 0:
                        try:
                            business.reviews_average = float(
                                page.locator(reviews_average_xpath).get_attribute("aria-label")
                                .split()[0]
                                .replace(',', '.')
                                .strip())
                        except:
                            business.reviews_average = ""
                    else:
                        business.reviews_average = ""

                    try:
                        business.latitude, business.longitude = extract_coordinates_from_url(page.url)
                    except:
                        business.latitude = ""
                        business.longitude = ""

                    business_list.business_list.append(business)

                    # Scrape reviews and images if business name exists
                    if business.name:
                        print(f"📝 Scraping reviews for: {business.name}")
                        try:
                            review_csv = scrape_reviews(page, business.name)
                        except Exception as e:
                            print(f"⚠️ Error scraping reviews: {e}")

                        # IMPROVED: Return to Overview tab after reviews
                        click_overview_tab(page)

                        print(f"🖼️ Scraping images for: {business.name}")
                        try:
                            image_csv = scrape_images(page, business.name)
                        except Exception as e:
                            print(f"⚠️ Error scraping images: {e}")

                        # IMPROVED: Return to Overview tab after images
                        click_overview_tab(page)

                    else:
                        print("⚠️ Cannot scrape reviews or images — no business name")

                    print(f"✅ Completed processing: {business.name or 'Unnamed Business'}")

                except Exception as e:
                    print(f'❌ Error occurred processing listing {index + 1}: {e}')
                    # Try to reset page state even if there was an error
                    try:
                        reset_to_search_results(page, search_for.strip())
                    except:
                        pass
                    continue

            #########
            # output
            #########
            business_list.save_to_excel(f"google_maps_data_{search_for}".replace(' ', '_'))
            business_list.save_to_csv(f"google_maps_data_{search_for}".replace(' ', '_'))

        browser.close()


if __name__ == "__main__":
    main()