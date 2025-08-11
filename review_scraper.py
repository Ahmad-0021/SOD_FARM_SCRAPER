# review_scraper_ultra_fast.py
from patchright.sync_api import Page, TimeoutError
import time
import csv
import os
from urllib.parse import quote


def sanitize_filename(name: str) -> str:
    return quote(name.strip().replace(" ", "_"), safe="")


def extract_all_reviews_single_pass(page: Page) -> list:
    """ULTRA-FAST: Extract ALL reviews in a single JavaScript execution"""

    js_code = """
    () => {
        const reviews = [];
        const reviewBlocks = document.querySelectorAll('div.jJc9Ad');

        reviewBlocks.forEach((block, index) => {
            try {
                // Extract author
                const authorElement = block.querySelector('.d4r55');
                if (!authorElement) return;
                const author = authorElement.textContent.trim();

                // Extract rating
                let rating = null;
                const ratingElement = block.querySelector('.kvMYJc');
                if (ratingElement) {
                    const ratingAttr = ratingElement.getAttribute('aria-label') || '';
                    if (ratingAttr.toLowerCase().includes('star')) {
                        const ratingParts = ratingAttr.split(' ');
                        for (const part of ratingParts) {
                            if (part.replace('.', '').match(/^\\d+$/)) {
                                rating = parseFloat(part);
                                break;
                            }
                        }
                    }
                }

                // Extract review text and business response
                let customerReview = '';
                let businessResponse = '';

                const textElements = block.querySelectorAll('.wiI7pd');
                if (textElements.length >= 1) {
                    customerReview = textElements[0].textContent.trim();
                }
                if (textElements.length >= 2) {
                    businessResponse = textElements[1].textContent.trim();
                }

                // Fallback for review text
                if (!customerReview) {
                    const fallbackSelectors = ['.MyEned', '.ZZnUNe', 'span.wiI7pd'];
                    for (const selector of fallbackSelectors) {
                        const fallbackElement = block.querySelector(selector);
                        if (fallbackElement) {
                            customerReview = fallbackElement.textContent.trim();
                            break;
                        }
                    }
                }

                // Extract date
                let date = '';
                const dateElement = block.querySelector('.rsqaWe');
                if (dateElement) {
                    date = dateElement.textContent.trim();
                }

                // Add review if we have meaningful data
                if (author && customerReview) {
                    reviews.push({
                        reviewer_name: author,
                        rating: rating,
                        customer_review: customerReview,
                        business_response: businessResponse,
                        date: date,
                        block_index: index
                    });
                }

            } catch (error) {
                console.log('Error processing review:', error);
            }
        });

        return reviews;
    }
    """

    try:
        return page.evaluate(js_code)
    except Exception as e:
        print(f"⚠️ JavaScript review extraction failed: {e}")
        return []


def ultra_fast_scroll_and_extract_reviews(page: Page, scrollable) -> list:
    """ULTRA-FAST: Minimal scrolling with immediate review extraction"""
    all_reviews = []
    seen_review_keys = set()

    # PHASE 1: Initial extraction (no scroll)
    print("⚡ Phase 1: Initial review extraction...")
    initial_reviews = extract_all_reviews_single_pass(page)

    for review in initial_reviews:
        review_key = (review['reviewer_name'], review['customer_review'][:100], review['date'])
        if review_key not in seen_review_keys:
            seen_review_keys.add(review_key)
            all_reviews.append(review)

    print(f"   📝 Found {len(initial_reviews)} initial reviews")

    # PHASE 2: Quick scroll cycles (max 5 iterations)
    max_quick_scrolls = 5
    no_change_limit = 2
    consecutive_no_change = 0

    print("⚡ Phase 2: Quick scroll extraction...")

    for i in range(max_quick_scrolls):
        # Fast aggressive scroll
        try:
            scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
            time.sleep(2)  # Minimal wait for reviews to load
        except Exception as e:
            print(f"   ⚠️ Scroll failed: {e}")
            time.sleep(0.5)

        # Extract reviews
        new_reviews = extract_all_reviews_single_pass(page)
        new_count = 0

        for review in new_reviews:
            review_key = (review['reviewer_name'], review['customer_review'][:100], review['date'])
            if review_key not in seen_review_keys:
                seen_review_keys.add(review_key)
                all_reviews.append(review)
                new_count += 1

        print(f"   📍 Scroll {i + 1}: +{new_count} new reviews (Total: {len(all_reviews)})")

        # Early exit conditions
        if new_count == 0:
            consecutive_no_change += 1
            if consecutive_no_change >= no_change_limit:
                print("   ✅ No new reviews - stopping early")
                break
        else:
            consecutive_no_change = 0

        # Sufficient reviews collected
        if len(all_reviews) > 300:  # Reasonable limit for faster processing
            print("   ✅ Sufficient reviews collected")
            break

    return all_reviews


def scrape_reviews(page: Page, business_name: str, output_dir: str = "output/reviews"):
    """
    ULTRA-FAST review scraper - optimized for maximum speed
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/reviews_{sanitize_filename(business_name)}.csv"

    try:
        print("🚀 Starting ULTRA-FAST review collection...")
        start_time = time.time()

        # Step 1: Quick reviews tab detection and click
        print("🔍 Clicking 'Reviews' tab...")
        reviews_tab = page.locator("button[role='tab']:has-text('Reviews')")
        if reviews_tab.count() == 0:
            print("⚠️ Reviews tab not found")
            return filename

        reviews_tab.click()
        time.sleep(3)  # Reduced wait time

        # Step 2: Quick wait for first review
        try:
            page.wait_for_selector("div.jJc9Ad", timeout=12000)  # Reduced timeout
            print("✅ Reviews loaded")
        except TimeoutError:
            print("⚠️ No reviews loaded")
            return filename

        # Step 3: Quick scroll container detection
        scrollable = None
        possible_containers = [
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div[role='main'] div[style*='overflow']",
            "div.m6QErb[aria-label]",
        ]

        for container_selector in possible_containers:
            container = page.locator(container_selector).filter(has=page.locator("div.jJc9Ad")).first
            if container.count() > 0:
                scrollable = container
                print(f"✅ Found scroll container: {container_selector}")
                break

        if scrollable is None or scrollable.count() == 0:
            print("⚠️ Using body for scrolling")
            scrollable = page.locator("body")

        # Step 4: ULTRA-FAST extraction
        reviews_data = ultra_fast_scroll_and_extract_reviews(page, scrollable)

        elapsed = time.time() - start_time
        print(f"\n🎯 ULTRA-FAST collection completed in {elapsed:.1f}s!")
        print(f"📝 Total reviews collected: {len(reviews_data)}")

        # Step 5: Final deduplication and cleanup
        unique_reviews = []
        final_seen = set()

        for r in reviews_data:
            # Create unique key from reviewer name + review text + date
            review_key = (r["reviewer_name"], r["customer_review"][:100], r["date"])

            if review_key not in final_seen:
                final_seen.add(review_key)
                # Clean up the review data (remove block_index)
                clean_review = {
                    "reviewer_name": r["reviewer_name"],
                    "rating": r["rating"],
                    "customer_review": r["customer_review"],
                    "business_response": r["business_response"],
                    "date": r["date"]
                }
                unique_reviews.append(clean_review)

        print(f"📋 After deduplication: {len(unique_reviews)} unique reviews")

        # Step 6: Quick save
        if unique_reviews:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ["reviewer_name", "rating", "customer_review", "business_response", "date"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(unique_reviews)
            print(f"✅ Saved {len(unique_reviews)} reviews to {filename}")

            # Quick stats
            rating_counts = {}
            business_responses = 0

            for review in unique_reviews:
                rating = review["rating"] or "No rating"
                rating_counts[rating] = rating_counts.get(rating, 0) + 1
                if review["business_response"]:
                    business_responses += 1

            print(f"\n⭐ Rating summary: {dict(list(rating_counts.items())[:5])}")  # Top 5 ratings only
            print(f"💬 Business responses: {business_responses}/{len(unique_reviews)}")

            # Sample reviews (first 2 only for speed)
            print("\n📋 Sample reviews:")
            for i, review in enumerate(unique_reviews[:2]):
                text_preview = review["customer_review"][:80] + "..." if len(review["customer_review"]) > 80 else \
                review["customer_review"]
                rating_text = f"({review['rating']} stars)" if review['rating'] else "(No rating)"
                print(f"   {i + 1}. {review['reviewer_name']} {rating_text}: {text_preview}")

                if review["business_response"]:
                    response_preview = review["business_response"][:60] + "..." if len(
                        review["business_response"]) > 60 else review["business_response"]
                    print(f"      Business: {response_preview}")

        else:
            print("❌ No reviews extracted")
            # Minimal debugging
            debug_count = page.locator('div.jJc9Ad').count()
            print(f"🔍 Debug: Found {debug_count} review blocks")

    except Exception as e:
        print(f"❌ Error during ultra-fast review scraping: {e}")
        import traceback
        traceback.print_exc()

    return filename