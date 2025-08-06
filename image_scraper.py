# image_scraper.py
from playwright.sync_api import Page, TimeoutError
import time
import csv
import os
from urllib.parse import quote, urlparse
import re


def sanitize_filename(name: str) -> str:
    return quote(name.strip().replace(" ", "_"), safe="")


def clean_image_url(url: str) -> str:
    """Clean and get the highest quality version of Google Images URL"""
    if not url or not url.startswith("http"):
        return url

    try:
        # Remove Google's resizing parameters to get full-size images
        url = re.sub(r'=w\d+-h\d+', '=w2000-h2000', url)
        url = re.sub(r'=s\d+', '=s2000', url)
        url = re.sub(r'=c-[^&]*', '', url)
        # Remove -k-no suffix for higher quality
        url = re.sub(r'-k-no$', '', url)
        return url
    except:
        return url


def extract_background_image_url(style_attr: str) -> str:
    """Extract URL from background-image CSS property"""
    if not style_attr:
        return ""

    # Match background-image: url("...") or url('...')
    match = re.search(r'background-image:\s*url\(["\']?(.*?)["\']?\)', style_attr)
    if match:
        return match.group(1)
    return ""


def scrape_images(page: Page, business_name: str, output_dir: str = "output/images"):
    """
    Enhanced image scraper that handles Google Maps photo galleries with div background images
    """
    image_urls = []
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/images_{sanitize_filename(business_name)}.csv"

    try:
        print("🖼️ Starting image collection process...")

        # Step 1: Look for photo count/button indicators first
        photo_indicators = [
            '[data-value="all_photos"]',
            'button[data-carousel-index="0"]',
            'button:has-text("photos")',
            'button:has-text("Photo")',
            '[role="button"]:has-text("Photo")',
            '.photos-section button',
            '[aria-label*="photo" i]',
        ]

        photos_button = None
        for selector in photo_indicators:
            button = page.locator(selector)
            if button.count() > 0:
                photos_button = button.first
                print(f"✅ Found photos section with: {selector}")
                break

        # Step 2: Try to click photos button if found
        if photos_button:
            try:
                photos_button.click()
                print("📸 Clicked photos button")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ Could not click photos button: {e}")
        else:
            print("⚠️ No specific photos button found, looking for images directly")

        # Step 3: Wait for images to appear with multiple strategies
        images_loaded = False
        wait_selectors = [
            'div[role="img"]',  # Your specific structure
            'div.U39Pmb[role="img"]',  # Even more specific
            'div.Uf0tqf',  # The inner div with background image
            'img[src*="googleusercontent.com"]',
            'img[src*="gstatic.com"]',
            'img[src*="ggpht.com"]',
            'img.DaSXdd',
            '[role="img"] img',
            'img[src^="https://lh"]',
            'img[data-src]',
            'picture img',
        ]

        for selector in wait_selectors:
            try:
                page.wait_for_selector(selector, timeout=3000)
                images_loaded = True
                print(f"✅ Images detected with: {selector}")
                break
            except TimeoutError:
                continue

        if not images_loaded:
            print("⚠️ No images detected, continuing anyway...")

        # Step 4: Advanced scrolling strategy
        max_iterations = 200  # Increased for more thorough scraping
        iteration = 0
        consecutive_no_change = 0
        max_no_change = 15  # Increased patience

        seen_urls = set()
        last_image_count = 0

        print("🔄 Starting comprehensive image collection...")

        # Try to find the best scroll container
        scroll_containers = [
            # Most specific first
            "div[role='main'] div[style*='overflow-y']",
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div[class*='scroll']",
            "[role='main']",
            "body"
        ]

        active_container = page.locator("body")  # default fallback
        for container_sel in scroll_containers:
            container = page.locator(container_sel)
            if container.count() > 0:
                active_container = container.first
                print(f"🎯 Using scroll container: {container_sel}")
                break

        while iteration < max_iterations:
            iteration += 1

            if iteration % 15 == 0:  # Show progress every 15 iterations
                print(f"📍 Iteration {iteration}/{max_iterations}")

            # Enhanced scrolling - try multiple methods
            scroll_methods = [
                lambda: active_container.evaluate("el => el.scrollTop = el.scrollHeight"),
                lambda: active_container.evaluate("el => el.scrollBy(0, 800)"),
                lambda: page.keyboard.press("PageDown"),
                lambda: page.keyboard.press("End"),
                lambda: page.evaluate("window.scrollBy(0, 1200)"),
                lambda: page.mouse.wheel(0, 600),
                # More aggressive scrolling
                lambda: page.evaluate("window.scrollTo(0, document.body.scrollHeight)"),
            ]

            # Use different scroll methods per iteration
            method_index = iteration % len(scroll_methods)
            try:
                scroll_methods[method_index]()
                time.sleep(1.2)  # Slightly longer wait for loading
            except:
                pass

            # Additional scroll for good measure
            try:
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(0.5)
            except:
                pass

            # Step 5: Comprehensive image extraction including background images
            current_new = 0

            # PRIORITY: Handle div elements with background-image (your specific case)
            background_image_selectors = [
                'div[role="img"][style*="background-image"]',  # Your exact case
                'div.U39Pmb[role="img"]',  # Your specific class
                'div.Uf0tqf[style*="background-image"]',  # Inner div with background
                'div[style*="background-image"][style*="googleusercontent"]',
                'div[style*="background-image"][style*="gstatic"]',
                'div[style*="background-image"][style*="ggpht"]',
            ]

            # Traditional img tag selectors
            img_tag_selectors = [
                'img[src*="googleusercontent.com"]',
                'img[src*="gstatic.com"]',
                'img[src*="ggpht.com"]',
                'img[src^="https://lh"]',
                'img.DaSXdd',
                'img[data-src*="google"]',
                'picture img',
                '[role="img"] img',
                'img[src^="data:image"]',
                'img[loading="lazy"]',
                'img[alt*="photo" i]',
            ]

            all_elements = set()

            # Process background image elements FIRST (highest priority)
            for selector in background_image_selectors:
                try:
                    elements = page.locator(selector).all()
                    for element in elements:
                        try:
                            style_attr = element.get_attribute("style")
                            if style_attr and "background-image" in style_attr:
                                bg_url = extract_background_image_url(style_attr)
                                if bg_url and bg_url.startswith('http'):
                                    # Skip very small images
                                    if any(bad in bg_url.lower() for bad in [
                                        '=s40', '=s60', '=w40', '=w60', '=h40', '=h60',
                                        'icon', 'logo', 'avatar', '1x1', 'pixel'
                                    ]):
                                        continue

                                    clean_url = clean_image_url(bg_url)

                                    if clean_url not in seen_urls:
                                        seen_urls.add(clean_url)

                                        # Try to get dimensions from style
                                        width_match = re.search(r'width:\s*(\d+)px', style_attr)
                                        height_match = re.search(r'height:\s*(\d+)px', style_attr)
                                        width = width_match.group(1) if width_match else ""
                                        height = height_match.group(1) if height_match else ""

                                        image_urls.append({
                                            "image_url": clean_url,
                                            "alt_text": f"Background image from {selector}",
                                            "original_url": bg_url,
                                            "width": width,
                                            "height": height,
                                            "source_type": "background-image"
                                        })
                                        current_new += 1

                                # Also check child elements for nested background images
                                child_divs = element.locator('div[style*="background-image"]').all()
                                for child in child_divs:
                                    child_style = child.get_attribute("style")
                                    if child_style and "background-image" in child_style:
                                        child_bg_url = extract_background_image_url(child_style)
                                        if child_bg_url and child_bg_url.startswith('http'):
                                            if any(bad in child_bg_url.lower() for bad in [
                                                '=s40', '=s60', '=w40', '=w60', '=h40', '=h60'
                                            ]):
                                                continue

                                            clean_child_url = clean_image_url(child_bg_url)

                                            if clean_child_url not in seen_urls:
                                                seen_urls.add(clean_child_url)

                                                width_match = re.search(r'width:\s*(\d+)px', child_style)
                                                height_match = re.search(r'height:\s*(\d+)px', child_style)
                                                width = width_match.group(1) if width_match else ""
                                                height = height_match.group(1) if height_match else ""

                                                image_urls.append({
                                                    "image_url": clean_child_url,
                                                    "alt_text": f"Nested background image",
                                                    "original_url": child_bg_url,
                                                    "width": width,
                                                    "height": height,
                                                    "source_type": "nested-background-image"
                                                })
                                                current_new += 1

                        except Exception:
                            continue
                except:
                    continue

            # Process traditional img tags
            for selector in img_tag_selectors:
                try:
                    imgs = page.locator(selector).all()
                    for img in imgs:
                        try:
                            src = None
                            for attr in ['src', 'data-src', 'data-lazy-src']:
                                src = img.get_attribute(attr)
                                if src and src.startswith('http'):
                                    break

                            if not src or not src.startswith('http'):
                                continue

                            # Skip very small images and common UI elements
                            if any(bad in src.lower() for bad in [
                                '=s40', '=s60', '=w40', '=w60', '=h40', '=h60',
                                'icon', 'logo', 'avatar', '1x1', 'pixel'
                            ]):
                                continue

                            clean_url = clean_image_url(src)

                            if clean_url not in seen_urls:
                                seen_urls.add(clean_url)

                                alt_text = img.get_attribute("alt") or ""
                                width = img.get_attribute("width") or ""
                                height = img.get_attribute("height") or ""

                                image_urls.append({
                                    "image_url": clean_url,
                                    "alt_text": alt_text,
                                    "original_url": src,
                                    "width": width,
                                    "height": height,
                                    "source_type": "img-tag"
                                })
                                current_new += 1

                        except Exception:
                            continue
                except:
                    continue

            current_total = len(image_urls)

            if iteration % 10 == 0 or current_new > 0:  # Report progress
                print(f"   📊 Total: {current_total} images (+{current_new} new)")

            # Stopping conditions
            if current_total == last_image_count:
                consecutive_no_change += 1
                if consecutive_no_change >= max_no_change:
                    print(f"✅ No new images for {max_no_change} iterations - stopping")
                    break
            else:
                consecutive_no_change = 0
                last_image_count = current_total

            # Safety limits
            if current_total > 1000:  # Increased limit
                print(f"✅ Collected {current_total} images - reasonable limit reached")
                break

        print(f"\n🎯 Image collection completed!")
        print(f"🖼️ Total iterations: {iteration}")
        print(f"📸 Total unique images: {len(image_urls)}")

        # Step 6: Final cleanup and save
        if image_urls:
            # Remove any remaining duplicates
            unique_images = []
            final_seen = set()

            for img_data in image_urls:
                url = img_data["image_url"]
                if url not in final_seen:
                    final_seen.add(url)
                    unique_images.append(img_data)

            # Save to CSV
            fieldnames = ["image_url", "alt_text", "original_url", "width", "height", "source_type"]
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(unique_images)

            print(f"✅ Saved {len(unique_images)} unique images to {filename}")

            # Show sample URLs for verification
            print("\n🔗 Sample image URLs collected:")
            for i, img_data in enumerate(unique_images[:8]):  # Show more samples
                url = img_data['image_url'][:80] + "..." if len(img_data['image_url']) > 80 else img_data['image_url']
                source_type = img_data.get('source_type', 'unknown')
                print(f"   {i + 1}. [{source_type}] {url}")

            # Show image sources breakdown
            sources = {}
            source_types = {}
            for img in unique_images:
                domain = urlparse(img['image_url']).netloc
                sources[domain] = sources.get(domain, 0) + 1

                src_type = img.get('source_type', 'unknown')
                source_types[src_type] = source_types.get(src_type, 0) + 1

            print("\n📊 Image sources by domain:")
            for domain, count in sources.items():
                print(f"   {domain}: {count} images")

            print("\n📋 Image sources by type:")
            for src_type, count in source_types.items():
                print(f"   {src_type}: {count} images")

        else:
            print("❌ No images were extracted")
            print("🔍 Debugging info:")
            print("   Try manually inspecting the page to see if images are loaded")
            print("   Check if Google Maps layout has changed")

            # Debug: Show what elements we can find
            debug_selectors = [
                'div[role="img"]',
                'div[style*="background-image"]',
                'img',
            ]

            for debug_sel in debug_selectors:
                count = page.locator(debug_sel).count()
                print(f"   Found {count} elements matching: {debug_sel}")

        # Close any modals
        try:
            page.keyboard.press("Escape")
        except:
            pass

    except Exception as e:
        print(f"❌ Error during image scraping: {e}")
        import traceback
        traceback.print_exc()

    return filename