# review_scraper.py
from playwright.sync_api import Page, TimeoutError
import time
import csv
import os
from urllib.parse import quote


def sanitize_filename(name: str) -> str:
    return quote(name.strip().replace(" ", "_"), safe="")


def scrape_reviews(page: Page, business_name: str, output_dir: str = "output/reviews"):
    reviews_data = []
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/reviews_{sanitize_filename(business_name)}.csv"

    try:
        print("🔍 Clicking 'Reviews' tab...")
        reviews_tab = page.locator("button[role='tab']:has-text('Reviews')")
        if reviews_tab.count() == 0:
            print("⚠️ Reviews tab not found")
            return

        reviews_tab.click()
        time.sleep(3)  # Increased wait time

        # Wait for first review to appear
        try:
            page.wait_for_selector("div.jJc9Ad", timeout=15000)  # Increased timeout
        except TimeoutError:
            print("⚠️ No reviews loaded")
            return

        # Get the correct scroll container - try multiple possible containers
        scrollable = None
        possible_containers = [
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",  # Your original
            "div[role='main'] div[style*='overflow']",  # Alternative
            "div.m6QErb[aria-label]",  # More specific
        ]

        for container_selector in possible_containers:
            scrollable = page.locator(container_selector).filter(has=page.locator("div.jJc9Ad")).first
            if scrollable.count() > 0:
                print(f"✅ Found scroll container with selector: {container_selector}")
                break

        if scrollable is None or scrollable.count() == 0:
            print("⚠️ Could not find reviews scroll container, trying page scroll")
            scrollable = page.locator("body")  # Fallback to page scroll

        # IMPROVED: More lenient conditions for getting all reviews
        max_iterations = 100  # Increased limit
        iteration = 0
        consecutive_no_change = 0
        max_no_change = 5  # Allow more attempts without new reviews

        # Track unique reviews as we go
        seen_reviews = set()
        last_review_count = 0

        print("🔄 Starting review collection...")

        while iteration < max_iterations:
            iteration += 1
            print(f"📍 Iteration {iteration}")

            # Multiple scroll attempts per iteration
            for scroll_attempt in range(3):  # Try scrolling 3 times per iteration
                try:
                    # Try different scroll methods
                    if scroll_attempt == 0:
                        # Scroll to bottom of container
                        scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
                    elif scroll_attempt == 1:
                        # Scroll by viewport height
                        scrollable.evaluate("el => el.scrollBy(0, window.innerHeight)")
                    else:
                        # Alternative scroll method
                        page.keyboard.press("End")

                    time.sleep(2)  # Wait for content to load
                except Exception as e:
                    print(f"⚠️ Scroll attempt {scroll_attempt + 1} failed: {e}")

            # Wait a bit more for any lazy-loaded content
            time.sleep(1)

            # Extract all current reviews
            review_blocks = page.locator("div.jJc9Ad").all()
            current_iteration_new = 0

            print(f"   Found {len(review_blocks)} review blocks on page")

            for i, block in enumerate(review_blocks):
                try:
                    # Extract author
                    author_element = block.locator(".d4r55")
                    if author_element.count() == 0:
                        continue
                    author = author_element.inner_text().strip()

                    # Extract rating
                    rating_element = block.locator(".kvMYJc")
                    rating = None
                    if rating_element.count() > 0:
                        rating_attr = rating_element.get_attribute("aria-label") or ""
                        if "star" in rating_attr.lower():
                            try:
                                # Extract number before "star"
                                rating_parts = rating_attr.split()
                                for part in rating_parts:
                                    if part.replace(".", "").isdigit():
                                        rating = float(part)
                                        break
                            except:
                                pass

                    # Extract review text - handle multiple possible selectors
                    text = ""
                    text_selectors = [".wiI7pd", ".MyEned", ".ZZnUNe"]  # Multiple possible text containers
                    for text_selector in text_selectors:
                        text_element = block.locator(text_selector)
                        if text_element.count() > 0:
                            text = text_element.inner_text().strip()
                            break

                    # Extract date
                    date_element = block.locator(".rsqaWe")
                    date = ""
                    if date_element.count() > 0:
                        date = date_element.inner_text().strip()

                    # Create unique key - use author + date + first 100 chars of text
                    review_key = (author, date, text[:100] if text else "")

                    if review_key not in seen_reviews and author:  # Must have author
                        seen_reviews.add(review_key)
                        reviews_data.append({
                            "reviewer_name": author,
                            "rating": rating,
                            "review_text": text,
                            "date": date
                        })
                        current_iteration_new += 1

                except Exception as e:
                    print(f"   ⚠️ Error processing review {i + 1}: {e}")
                    continue

            current_total = len(reviews_data)
            print(f"   📊 Total reviews: {current_total} (+{current_iteration_new} new)")

            # Check for stopping conditions
            if current_total == last_review_count:
                consecutive_no_change += 1
                print(f"   ⏳ No new reviews ({consecutive_no_change}/{max_no_change})")

                if consecutive_no_change >= max_no_change:
                    print("✅ No new reviews found after multiple attempts - likely reached end")
                    break
            else:
                consecutive_no_change = 0  # Reset counter
                last_review_count = current_total

            # Optional: Stop if we have a very large number
            if current_total > 2000:
                print(f"✅ Collected {current_total} reviews - stopping to prevent excessive data")
                break

        print(f"\n🎯 Scraping completed after {iteration} iterations")
        print(f"📝 Total unique reviews collected: {len(reviews_data)}")

        # Final deduplication (extra safety)
        final_seen = set()
        unique_reviews = []
        for r in reviews_data:
            key = (r["reviewer_name"], r["date"], r["review_text"][:100])
            if key not in final_seen:
                final_seen.add(key)
                unique_reviews.append(r)

        # Save to CSV
        if unique_reviews:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=["reviewer_name", "rating", "review_text", "date"])
                writer.writeheader()
                writer.writerows(unique_reviews)
            print(f"✅ Saved {len(unique_reviews)} unique reviews to {filename}")

            # Print sample of what was collected
            print("\n📋 Sample reviews:")
            for i, review in enumerate(unique_reviews[:3]):
                text_preview = review["review_text"][:100] + "..." if len(review["review_text"]) > 100 else review[
                    "review_text"]
                print(f"   {i + 1}. {review['reviewer_name']} ({review['rating']} stars): {text_preview}")

        else:
            print("❌ No reviews extracted")

    except Exception as e:
        print(f"❌ Error scraping reviews: {e}")
        import traceback
        traceback.print_exc()

    return filename