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


def reset_to_search_results(page):
    """Reset the page to show search results list view"""
    try:
        # Method 1: Press Escape key multiple times (most reliable)
        print("🔄 Attempting to reset with Escape key...")
        for i in range(3):
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)

        # Check if we're back to search results
        if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() > 0:
            print("✅ Reset successful with Escape key")
            return True

        # Method 2: Try clicking visible close buttons only
        close_selectors = [
            "button[aria-label*='Close']",
            "button[aria-label*='Back']",
            "[data-value='back']",
            "button[jsaction*='close']"
        ]

        for selector in close_selectors:
            try:
                elements = page.locator(selector).all()
                for element in elements:
                    if element.is_visible():
                        element.click(timeout=3000)
                        page.wait_for_timeout(2000)
                        print(f"✅ Closed detail view using: {selector}")
                        return True
            except Exception:
                continue

        # Method 3: Click on the left sidebar area to get back to results
        print("🔄 Trying to click on sidebar...")
        try:
            # Click on the search results sidebar
            sidebar_selectors = [
                "[role='main'] [role='region']",
                ".m6QErb",  # Google Maps sidebar class
                "[data-pane='search-overview']"
            ]

            for selector in sidebar_selectors:
                if page.locator(selector).count() > 0:
                    page.locator(selector).first.click()
                    page.wait_for_timeout(2000)
                    print(f"✅ Clicked sidebar: {selector}")
                    return True
        except Exception:
            pass

        # Method 4: Navigate back in browser history
        print("🔄 Trying browser back...")
        page.go_back()
        page.wait_for_timeout(3000)

        if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() > 0:
            print("✅ Reset successful with browser back")
            return True

        print("⚠️ All reset methods failed")
        return False

    except Exception as e:
        print(f"⚠️ Error resetting to search results: {e}")
        return False


def click_overview_tab(page):
    """Clicks the 'Overview' tab to return to main view"""
    try:
        # Try multiple selectors for the Overview tab
        overview_selectors = [
            "button[role='tab']:has-text('Overview')",
            "button[role='tab'][aria-label*='Overview']",
            "div[role='tab']:has-text('Overview')",
            "//button[@role='tab' and contains(., 'Overview')]",
            "//div[@role='tab' and contains(., 'Overview')]"
        ]

        for selector in overview_selectors:
            if page.locator(selector).count() > 0:
                page.locator(selector).first.click()
                page.wait_for_timeout(2000)
                print("✅ Clicked 'Overview' tab")
                return True

        print("⚠️ 'Overview' tab not found with any selector")
        return False

    except Exception as e:
        print(f"⚠️ Error clicking Overview tab: {e}")
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

                    # IMPORTANT: Reset page state before clicking listing (skip first)
                    if index > 0:
                        print("🔄 Resetting page state...")

                        # Try multiple reset approaches
                        reset_success = False

                        # Approach 1: Simple Escape key
                        try:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(2000)
                            if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() > 0:
                                print("✅ Reset with Escape key")
                                reset_success = True
                        except:
                            pass

                        # Approach 2: Full reset function
                        if not reset_success:
                            reset_success = reset_to_search_results(page)

                        # Approach 3: Re-search if all else fails
                        if not reset_success:
                            print("🔄 Performing hard reset with new search...")
                            try:
                                search_box = page.locator('//input[@id="searchboxinput"]')
                                search_box.click()
                                page.wait_for_timeout(1000)
                                search_box.press("Control+a")
                                search_box.type(search_for.strip())
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(5000)

                                # Re-scroll to get listings
                                page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
                                page.mouse.wheel(0, 5000)
                                page.wait_for_timeout(2000)

                                # Re-get listings
                                updated_listings = page.locator(
                                    '//a[contains(@href, "https://www.google.com/maps/place")]'
                                ).all()[:total]
                                listings = [listing.locator("xpath=..") for listing in updated_listings]
                                print(f"✅ Hard reset completed, found {len(listings)} listings")

                            except Exception as e:
                                print(f"❌ Hard reset failed: {e}")
                                continue

                        # Verify we have valid listings after reset
                        try:
                            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]', timeout=10000)
                            page.wait_for_timeout(1000)

                            # Get fresh listings reference
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

                    # Ensure the listing is visible and clickable
                    try:
                        page.evaluate("arguments[0].scrollIntoView({block: 'center'})", listing.element_handle())
                        page.wait_for_timeout(1000)
                    except:
                        pass

                    # Click the listing with retry logic
                    click_success = False
                    for attempt in range(3):
                        try:
                            listing.click(timeout=5000)
                            page.wait_for_timeout(3000)

                            # Verify we're on a business page
                            if page.locator("//h1[contains(@class, 'DUwDvf')]").count() > 0:
                                click_success = True
                                break
                            else:
                                print(f"⚠️ Click attempt {attempt + 1} didn't open business details")
                                page.wait_for_timeout(2000)
                        except Exception as e:
                            print(f"⚠️ Click attempt {attempt + 1} failed: {e}")
                            page.wait_for_timeout(2000)

                    if not click_success:
                        print(f"❌ Failed to click listing {index + 1} after 3 attempts, skipping")
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
                        business.reviews_average = float(
                            page.locator(reviews_average_xpath).get_attribute("aria-label")
                            .split()[0]
                            .replace(',', '.')
                            .strip())
                    else:
                        business.reviews_average = ""

                    business.latitude, business.longitude = extract_coordinates_from_url(page.url)

                    business_list.business_list.append(business)

                    # Scrape reviews and images if business name exists
                    if business.name:
                        print(f"📝 Scraping reviews for: {business.name}")
                        try:
                            review_csv = scrape_reviews(page, business.name)
                        except Exception as e:
                            print(f"⚠️ Error scraping reviews: {e}")

                        # Return to Overview tab after reviews
                        click_overview_tab(page)
                        time.sleep(2)

                        print(f"🖼️ Scraping images for: {business.name}")
                        try:
                            image_csv = scrape_images(page, business.name)
                        except Exception as e:
                            print(f"⚠️ Error scraping images: {e}")

                        # Return to Overview tab after images
                        click_overview_tab(page)
                        time.sleep(2)

                    else:
                        print("⚠️ Cannot scrape reviews or images — no business name")

                    print(f"✅ Completed processing: {business.name or 'Unnamed Business'}")

                except Exception as e:
                    print(f'❌ Error occurred processing listing {index + 1}: {e}')
                    # Try to reset page state even if there was an error
                    try:
                        reset_to_search_results(page)
                        page.wait_for_timeout(2000)
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