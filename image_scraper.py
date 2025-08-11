# image_scraper_ultra_fast.py
from patchright.sync_api import Page, TimeoutError
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
        url = re.sub(r'-k-no$', '', url)
        return url
    except:
        return url


def extract_background_image_url(style_attr: str) -> str:
    """Extract URL from background-image CSS property"""
    if not style_attr:
        return ""
    match = re.search(r'background-image:\s*url\(["\']?(.*?)["\']?\)', style_attr)
    return match.group(1) if match else ""


def is_valid_image_url(url: str) -> bool:
    """Quick validation to skip obvious non-image URLs"""
    if not url or not url.startswith('http'):
        return False

    # Skip very small images and common UI elements
    bad_patterns = ['=s40', '=s60', '=w40', '=w60', '=h40', '=h60', 'icon', 'logo', 'avatar', '1x1', 'pixel']
    return not any(bad in url.lower() for bad in bad_patterns)


def extract_all_images_single_pass(page: Page) -> list:
    """ULTRA-FAST: Extract ALL images in a single JavaScript execution"""

    # JavaScript code to extract ALL images at once
    js_code = """
    () => {
        const images = [];
        const seenUrls = new Set();

        // Helper function to add image if valid
        const addImage = (url, altText, originalUrl, width, height, sourceType) => {
            if (!url || !url.startsWith('http') || seenUrls.has(url)) return;

            // Skip small/UI images
            const badPatterns = ['=s40', '=s60', '=w40', '=w60', '=h40', '=h60', 'icon', 'logo', 'avatar', '1x1', 'pixel'];
            if (badPatterns.some(bad => url.toLowerCase().includes(bad))) return;

            seenUrls.add(url);
            images.push({
                image_url: url,
                alt_text: altText || '',
                original_url: originalUrl || url,
                width: width || '',
                height: height || '',
                source_type: sourceType
            });
        };

        // Clean URL function
        const cleanUrl = (url) => {
            if (!url) return url;
            return url.replace(/=w\\d+-h\\d+/g, '=w2000-h2000')
                     .replace(/=s\\d+/g, '=s2000')
                     .replace(/=c-[^&]*/g, '')
                     .replace(/-k-no$/g, '');
        };

        // Extract background image URL
        const extractBgUrl = (style) => {
            if (!style) return '';
            const match = style.match(/background-image:\\s*url\\(["\']?(.*?)["\']?\\)/);
            return match ? match[1] : '';
        };

        // PRIORITY 1: Background images from div[role="img"]
        const bgSelectors = [
            'div[role="img"][style*="background-image"]',
            'div.U39Pmb[role="img"]',
            'div.Uf0tqf[style*="background-image"]',
            'div[style*="background-image"][style*="googleusercontent"]',
            'div[style*="background-image"][style*="gstatic"]',
            'div[style*="background-image"][style*="ggpht"]'
        ];

        bgSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                const style = el.getAttribute('style');
                if (style && style.includes('background-image')) {
                    const bgUrl = extractBgUrl(style);
                    if (bgUrl) {
                        const cleanedUrl = cleanUrl(bgUrl);
                        const widthMatch = style.match(/width:\\s*(\\d+)px/);
                        const heightMatch = style.match(/height:\\s*(\\d+)px/);
                        addImage(
                            cleanedUrl,
                            'Background image',
                            bgUrl,
                            widthMatch ? widthMatch[1] : '',
                            heightMatch ? heightMatch[1] : '',
                            'background-image'
                        );

                        // Check nested divs
                        el.querySelectorAll('div[style*="background-image"]').forEach(child => {
                            const childStyle = child.getAttribute('style');
                            if (childStyle && childStyle.includes('background-image')) {
                                const childBgUrl = extractBgUrl(childStyle);
                                if (childBgUrl) {
                                    const cleanedChildUrl = cleanUrl(childBgUrl);
                                    const cWidthMatch = childStyle.match(/width:\\s*(\\d+)px/);
                                    const cHeightMatch = childStyle.match(/height:\\s*(\\d+)px/);
                                    addImage(
                                        cleanedChildUrl,
                                        'Nested background image',
                                        childBgUrl,
                                        cWidthMatch ? cWidthMatch[1] : '',
                                        cHeightMatch ? cHeightMatch[1] : '',
                                        'nested-background-image'
                                    );
                                }
                            }
                        });
                    }
                }
            });
        });

        // PRIORITY 2: Regular img tags
        const imgSelectors = [
            'img[src*="googleusercontent.com"]',
            'img[src*="gstatic.com"]',
            'img[src*="ggpht.com"]',
            'img[src^="https://lh"]',
            'img.DaSXdd',
            'img[data-src*="google"]',
            'picture img',
            '[role="img"] img',
            'img[loading="lazy"]',
            'img[alt*="photo" i]'
        ];

        imgSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(img => {
                const src = img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src');
                if (src) {
                    const cleanedUrl = cleanUrl(src);
                    addImage(
                        cleanedUrl,
                        img.alt || '',
                        src,
                        img.width || img.getAttribute('width') || '',
                        img.height || img.getAttribute('height') || '',
                        'img-tag'
                    );
                }
            });
        });

        return images;
    }
    """

    try:
        return page.evaluate(js_code)
    except Exception as e:
        print(f"⚠️ JavaScript extraction failed: {e}")
        return []


def ultra_fast_scroll_and_extract(page: Page) -> list:
    """ULTRA-FAST: Minimal scrolling with immediate extraction"""
    all_images = []
    seen_urls = set()

    # Get scroll container
    active_container = page.locator("body")
    containers = [
        "div[role='main'] div[style*='overflow-y']",
        "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
        "[role='main']"
    ]

    for container_sel in containers:
        container = page.locator(container_sel)
        if container.count() > 0:
            active_container = container.first
            break

    # PHASE 1: Initial extraction (no scroll)
    print("⚡ Phase 1: Initial extraction...")
    initial_images = extract_all_images_single_pass(page)
    for img in initial_images:
        if img['image_url'] not in seen_urls:
            seen_urls.add(img['image_url'])
            all_images.append(img)

    print(f"   📸 Found {len(initial_images)} initial images")

    # PHASE 2: Quick scroll cycles (max 6 iterations)
    max_quick_scrolls = 6
    no_change_limit = 2
    consecutive_no_change = 0

    print("⚡ Phase 2: Quick scroll extraction...")

    for i in range(max_quick_scrolls):
        # Fast aggressive scroll
        try:
            page.evaluate("window.scrollBy(0, 1500)")
            active_container.evaluate("el => el.scrollBy(0, 1000)")
            time.sleep(1)  # Minimal wait
        except:
            pass

        # Extract images
        new_images = extract_all_images_single_pass(page)
        new_count = 0

        for img in new_images:
            if img['image_url'] not in seen_urls:
                seen_urls.add(img['image_url'])
                all_images.append(img)
                new_count += 1

        print(f"   📍 Scroll {i + 1}: +{new_count} new images (Total: {len(all_images)})")

        # Early exit conditions
        if new_count == 0:
            consecutive_no_change += 1
            if consecutive_no_change >= no_change_limit:
                print("   ✅ No new images - stopping early")
                break
        else:
            consecutive_no_change = 0

        # Sufficient images collected
        if len(all_images) > 200:
            print("   ✅ Sufficient images collected")
            break

    return all_images


def scrape_images(page: Page, business_name: str, output_dir: str = "output/images"):
    """
    ULTRA-FAST image scraper - optimized for maximum speed
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/images_{sanitize_filename(business_name)}.csv"

    try:
        print("🚀 Starting ULTRA-FAST image collection...")
        start_time = time.time()

        # Step 1: Quick photo button detection and click
        photo_indicators = [
            '[data-value="all_photos"]',
            'button[data-carousel-index="0"]',
            'button:has-text("photos")',
            'button:has-text("Photo")',
            '[role="button"]:has-text("Photo")'
        ]

        photos_button = None
        for selector in photo_indicators:
            button = page.locator(selector)
            if button.count() > 0:
                photos_button = button.first
                print(f"✅ Found photos button: {selector}")
                break

        if photos_button:
            try:
                photos_button.click()
                print("📸 Clicked photos button")
                time.sleep(2)  # Minimal wait
            except Exception as e:
                print(f"⚠️ Could not click photos button: {e}")

        # Step 2: Quick image detection wait
        wait_selectors = ['div[role="img"]', 'img[src*="googleusercontent.com"]']
        images_loaded = False

        for selector in wait_selectors:
            try:
                page.wait_for_selector(selector, timeout=2000)  # Very short timeout
                images_loaded = True
                print(f"✅ Images detected: {selector}")
                break
            except TimeoutError:
                continue

        # Step 3: ULTRA-FAST extraction
        image_urls = ultra_fast_scroll_and_extract(page)

        elapsed = time.time() - start_time
        print(f"\n🎯 ULTRA-FAST collection completed in {elapsed:.1f}s!")
        print(f"📸 Total unique images: {len(image_urls)}")

        # Step 4: Quick save
        if image_urls:
            # Quick deduplication (should already be unique)
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

            print(f"✅ Saved {len(unique_images)} images to {filename}")

            # Quick stats
            sources = {}
            source_types = {}
            for img in unique_images:
                domain = urlparse(img['image_url']).netloc
                sources[domain] = sources.get(domain, 0) + 1
                src_type = img.get('source_type', 'unknown')
                source_types[src_type] = source_types.get(src_type, 0) + 1

            print(f"📊 Top domains: {dict(list(sources.items())[:3])}")
            print(f"📋 Source types: {source_types}")

            # Sample URLs (first 3 only for speed)
            print("\n🔗 Sample URLs:")
            for i, img_data in enumerate(unique_images[:3]):
                url = img_data['image_url'][:50] + "..." if len(img_data['image_url']) > 50 else img_data['image_url']
                print(f"   {i + 1}. [{img_data.get('source_type', 'unknown')}] {url}")

        else:
            print("❌ No images extracted")
            # Minimal debugging
            debug_count = page.locator('div[role="img"]').count()
            print(f"🔍 Debug: Found {debug_count} div[role='img'] elements")

        # Quick cleanup
        try:
            page.keyboard.press("Escape")
        except:
            pass

    except Exception as e:
        print(f"❌ Error during ultra-fast scraping: {e}")
        import traceback
        traceback.print_exc()

    return filename