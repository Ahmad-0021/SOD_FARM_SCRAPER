# review_scraper.py - EFFICIENT VERSION
from patchright.sync_api import Page, TimeoutError
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
        time.sleep(3)

        # Wait for first review to appear
        try:
            page.wait_for_selector("div.jJc9Ad", timeout=15000)
        except TimeoutError:
            print("⚠️ No reviews loaded")
            return

        # Get the correct scroll container
        scrollable = None
        possible_containers = [
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div[role='main'] div[style*='overflow']",
            "div.m6QErb[aria-label]",
        ]

        for container_selector in possible_containers:
            scrollable = page.locator(container_selector).filter(has=page.locator("div.jJc9Ad")).first
            if scrollable.count() > 0:
                print(f"✅ Found scroll container with selector: {container_selector}")
                break

        if scrollable is None or scrollable.count() == 0:
            print("⚠️ Could not find reviews scroll container, trying page scroll")
            scrollable = page.locator("body")

        # OPTIMIZED: Much more efficient approach
        processed_reviews = set()  # Track which review indices we've already processed
        max_iterations = 10  # REDUCED from 100
        iteration = 0
        consecutive_no_change = 0
        max_no_change = 2  # REDUCED from 5

        print("🔄 Starting efficient review collection...")

        while iteration < max_iterations:
            iteration += 1

            # Get current review count BEFORE scrolling
            current_review_blocks = page.locator("div.jJc9Ad").all()
            reviews_before_scroll = len(current_review_blocks)

            print(f"📍 Iteration {iteration}: {reviews_before_scroll} review blocks visible")

            # SINGLE efficient scroll per iteration
            try:
                scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
                time.sleep(3)  # Wait for new content to load
            except Exception as e:
                print(f"⚠️ Scroll failed: {e}")

            # Check if new reviews loaded
            updated_review_blocks = page.locator("div.jJc9Ad").all()
            reviews_after_scroll = len(updated_review_blocks)

            if reviews_after_scroll == reviews_before_scroll:
                consecutive_no_change += 1
                print(f"   ⏳ No new reviews loaded ({consecutive_no_change}/{max_no_change})")

                if consecutive_no_change >= max_no_change:
                    print("✅ No new reviews loading - stopping")
                    break
            else:
                consecutive_no_change = 0
                print(f"   📈 New reviews loaded: {reviews_before_scroll} → {reviews_after_scroll}")

            # OPTIMIZED: Only process NEW reviews (not all reviews again)
            new_reviews_processed = 0

            for i in range(len(updated_review_blocks)):
                # Skip if we already processed this review index
                if i in processed_reviews:
                    continue

                block = updated_review_blocks[i]
                try:
                    # Extract author
                    author_element = block.locator(".d4r55")
                    if author_element.count() == 0:
                        continue
                    author = author_element.first.inner_text().strip()

                    # Extract rating
                    rating_element = block.locator(".kvMYJc")
                    rating = None
                    if rating_element.count() > 0:
                        rating_attr = rating_element.first.get_attribute("aria-label") or ""
                        if "star" in rating_attr.lower():
                            try:
                                rating_parts = rating_attr.split()
                                for part in rating_parts:
                                    if part.replace(".", "").isdigit():
                                        rating = float(part)
                                        break
                            except:
                                pass

                    # Handle multiple text elements properly
                    customer_review = ""
                    business_response = ""

                    text_elements = block.locator(".wiI7pd").all()

                    if len(text_elements) >= 1:
                        customer_review = text_elements[0].inner_text().strip()

                    if len(text_elements) >= 2:
                        business_response = text_elements[1].inner_text().strip()

                    # Fallback for review text
                    if not customer_review:
                        fallback_selectors = [".MyEned", ".ZZnUNe", "span.wiI7pd"]
                        for text_selector in fallback_selectors:
                            text_element = block.locator(text_selector)
                            if text_element.count() > 0:
                                customer_review = text_element.first.inner_text().strip()
                                break

                    # Extract date
                    date_element = block.locator(".rsqaWe")
                    date = ""
                    if date_element.count() > 0:
                        date = date_element.first.inner_text().strip()

                    # Add review if we have meaningful data
                    if author and customer_review:
                        reviews_data.append({
                            "reviewer_name": author,
                            "rating": rating,
                            "customer_review": customer_review,
                            "business_response": business_response,
                            "date": date
                        })

                        processed_reviews.add(i)  # Mark this review index as processed
                        new_reviews_processed += 1

                except Exception as e:
                    print(f"   ⚠️ Error processing review {i + 1}: {e}")
                    continue

            print(f"   ✅ Processed {new_reviews_processed} new reviews (Total: {len(reviews_data)})")

            # Safety limit
            if len(reviews_data) > 1000:
                print(f"✅ Collected {len(reviews_data)} reviews - reasonable limit reached")
                break

        print(f"\n🎯 Scraping completed after {iteration} iterations")
        print(f"📝 Total reviews collected: {len(reviews_data)}")

        # Final deduplication based on content (not just index)
        final_seen = set()
        unique_reviews = []

        for r in reviews_data:
            # Create unique key from reviewer name + review text
            review_key = (r["reviewer_name"], r["customer_review"][:100], r["date"])

            if review_key not in final_seen:
                final_seen.add(review_key)
                unique_reviews.append(r)

        print(f"📋 After deduplication: {len(unique_reviews)} unique reviews")

        # Save to CSV
        if unique_reviews:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ["reviewer_name", "rating", "customer_review", "business_response", "date"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(unique_reviews)
            print(f"✅ Saved {len(unique_reviews)} unique reviews to {filename}")

            # Show rating distribution
            rating_counts = {}
            for review in unique_reviews:
                rating = review["rating"] or "No rating"
                rating_counts[rating] = rating_counts.get(rating, 0) + 1

            print("\n⭐ Rating Distribution:")
            for rating, count in sorted(rating_counts.items(), reverse=True):
                print(f"   {rating}: {count} reviews")

            # Print sample of what was collected
            print("\n📋 Sample reviews:")
            for i, review in enumerate(unique_reviews[:3]):
                text_preview = review["customer_review"][:100] + "..." if len(review["customer_review"]) > 100 else \
                review["customer_review"]
                print(f"   {i + 1}. {review['reviewer_name']} ({review['rating']} stars): {text_preview}")
                if review["business_response"]:
                    response_preview = review["business_response"][:80] + "..." if len(
                        review["business_response"]) > 80 else review["business_response"]
                    print(f"      Business replied: {response_preview}")

        else:
            print("❌ No reviews extracted")

    except Exception as e:
        print(f"❌ Error scraping reviews: {e}")
        import traceback
        traceback.print_exc()

    return filename