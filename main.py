"""This script scrapes all sod farms from every US state using Google Maps - OPTIMIZED URL-BASED VERSION"""
from dotenv import load_dotenv
from patchright.sync_api import sync_playwright, ProxySettings
from dataclasses import dataclass, asdict, field
from review_scraper import scrape_reviews
from image_scraper import scrape_images
import pandas as pd
import argparse
import os
import time
import random
import re
from urllib.parse import urlparse, parse_qs

load_dotenv()

PROXY: ProxySettings = {
    "server": f"http://{os.getenv('PROXY_HOST')}:{os.getenv('PROXY_PORT')}",
    "username": os.getenv("PROXY_USERNAME"),
    "password": os.getenv("PROXY_PASSWORD")
}

# US States list for comprehensive scraping
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

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
    state: str = None
    google_maps_url: str = None  # Store the original Google Maps URL

@dataclass
class BusinessList:
    """holds list of Business objects, and save to both excel and csv"""
    business_list: list[Business] = field(default_factory=list)
    save_at = 'output'

    def dataframe(self):
        """transform business_list to pandas dataframe"""
        return pd.json_normalize(
            (asdict(business) for business in self.business_list), sep="_"
        )

    def save_to_excel(self, filename):
        """saves pandas dataframe to excel (xlsx) file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_excel(f"output/{filename}.xlsx", index=False)

    def save_to_csv(self, filename):
        """saves pandas dataframe to csv file"""
        if not os.path.exists(self.save_at):
            os.makedirs(self.save_at)
        self.dataframe().to_csv(f"output/{filename}.csv", index=False)

def extract_coordinates_from_url(url: str) -> tuple[float, float]:
    """helper function to extract coordinates from url"""
    try:
        coordinates = url.split('/@')[-1].split('/')[0]
        return float(coordinates.split(',')[0]), float(coordinates.split(',')[1])
    except:
        return None, None

def enhanced_scroll_to_load_all_results(page, max_attempts=30):
    """ULTRA-ENHANCED SCROLLING LOGIC - Loads ALL available results"""
    print("🔄 Starting ultra-enhanced scrolling to load ALL results...")

    # Wait for initial results to load
    page.wait_for_timeout(3000)

    # More aggressive scrolling strategies
    scroll_strategies = [
        {"method": "wheel", "distance": 5000, "wait": 2000},
        {"method": "wheel", "distance": 8000, "wait": 2500},
        {"method": "wheel", "distance": 12000, "wait": 3000},
        {"method": "key", "key": "PageDown", "wait": 1800},
        {"method": "wheel", "distance": 15000, "wait": 4000},
        {"method": "end_key", "wait": 2500},
    ]

    consecutive_same_count = 0
    previous_count = 0
    strategy_index = 0
    no_progress_cycles = 0
    max_consecutive_before_strategy_change = 2

    # Track the highest count we've seen to detect if we're truly stuck
    highest_count_seen = 0
    attempts_since_highest = 0

    for attempt in range(max_attempts):
        try:
            # Get current count of listings
            current_listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]')
            current_count = current_listings.count()

            print(f"📊 Attempt {attempt + 1}: Found {current_count} listings")

            # Check if we found any results at all
            if current_count == 0 and attempt < 5:
                print("⚠️ No listings found yet, waiting longer...")
                page.wait_for_timeout(5000)
                continue

            # Track highest count
            if current_count > highest_count_seen:
                highest_count_seen = current_count
                attempts_since_highest = 0
            else:
                attempts_since_highest += 1

            # Check for progress
            if current_count == previous_count:
                consecutive_same_count += 1
                print(f"🔄 No new results (consecutive: {consecutive_same_count})")
            else:
                consecutive_same_count = 0
                no_progress_cycles = 0
                print(f"✅ Progress: {current_count - previous_count} new listings loaded")

            previous_count = current_count

            # Advanced strategy switching
            if consecutive_same_count >= max_consecutive_before_strategy_change:
                print("🎯 Trying alternative scrolling strategies...")

                # Strategy 1: Rapid small scrolls with hover
                if no_progress_cycles == 0:
                    print("📜 Strategy 1: Rapid small scrolls + hover")
                    try:
                        if current_count > 0:
                            current_listings.first.hover()
                            page.wait_for_timeout(1000)

                        for i in range(8):
                            page.mouse.wheel(0, 2500)
                            page.wait_for_timeout(800)
                    except:
                        page.mouse.wheel(0, 15000)
                        page.wait_for_timeout(3000)

                # Strategy 2: Large scroll + show more buttons
                elif no_progress_cycles == 1:
                    print("📜 Strategy 2: Large scroll + show more buttons")
                    try:
                        page.mouse.wheel(0, 25000)
                        page.wait_for_timeout(4000)

                        # Look for "Show more results" buttons
                        show_more_selectors = [
                            "//button[contains(text(), 'Show more')]",
                            "//button[contains(text(), 'More results')]",
                            "//button[contains(text(), 'Load more')]",
                            "[data-value='Show more results']"
                        ]

                        for selector in show_more_selectors:
                            if page.locator(selector).count() > 0:
                                print("🔘 Found 'Show more' button, clicking...")
                                page.locator(selector).first.click()
                                page.wait_for_timeout(5000)
                                break

                    except Exception as e:
                        print(f"⚠️ Strategy 2 error: {e}")
                        page.mouse.wheel(0, 15000)
                        page.wait_for_timeout(3000)

                # Strategy 3: Keyboard navigation with End key
                elif no_progress_cycles == 2:
                    print("📜 Strategy 3: Keyboard End key navigation")
                    try:
                        if current_count > 0:
                            current_listings.first.click()
                            page.wait_for_timeout(1000)

                        for i in range(5):
                            page.keyboard.press("End")
                            page.wait_for_timeout(1500)
                            page.keyboard.press("PageDown")
                            page.wait_for_timeout(1500)
                    except:
                        page.mouse.wheel(0, 20000)
                        page.wait_for_timeout(4000)

                # Strategy 4: Multi-listing hover + scroll
                elif no_progress_cycles == 3:
                    print("📜 Strategy 4: Multi-listing hover + scroll")
                    try:
                        if current_count > 0:
                            visible_listings = current_listings.all()[:min(5, current_count)]
                            for i, listing in enumerate(visible_listings):
                                try:
                                    listing.hover()
                                    page.wait_for_timeout(500)
                                    page.mouse.wheel(0, 4000 + (i * 1000))
                                    page.wait_for_timeout(1200)
                                except:
                                    continue
                    except:
                        page.mouse.wheel(0, 18000)
                        page.wait_for_timeout(4000)

                # Strategy 5: Aggressive continuous scrolling
                elif no_progress_cycles == 4:
                    print("📜 Strategy 5: Aggressive continuous scroll")
                    for i in range(10):
                        scroll_distance = 3000 + (i * 500)
                        page.mouse.wheel(0, scroll_distance)
                        page.wait_for_timeout(1000)

                        temp_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                        if temp_count > current_count:
                            print(f"🎉 Mid-scroll progress detected: {temp_count} listings")
                            break

                no_progress_cycles += 1
                consecutive_same_count = 0

                if no_progress_cycles >= 6:
                    print("🏁 All advanced scrolling strategies exhausted")
                    break

            else:
                # Normal scrolling when making progress
                current_strategy = scroll_strategies[strategy_index % len(scroll_strategies)]

                if current_strategy["method"] == "wheel":
                    distance = current_strategy["distance"] + random.randint(-1000, 2000)
                    page.mouse.wheel(0, distance)

                elif current_strategy["method"] == "key":
                    for _ in range(4):
                        page.keyboard.press(current_strategy["key"])
                        page.wait_for_timeout(600)

                elif current_strategy["method"] == "end_key":
                    try:
                        page.keyboard.press("End")
                        page.wait_for_timeout(current_strategy["wait"])
                    except:
                        page.mouse.wheel(0, 15000)
                        page.wait_for_timeout(3000)

                strategy_index += 1
                wait_time = current_strategy["wait"] + random.randint(-300, 800)
                page.wait_for_timeout(wait_time)

            # Exit condition
            if attempts_since_highest >= 8 and current_count > 10:
                print(f"🎯 Stopping: No progress for {attempts_since_highest} attempts since highest count ({highest_count_seen})")
                break

        except Exception as e:
            print(f"⚠️ Error during scrolling attempt {attempt + 1}: {e}")
            try:
                page.mouse.wheel(0, 15000)
                page.wait_for_timeout(4000)
            except:
                pass
            continue

    # Final scroll attempt
    print("🔄 Final aggressive scroll attempt...")
    try:
        for i in range(5):
            page.mouse.wheel(0, 8000)
            page.wait_for_timeout(2000)
        page.wait_for_timeout(3000)
    except:
        pass

    # Final count
    final_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
    print(f"✅ Ultra-enhanced scrolling completed: {final_count} total listings found")

    return final_count

def extract_all_business_urls(page):
    """Extract all Google Maps business URLs from the current search results"""
    print("🔗 STEP 2: Extracting all business URLs...")

    try:
        # Get all Google Maps place URLs
        listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
        urls = []

        for listing in listings:
            try:
                href = listing.get_attribute("href")
                if href and "google.com/maps/place" in href:
                    urls.append(href)
            except Exception as e:
                print(f"⚠️ Error extracting URL from listing: {e}")
                continue

        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)

        print(f"✅ Extracted {len(unique_urls)} unique business URLs")
        return unique_urls

    except Exception as e:
        print(f"❌ Error extracting business URLs: {e}")
        return []

def scrape_business_from_url(page, url, state_name, business_index, total_count):
    """Scrape a single business by navigating directly to its URL"""
    try:
        print(f"🏢 Processing business {business_index + 1}/{total_count} from {state_name}")

        # Navigate directly to the business URL
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)

        # Verify we're on a business page
        if page.locator("//h1[contains(@class, 'DUwDvf')]").count() == 0:
            print(f"⚠️ Business details not loaded properly for URL: {url}")
            return None

        # XPaths for extracting business information
        name_xpath = "//h1[contains(@class, 'DUwDvf')]"
        address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
        website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
        phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
        review_count_xpath = '//button[contains(@jsaction, "reviewChart")]//span'
        reviews_average_xpath = '//div[@jsaction="pane.reviewChart.moreReviews"]//div[@role="img"]'

        business = Business()
        business.state = state_name
        business.google_maps_url = url

        # Extract business information
        if page.locator(name_xpath).count() > 0:
            business.name = page.locator(name_xpath).first.inner_text().strip()
        else:
            business.name = ""

        if page.locator(address_xpath).count() > 0:
            business.address = page.locator(address_xpath).first.inner_text().strip()
        else:
            business.address = ""

        if page.locator(website_xpath).count() > 0:
            business.website = page.locator(website_xpath).first.inner_text().strip()
        else:
            business.website = ""

        if page.locator(phone_number_xpath).count() > 0:
            business.phone_number = page.locator(phone_number_xpath).first.inner_text().strip()
        else:
            business.phone_number = ""

        # Extract review count
        if page.locator(review_count_xpath).count() > 0:
            try:
                review_text = page.locator(review_count_xpath).first.inner_text().strip()
                numbers = re.findall(r'\d+', review_text.replace(',', ''))
                if numbers:
                    business.reviews_count = int(numbers[0])
                else:
                    business.reviews_count = ""
            except Exception as e:
                business.reviews_count = ""
        else:
            business.reviews_count = ""

        # Extract average rating
        if page.locator(reviews_average_xpath).count() > 0:
            try:
                rating_text = page.locator(reviews_average_xpath).get_attribute("aria-label")
                if rating_text:
                    rating_match = re.search(r'(\d+[.,]\d+)', rating_text)
                    if rating_match:
                        business.reviews_average = float(rating_match.group(1).replace(',', '.'))
                    else:
                        business.reviews_average = ""
                else:
                    business.reviews_average = ""
            except:
                business.reviews_average = ""
        else:
            business.reviews_average = ""

        # Extract coordinates
        try:
            business.latitude, business.longitude = extract_coordinates_from_url(page.url)
        except:
            business.latitude = ""
            business.longitude = ""

        # Scrape reviews and images if business name exists
        if business.name:
            print(f"📝 Scraping reviews for: {business.name}")
            try:
                review_csv = scrape_reviews(page, business.name)
            except Exception as e:
                print(f"⚠️ Error scraping reviews: {e}")

            # Click overview tab before scraping images
            try:
                click_overview_tab(page)
            except:
                pass

            print(f"🖼️ Scraping images for: {business.name}")
            try:
                image_csv = scrape_images(page, business.name)
            except Exception as e:
                print(f"⚠️ Error scraping images: {e}")
        else:
            print("⚠️ Cannot scrape reviews or images — no business name")

        print(f"✅ Completed: {business.name or 'Unnamed Business'} ({business_index + 1}/{total_count}) [{state_name}]")
        return business

    except Exception as e:
        print(f'❌ Error processing business URL {url}: {e}')
        return None

def click_overview_tab(page):
    """Clicks the 'Overview' tab to return to main view"""
    try:
        overview_selectors = [
            "button[role='tab'] >> text=Overview",
            "div[role='tab'] >> text=Overview",
            "button[data-value='Overview']",
            "//button[@role='tab' and contains(text(), 'Overview')]",
            "//div[@role='tab' and contains(text(), 'Overview')]",
            "//button[contains(text(), 'Overview')]",
            "[data-tab-index='0']",
            "div[role='tablist'] button:first-child"
        ]

        for selector in overview_selectors:
            try:
                if page.locator(selector).count() > 0:
                    element = page.locator(selector).first
                    if element.is_visible():
                        element.click()
                        page.wait_for_timeout(1000)
                        print(f"✅ Clicked 'Overview' tab")
                        return True
            except Exception:
                continue

        return False

    except Exception as e:
        print(f"⚠️ Error clicking Overview tab: {e}")
        return False

def scrape_state_sod_farms_optimized(page, state_name, all_business_list):
    """OPTIMIZED: Scrape all sod farms from a specific state using URL-based approach"""
    search_term = f"sod farms in {state_name}"
    print(f"\n🏛️ ===========================================")
    print(f"🏛️ SCRAPING SOD FARMS IN {state_name.upper()}")
    print(f"🏛️ ===========================================")

    try:
        # Search for sod farms in the state
        search_box = page.locator('//input[@id="searchboxinput"]')
        search_box.click()
        page.wait_for_timeout(1000)
        search_box.press("Control+a")
        search_box.fill(search_term)
        page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

        # Check if there are any results
        if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() == 0:
            print(f"⚠️ No sod farms found in {state_name}")
            return

        print("📜 STEP 1: Loading all results with enhanced scrolling...")
        # STEP 1: Use enhanced scrolling to load ALL results (once)
        total_count = enhanced_scroll_to_load_all_results(page)

        if total_count == 0:
            print(f"⚠️ No sod farms loaded for {state_name}")
            return

        print(f"✅ Step 1 Complete: {total_count} sod farms found in {state_name}")

        # STEP 2: Extract all business URLs (once)
        business_urls = extract_all_business_urls(page)

        if not business_urls:
            print(f"⚠️ No business URLs extracted for {state_name}")
            return

        print(f"✅ Step 2 Complete: {len(business_urls)} business URLs extracted")

        print("🚀 STEP 3: Scraping businesses directly from URLs...")
        print("⚡ Using optimized URL-based approach (no more resets/re-scrolling!)")

        # STEP 3: Loop through URLs and scrape each business directly
        state_scraped_count = 0
        successful_businesses = []

        for index, url in enumerate(business_urls):
            try:
                business = scrape_business_from_url(page, url, state_name, index, len(business_urls))

                if business:
                    all_business_list.business_list.append(business)
                    successful_businesses.append(business)
                    state_scraped_count += 1
                else:
                    print(f"⚠️ Failed to scrape business {index + 1}")

            except Exception as e:
                print(f'❌ Error processing URL {index + 1} in {state_name}: {e}')
                continue

        print(f"🎉 Completed {state_name}: {state_scraped_count}/{len(business_urls)} sod farms scraped successfully")
        print(f"📊 Success rate: {(state_scraped_count/len(business_urls))*100:.1f}%")

        if state_scraped_count < len(business_urls):
            missed_count = len(business_urls) - state_scraped_count
            print(f"⚠️ Missed {missed_count} listings due to errors")

    except Exception as e:
        print(f"❌ Error scraping {state_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Scrape sod farms from all US states - OPTIMIZED VERSION")
    parser.add_argument("-s", "--search", type=str, help="Custom search term (optional, will scrape all states if not provided)")
    parser.add_argument("--states", nargs="+", help="Specific states to scrape (optional, will scrape all states if not provided)")
    parser.add_argument("--use-old-method", action="store_true", help="Use old click-based method instead of optimized URL method")
    args = parser.parse_args()

    # Determine what to scrape
    if args.search:
        search_list = [args.search]
        print(f"🎯 Custom search mode: '{args.search}'")
    elif args.states:
        search_list = [f"sod farms in {state}" for state in args.states]
        print(f"🏛️ Specific states mode: {', '.join(args.states)}")
    else:
        search_list = [f"sod farms in {state}" for state in US_STATES]
        print(f"🇺🇸 Full USA mode: All {len(US_STATES)} states")

    # Show optimization status
    if not args.use_old_method and not args.search:
        print("🚀 Using OPTIMIZED URL-based scraping method!")
        print("⚡ This will be much faster than the old click-and-reset method!")
    elif args.use_old_method:
        print("🐌 Using legacy click-based method (slower)")

    ###########
    # scraping
    ###########
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, proxy=PROXY)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        # Initialize master business list for all states
        master_business_list = BusinessList()

        if args.search:
            # Handle custom search (legacy behavior for now)
            print("Custom search logic - using traditional method")
            # Could implement URL-based optimization here too if needed
        else:
            # New optimized state-by-state scraping
            states_to_scrape = args.states if args.states else US_STATES

            start_time = time.time()

            for state_index, state_name in enumerate(states_to_scrape):
                print(f"\n{'='*60}")
                print(f"🏛️ STATE {state_index + 1}/{len(states_to_scrape)}: {state_name.upper()}")
                print(f"{'='*60}")

                state_start_time = time.time()

                # Use optimized method by default, fall back to old if requested
                if args.use_old_method:
                    print("🐌 Using legacy method...")
                    # scrape_state_sod_farms(page, state_name, master_business_list)  # Old method
                    print("Legacy method not implemented in this optimized version")
                else:
                    scrape_state_sod_farms_optimized(page, state_name, master_business_list)

                state_end_time = time.time()
                state_duration = state_end_time - state_start_time
                print(f"⏱️ {state_name} completed in {state_duration:.1f} seconds")

                # Save progress after each state
                try:
                    master_business_list.save_to_csv(f"all_usa_sod_farms_progress")
                    print(f"💾 Progress saved: {len(master_business_list.business_list)} total businesses so far")
                except Exception as e:
                    print(f"⚠️ Error saving progress: {e}")

                # Add delay between states
                if state_index < len(states_to_scrape) - 1:
                    print(f"⏱️ Waiting 10 seconds before next state...")
                    time.sleep(10)

            end_time = time.time()
            total_duration = end_time - start_time

            print(f"\n🎉 SCRAPING COMPLETED!")
            print(f"📊 Total sod farms scraped from all states: {len(master_business_list.business_list)}")
            print(f"⏱️ Total time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")

            if len(states_to_scrape) > 0:
                avg_time_per_state = total_duration / len(states_to_scrape)
                print(f"⚡ Average time per state: {avg_time_per_state:.1f} seconds")

            #########
            # final output
            #########
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            master_business_list.save_to_excel(f"all_usa_sod_farms_complete_{timestamp}")
            master_business_list.save_to_csv(f"all_usa_sod_farms_complete_{timestamp}")

            print(f"💾 Final files saved:")
            print(f"   - all_usa_sod_farms_complete_{timestamp}.xlsx")
            print(f"   - all_usa_sod_farms_complete_{timestamp}.csv")

        browser.close()

if __name__ == "__main__":
    main()