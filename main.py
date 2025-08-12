"""This script scrapes all sod farms from every city in every US state using Google Maps - CITY-WISE OPTIMIZED VERSION"""
from dotenv import load_dotenv
from patchright.sync_api import sync_playwright, ProxySettings
from dataclasses import dataclass, asdict, field
from review_scraper import scrape_reviews
from image_scraper import scrape_images
from cities_data import US_CITIES_BY_STATE, US_STATES  # Import from separate file
import pandas as pd
import argparse
import os
import time
import random
import re

load_dotenv()

PROXY: ProxySettings = {
    "server": f"http://{os.getenv('PROXY_HOST')}:{os.getenv('PROXY_PORT')}",
    "username": os.getenv("PROXY_USERNAME"),
    "password": os.getenv("PROXY_PASSWORD")
}

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
    city: str = None  # Added city field
    google_maps_url: str = None
    category:str = None

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


def extract_categories_from_url(url: str) -> str:
    """Extract business category based on URL content"""
    try:
        url_lower = url.lower()

        # Check for specific keywords in URL
        if "sod" in url_lower or "turf" in url_lower:
            return "sod supplier"
        elif "grass" in url_lower:
            return "grass store"
        elif "landscape" in url_lower or "landscaping" in url_lower:
            return "landscape supplier"
        elif "nursery" in url_lower:
            return "nursery"
        elif "garden" in url_lower:
            return "garden center"
        else:
            return "others"
    except Exception as e:
        print(f"⚠️ Error extracting category: {e}")
        return "unknown"

def enhanced_scroll_to_load_all_results(page, max_attempts=25):
    """ULTRA-ENHANCED SCROLLING LOGIC - Loads ALL available results"""
    print("🔄 Starting enhanced scrolling to load ALL results...")

    # Wait for initial results to load
    page.wait_for_timeout(3000)

    consecutive_same_count = 0
    previous_count = 0
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
            if current_count == 0 and attempt < 3:
                print("⚠️ No listings found yet, waiting longer...")
                page.wait_for_timeout(3000)
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

            # Strategy switching for stuck situations
            if consecutive_same_count >= max_consecutive_before_strategy_change:
                print("🎯 Trying alternative scrolling strategies...")

                if no_progress_cycles == 0:
                    # Strategy 1: Rapid small scrolls
                    print("📜 Strategy 1: Rapid small scrolls")
                    for i in range(6):
                        page.mouse.wheel(0, 2000)
                        page.wait_for_timeout(800)

                elif no_progress_cycles == 1:
                    # Strategy 2: Large scroll + wait
                    print("📜 Strategy 2: Large scroll")
                    page.mouse.wheel(0, 15000)
                    page.wait_for_timeout(4000)

                elif no_progress_cycles == 2:
                    # Strategy 3: End key navigation
                    print("📜 Strategy 3: End key navigation")
                    try:
                        for i in range(3):
                            page.keyboard.press("End")
                            page.wait_for_timeout(1500)
                    except:
                        page.mouse.wheel(0, 10000)
                        page.wait_for_timeout(3000)

                else:
                    # Strategy 4: Final aggressive scroll
                    print("📜 Strategy 4: Final aggressive scroll")
                    for i in range(5):
                        page.mouse.wheel(0, 5000 + (i * 1000))
                        page.wait_for_timeout(1000)

                no_progress_cycles += 1
                consecutive_same_count = 0

                if no_progress_cycles >= 4:
                    print("🏁 All scrolling strategies exhausted")
                    break

            else:
                # Normal scrolling when making progress
                scroll_distance = 4000 + random.randint(-1000, 2000)
                page.mouse.wheel(0, scroll_distance)
                page.wait_for_timeout(2000 + random.randint(-300, 800))

            # Exit condition - for city searches, be less aggressive
            if attempts_since_highest >= 6 and current_count > 5:
                print(f"🎯 Stopping: No progress for {attempts_since_highest} attempts since highest count ({highest_count_seen})")
                break

        except Exception as e:
            print(f"⚠️ Error during scrolling attempt {attempt + 1}: {e}")
            try:
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(3000)
            except:
                pass
            continue

    # Final count
    final_count = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
    print(f"✅ Enhanced scrolling completed: {final_count} total listings found")

    return final_count

def extract_all_business_urls(page):
    """Extract all Google Maps business URLs from the current search results"""
    print("🔗 Extracting all business URLs...")

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


def  scrape_business_from_url(page, url, state_name, city_name, business_index, total_count):
    """Scrape a single business by navigating directly to its URL"""
    try:
        print(f"🏢 Processing business {business_index + 1}/{total_count} from {city_name}, {state_name}")

        # Navigate directly to the business URL
        page.goto(url, timeout=30000)
        page.wait_for_timeout(2500)

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
        business.city = city_name
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

        # Extract and assign category - FIXED VERSION
        try:
            business.category = extract_categories_from_url(page.url)
            print(f"📋 Category assigned: {business.category}")
        except Exception as e:
            print(f"⚠️ Error extracting category: {e}")
            business.category = "unknown"

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

        print(
            f"✅ Completed: {business.name or 'Unnamed Business'} ({business_index + 1}/{total_count}) [{city_name}, {state_name}] - Category: {business.category}")
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

def scrape_city_sod_farms_optimized(page, state_name, city_name, all_business_list, all_scraped_urls):
    """OPTIMIZED: Scrape all sod farms from a specific city using URL-based approach"""
    search_term = f"sod farms in {city_name}, {state_name}"
    print(f"\n🏙️ ===========================================")
    print(f"🏙️ SCRAPING SOD FARMS IN {city_name.upper()}, {state_name.upper()}")
    print(f"🏙️ ===========================================")

    try:
        # Search for sod farms in the city
        search_box = page.locator('//input[@id="searchboxinput"]')
        search_box.click()
        page.wait_for_timeout(1000)
        search_box.press("Control+a")
        search_box.fill(search_term)
        page.keyboard.press("Enter")
        page.wait_for_timeout(4000)

        # Check if there are any results
        if page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count() == 0:
            print(f"⚠️ No sod farms found in {city_name}, {state_name}")
            return 0

        print("📜 STEP 1: Loading all results with enhanced scrolling...")
        # STEP 1: Use enhanced scrolling to load ALL results (once)
        total_count = enhanced_scroll_to_load_all_results(page)

        if total_count == 0:
            print(f"⚠️ No sod farms loaded for {city_name}, {state_name}")
            return 0

        print(f"✅ Step 1 Complete: {total_count} sod farms found in {city_name}, {state_name}")

        # STEP 2: Extract all business URLs (once)
        business_urls = extract_all_business_urls(page)

        if not business_urls:
            print(f"⚠️ No business URLs extracted for {city_name}, {state_name}")
            return 0

        # Filter out already scraped URLs to avoid duplicates
        new_urls = []
        for url in business_urls:
            if url not in all_scraped_urls:
                new_urls.append(url)
                all_scraped_urls.add(url)
            else:
                print(f"🔄 Skipping duplicate URL: {url}")

        if not new_urls:
            print(f"⚠️ All URLs from {city_name}, {state_name} were already scraped")
            return 0

        print(f"✅ Step 2 Complete: {len(new_urls)} new business URLs extracted (filtered {len(business_urls) - len(new_urls)} duplicates)")

        print("🚀 STEP 3: Scraping businesses directly from URLs...")

        # STEP 3: Loop through URLs and scrape each business directly
        city_scraped_count = 0
        successful_businesses = []

        for index, url in enumerate(new_urls):
            try:
                business = scrape_business_from_url(page, url, state_name, city_name, index, len(new_urls))

                if business:
                    all_business_list.business_list.append(business)
                    successful_businesses.append(business)
                    city_scraped_count += 1
                else:
                    print(f"⚠️ Failed to scrape business {index + 1}")

            except Exception as e:
                print(f'❌ Error processing URL {index + 1} in {city_name}, {state_name}: {e}')
                continue

        print(f"🎉 Completed {city_name}, {state_name}: {city_scraped_count}/{len(new_urls)} sod farms scraped successfully")

        if len(new_urls) > 0:
            print(f"📊 Success rate: {(city_scraped_count/len(new_urls))*100:.1f}%")

        return city_scraped_count

    except Exception as e:
        print(f"❌ Error scraping {city_name}, {state_name}: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Scrape sod farms from all cities in all US states - CITY-WISE OPTIMIZED VERSION")
    parser.add_argument("-s", "--search", type=str, help="Custom search term (optional)")
    parser.add_argument("--states", nargs="+", help="Specific states to scrape (optional)")
    parser.add_argument("--cities", nargs="+", help="Specific cities to scrape (requires --state)")
    parser.add_argument("--state", type=str, help="State for specific cities (used with --cities)")
    parser.add_argument("--max-cities-per-state", type=int, default=None, help="Maximum cities to scrape per state")
    args = parser.parse_args()

    # Validation for city-specific searches
    if args.cities and not args.state:
        print("❌ Error: --cities requires --state to be specified")
        return

    # Determine what to scrape
    if args.search:
        print(f"🎯 Custom search mode: '{args.search}'")
        print("⚠️ Note: Custom search will use legacy method, not city-wise optimization")
    elif args.cities and args.state:
        if args.state not in US_CITIES_BY_STATE:
            print(f"❌ Error: State '{args.state}' not found in city database")
            return
        print(f"🏙️ Specific cities mode: {', '.join(args.cities)} in {args.state}")
    elif args.states:
        print(f"🏛️ Specific states mode: {', '.join(args.states)}")
        if args.max_cities_per_state:
            print(f"📊 Limited to {args.max_cities_per_state} cities per state")
    else:
        print(f"🇺🇸 Full USA city-wise mode: All cities in all {len(US_CITIES_BY_STATE)} states")
        if args.max_cities_per_state:
            print(f"📊 Limited to {args.max_cities_per_state} cities per state")

    print("🚀 Using CITY-WISE OPTIMIZED URL-based scraping method!")
    print("⚡ This will provide maximum coverage by searching each city individually!")

    ###########
    # scraping
    ###########
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, proxy=PROXY)
        page = browser.new_page()

        page.goto("https://www.google.com/maps", timeout=60000)
        page.wait_for_timeout(5000)

        # Initialize master business list for all cities
        master_business_list = BusinessList()
        all_scraped_urls = set()  # Track scraped URLs to avoid duplicates

        if args.search:
            # Handle custom search (legacy behavior)
            print("Custom search logic - using traditional method")
            # Custom search implementation would go here
            print("⚠️ Custom search mode not implemented in this city-wise version")

        else:
            # New city-wise scraping
            if args.cities and args.state:
                # Scrape specific cities in specific state
                states_to_scrape = {args.state: tuple(args.cities)}
            elif args.states:
                # Scrape specific states
                states_to_scrape = {}
                for state in args.states:
                    if state in US_CITIES_BY_STATE:
                        cities = US_CITIES_BY_STATE[state]
                        if args.max_cities_per_state:
                            cities = cities[:args.max_cities_per_state]
                        states_to_scrape[state] = cities
                    else:
                        print(f"⚠️ Warning: State '{state}' not found in city database")
            else:
                # Scrape all states and cities
                states_to_scrape = {}
                for state, cities in US_CITIES_BY_STATE.items():
                    if args.max_cities_per_state:
                        cities = cities[:args.max_cities_per_state]
                    states_to_scrape[state] = cities

            start_time = time.time()
            total_states = len(states_to_scrape)
            total_cities = sum(len(cities) for cities in states_to_scrape.values())
            total_scraped_businesses = 0

            print(f"\n🌟 STARTING CITY-WISE SCRAPING:")
            print(f"📊 Total states to process: {total_states}")
            print(f"🏙️ Total cities to process: {total_cities}")
            print(f"{'='*80}")

            state_index = 0
            city_global_index = 0

            for state_name, cities in states_to_scrape.items():
                state_index += 1
                print(f"\n{'='*80}")
                print(f"🏛️ STATE {state_index}/{total_states}: {state_name.upper()}")
                print(f"🏙️ Cities to process in {state_name}: {len(cities)}")
                print(f"{'='*80}")

                state_start_time = time.time()
                state_scraped_businesses = 0

                for city_index, city_name in enumerate(cities):
                    city_global_index += 1
                    print(f"\n🏙️ CITY {city_index + 1}/{len(cities)} in {state_name} (Global: {city_global_index}/{total_cities})")

                    city_start_time = time.time()

                    # Scrape this specific city
                    city_scraped_count = scrape_city_sod_farms_optimized(
                        page, state_name, city_name, master_business_list, all_scraped_urls
                    )

                    state_scraped_businesses += city_scraped_count
                    total_scraped_businesses += city_scraped_count

                    city_end_time = time.time()
                    city_duration = city_end_time - city_start_time

                    print(f"⏱️ {city_name}, {state_name} completed in {city_duration:.1f} seconds")
                    print(f"📊 Running totals: {total_scraped_businesses} businesses from {city_global_index} cities")

                    # Save progress after each city (optional - can be removed for performance)
                    if city_scraped_count > 0:
                        try:
                            master_business_list.save_to_csv(f"all_usa_sod_farms_citywise_progress")
                            print(f"💾 Progress saved")
                        except Exception as e:
                            print(f"⚠️ Error saving progress: {e}")

                    # Add small delay between cities to be respectful
                    if city_index < len(cities) - 1:
                        print(f"⏱️ Waiting 5 seconds before next city...")
                        time.sleep(5)

                state_end_time = time.time()
                state_duration = state_end_time - state_start_time

                print(f"\n🎉 STATE COMPLETED: {state_name}")
                print(f"📊 {state_name} Results: {state_scraped_businesses} sod farms from {len(cities)} cities")
                print(f"⏱️ {state_name} Duration: {state_duration:.1f} seconds ({state_duration/60:.1f} minutes)")

                if len(cities) > 0:
                    avg_time_per_city = state_duration / len(cities)
                    print(f"⚡ Average time per city in {state_name}: {avg_time_per_city:.1f} seconds")

                # Save state progress
                try:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    master_business_list.save_to_csv(f"sod_farms_{state_name.lower().replace(' ', '_')}_{timestamp}")
                    print(f"💾 {state_name} data saved")
                except Exception as e:
                    print(f"⚠️ Error saving {state_name} data: {e}")

                # Add delay between states
                if state_index < total_states:
                    print(f"⏱️ Waiting 15 seconds before next state...")
                    time.sleep(15)

            end_time = time.time()
            total_duration = end_time - start_time

            print(f"\n🎉🎉🎉 CITY-WISE SCRAPING COMPLETED! 🎉🎉🎉")
            print(f"{'='*80}")
            print(f"📊 FINAL STATISTICS:")
            print(f"🏛️ States processed: {total_states}")
            print(f"🏙️ Cities processed: {total_cities}")
            print(f"🏢 Total sod farms scraped: {total_scraped_businesses}")
            print(f"⏱️ Total time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")

            if total_cities > 0:
                avg_time_per_city = total_duration / total_cities
                print(f"⚡ Average time per city: {avg_time_per_city:.1f} seconds")

            if total_scraped_businesses > 0 and total_cities > 0:
                avg_businesses_per_city = total_scraped_businesses / total_cities
                print(f"📈 Average sod farms per city: {avg_businesses_per_city:.1f}")

            # Check for duplicates in final data
            unique_urls_in_data = set()
            duplicates_found = 0
            for business in master_business_list.business_list:
                if business.google_maps_url in unique_urls_in_data:
                    duplicates_found += 1
                else:
                    unique_urls_in_data.add(business.google_maps_url)

            if duplicates_found > 0:
                print(f"⚠️ Warning: {duplicates_found} duplicate businesses found in final data")
            else:
                print(f"✅ No duplicates found in final data")

            print(f"{'='*80}")

            #########
            # final output
            #########
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            final_filename_base = f"all_usa_sod_farms_citywise_complete_{timestamp}"

            master_business_list.save_to_excel(final_filename_base)
            master_business_list.save_to_csv(final_filename_base)

            print(f"💾 FINAL FILES SAVED:")
            print(f"   📄 {final_filename_base}.xlsx")
            print(f"   📄 {final_filename_base}.csv")
            print(f"📁 Location: ./output/ directory")

        browser.close()

if __name__ == "__main__":
    main()