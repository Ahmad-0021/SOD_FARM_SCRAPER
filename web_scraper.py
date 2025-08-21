from dotenv import load_dotenv
from google import genai
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import random
from patchright.sync_api import sync_playwright, ProxySettings
import os
from urllib.parse import urljoin, urlparse
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

PROXY: ProxySettings = {
    "server": f"http://{os.getenv('PROXY_HOST')}:{os.getenv('PROXY_PORT')}",
    "username": os.getenv("PROXY_USERNAME"),
    "password": os.getenv("PROXY_PASSWORD")
}


def clean_html_content(html_content):
    """Clean HTML content and extract readable text with better sod-related content focus"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Store original soup for specific element extraction later
    original_soup = BeautifulSoup(html_content, 'html.parser')

    # Extract specific elements before cleaning
    footer_content = ""
    header_content = ""
    contact_content = ""

    # Extract footer content for service area and contact info
    footer = original_soup.find(['footer', 'div[class*="footer"]', 'div[id*="footer"]'])
    if footer:
        footer_content = footer.get_text(separator=' ', strip=True)

    # Extract header/banner content for service area
    header = original_soup.find(['header', 'div[class*="banner"]', 'div[class*="hero"]', 'div[id*="banner"]'])
    if header:
        header_content = header.get_text(separator=' ', strip=True)

    # Extract contact page links or contact sections
    contact_links = original_soup.find_all('a', href=re.compile(r'contact', re.I))
    contact_sections = original_soup.find_all(['div', 'section'], class_=re.compile(r'contact', re.I))
    for elem in contact_links + contact_sections:
        contact_content += elem.get_text(separator=' ', strip=True) + " "

    # Remove unwanted elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        element.decompose()

    # Focus on content that likely contains sod information
    main_content = soup.find(['main', 'article', 'div[id*="content"]', 'div[class*="content"]'])
    if main_content:
        text = main_content.get_text()
    else:
        text = soup.get_text()

    # Clean text
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    clean_text = ' '.join(chunk for chunk in chunks if chunk)

    # Look for sod-related sections more specifically
    sod_keywords = ['sod', 'grass', 'turf', 'lawn', 'bermuda', 'zoysia', 'augustine', 'centipede', 'fescue']
    sentences = clean_text.split('.')
    relevant_sentences = []

    for sentence in sentences:
        if any(keyword.lower() in sentence.lower() for keyword in sod_keywords):
            relevant_sentences.append(sentence.strip())

    # Combine all content for comprehensive analysis
    combined_content = clean_text
    if footer_content:
        combined_content += f"\n\n[FOOTER CONTENT]\n{footer_content}"
    if header_content:
        combined_content += f"\n\n[HEADER/BANNER CONTENT]\n{header_content}"
    if contact_content:
        combined_content += f"\n\n[CONTACT CONTENT]\n{contact_content}"

    # If we found relevant sentences, prioritize them
    if relevant_sentences:
        relevant_text = '. '.join(relevant_sentences)
        # Limit length but include both relevant and general content
        final_text = relevant_text + " " + combined_content
        return final_text[:15000] if len(final_text) > 15000 else final_text

    return combined_content[:12000] if len(combined_content) > 12000 else combined_content


def attempt_scrape_single_url(url, page, context):
    """Attempt to scrape a single URL with multiple strategies"""
    try:
        # Set random user agent and headers to avoid detection
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0'
        ]

        # Set headers
        page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Random delay before navigation
        time.sleep(random.uniform(1, 2))

        # Try multiple navigation strategies
        content_loaded = False
        strategies = [
            ('networkidle', 60000),  # Wait for network idle, 60s timeout
            ('domcontentloaded', 45000),  # Wait for DOM, 45s timeout
            ('load', 30000),  # Wait for load event, 30s timeout
            (None, 20000)  # No wait condition, 20s timeout
        ]

        for strategy, timeout in strategies:
            try:
                logger.info(f"Trying navigation strategy: {strategy} with {timeout / 1000}s timeout")
                if strategy:
                    page.goto(url, timeout=timeout, wait_until=strategy)
                else:
                    page.goto(url, timeout=timeout)

                content_loaded = True
                logger.info(f"Successfully loaded page with strategy: {strategy}")
                break

            except Exception as e:
                logger.warning(f"Strategy {strategy} failed: {str(e)}")
                if strategy == strategies[-1][0]:  # Last strategy
                    logger.error(f"All navigation strategies failed for {url}")
                    return None
                continue

        if not content_loaded:
            return None

        # Wait for content to load with random delay
        page.wait_for_timeout(random.randint(2000, 4000))

        # Scroll down to load any lazy content
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            page.evaluate("window.scrollTo(0, 0)")
        except:
            pass

        # Get page content
        html_content = page.content()

        # Check if we got actual content (not just error pages)
        if len(html_content) < 500:
            logger.warning(f"Very little content received from {url}")
            return None

        # Clean and extract text
        clean_text = clean_html_content(html_content)

        if len(clean_text) < 100:
            logger.warning(f"Very little text content extracted from {url}")
            return None

        logger.info(f"Successfully extracted {len(clean_text)} characters from {url}")
        return clean_text

    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None


def scrape_website(url, page, context):
    """Enhanced website scraping with multiple URL attempts and fallback strategies"""
    # Try alternative approaches if main site fails
    alternative_urls = []
    if url.startswith('https://'):
        alternative_urls.append(url.replace('https://', 'http://'))
    if 'www.' not in url:
        base_url = url.replace('https://', '').replace('http://', '')
        alternative_urls.append(f"https://www.{base_url}")
        alternative_urls.append(f"http://www.{base_url}")

    all_urls_to_try = [url] + alternative_urls[:2]  # Try max 3 URLs total

    for attempt_url in all_urls_to_try:
        logger.info(f"Attempting to scrape: {attempt_url}")
        content = attempt_scrape_single_url(attempt_url, page, context)
        if content:
            logger.info(f"Successfully scraped content from: {attempt_url}")
            return content
        else:
            logger.warning(f"Failed to get content from: {attempt_url}")

    logger.error(f"All URL attempts failed for: {url}")
    return None


def extract_business_data_with_ai(content, client, url):
    """Enhanced AI extraction for all business data fields"""
    try:
        # Comprehensive prompt for all data fields
        prompt = f'''You are an expert assistant that extracts comprehensive business data from sod farm and landscaping company websites. 

IMPORTANT: Analyze the content carefully and extract ALL available information for each field below.

Common sod types include:
- Bermuda (including varieties like Tifway 419, Celebration, TifTuf, Tifton)  
- Zoysia (including Emerald, Meyer, Palisades, Zeon)
- St. Augustine (including Palmetto, Floratam, Raleigh)
- Centipede
- Fescue (Tall Fescue, Fine Fescue)
- Buffalo grass
- Bahia

Service area indicators: "serving", "delivery area", "we serve", city/county names, "local", "regional", radius mentions
Delivery info: "we deliver", "delivery available", "pickup only", "free delivery", "delivery service"
Installation: "installation available", "we install", "installation service", "professional installation"
Certifications: "certified", "licensed", "accredited", "member of", professional associations
Contact: email addresses in any format

Below is content from: {url}

[BEGIN WEBSITE CONTENT]
{content}
[END WEBSITE CONTENT]

Extract and return ONLY valid JSON in this EXACT format:

{{
  "sod_types": ["Bermuda", "Zoysia"],
  "service_area": "Local/Regional or specific areas mentioned",
  "delivery_info": "Delivery available/Pickup only/specific delivery details",
  "installation_services": "Installation available/Not mentioned/specific details",
  "contact_email": "email@example.com or empty string if not found",
  "certifications": "Any certifications mentioned or empty string",
  "brief_description": "First meaningful paragraph about the business"
}}

Rules:
- If a field is not found, use empty string "" or empty array []
- For sod_types, include specific variety names when mentioned
- For service_area, mention specific cities/regions if listed
- For brief_description, use the first substantial paragraph about what they do
- Keep descriptions under 200 characters
- Extract actual email addresses, not just "contact us" text'''

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # Parse the JSON response with better error handling
        response_text = response.text.strip()

        # Clean the response
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Sometimes AI returns extra text, try to extract just the JSON part
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            response_text = json_match.group()

        # Parse JSON
        result = json.loads(response_text)

        # Validate and clean the results
        cleaned_result = {
            "sod_types": [],
            "service_area": "",
            "delivery_info": "",
            "installation_services": "",
            "contact_email": "",
            "certifications": "",
            "brief_description": ""
        }

        # Clean sod types
        if 'sod_types' in result and isinstance(result['sod_types'], list):
            for sod_type in result['sod_types']:
                if sod_type and isinstance(sod_type, str) and len(sod_type.strip()) > 0:
                    cleaned_result['sod_types'].append(sod_type.strip())

        # Clean other fields
        for field in ['service_area', 'delivery_info', 'installation_services', 'contact_email', 'certifications',
                      'brief_description']:
            if field in result and isinstance(result[field], str):
                cleaned_result[field] = result[field].strip()[:200] if field == 'brief_description' else result[
                    field].strip()

        return cleaned_result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {url}: {str(e)}")
        logger.error(f"Raw response: {response.text[:500]}...")

        # Fallback manual extraction for sod types
        try:
            response_text = response.text.lower()
            manual_sod_types = []

            sod_patterns = [
                r'\b(bermuda|tifway|celebration|tiftuf|tifton)\b',
                r'\b(zoysia|emerald|meyer|palisades|zeon)\b',
                r'\b(st\.?\s*augustine|palmetto|floratam|raleigh)\b',
                r'\b(centipede)\b',
                r'\b(fescue|tall\s*fescue|fine\s*fescue)\b',
                r'\b(buffalo\s*grass)\b',
                r'\b(bahia)\b'
            ]

            for pattern in sod_patterns:
                matches = re.findall(pattern, response_text)
                manual_sod_types.extend([match.title() for match in matches])

            return {
                "sod_types": list(set(manual_sod_types)) if manual_sod_types else [],
                "service_area": "",
                "delivery_info": "",
                "installation_services": "",
                "contact_email": "",
                "certifications": "",
                "brief_description": ""
            }

        except:
            return {
                "sod_types": [],
                "service_area": "",
                "delivery_info": "",
                "installation_services": "",
                "contact_email": "",
                "certifications": "",
                "brief_description": ""
            }

    except Exception as e:
        logger.error(f"AI processing error for {url}: {str(e)}")
        return {
            "sod_types": [],
            "service_area": "",
            "delivery_info": "",
            "installation_services": "",
            "contact_email": "",
            "certifications": "",
            "brief_description": ""
        }


def normalize_url(url):
    """Enhanced URL normalization"""
    if not url or pd.isna(url):
        return None

    url = str(url).strip()
    if not url:
        return None

    # Remove common prefixes that might interfere
    url = url.replace('www.', '', 1) if url.startswith('www.') else url

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    return url


def main():
    # Initialize Gemini client
    try:
        client = genai.Client()
        logger.info("Gemini client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return

    # Read the CSV file
    try:
        df = pd.read_csv("output/all_usa_sod_farms_citywise_progress.csv")
        logger.info(f"Loaded {len(df)} records from CSV")
    except FileNotFoundError:
        logger.error("CSV file not found. Please check the path.")
        return

    # Add new columns for all data fields
    new_columns = [
        'sod_types', 'service_area', 'delivery_info', 'installation_services',
        'contact_email', 'certifications', 'brief_description',
        'scrape_status', 'scrape_timestamp', 'content_length'
    ]

    for col in new_columns:
        if col not in df.columns:
            df[col] = '' if col != 'content_length' else 0

    # Initialize Playwright with enhanced settings
    with sync_playwright() as p:
        # Launch browser with additional options
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-extensions'
            ],
            proxy=PROXY
        )

        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )

        page = context.new_page()

        # Process each row
        for index, row in df.iterrows():
            url = normalize_url(row.get('website', ''))

            if not url:
                logger.warning(f"Row {index}: No valid URL found")
                df.at[index, 'scrape_status'] = 'no_url'
                df.at[index, 'scrape_timestamp'] = pd.Timestamp.now()
                continue

            # Skip if already successfully processed AND has comprehensive data
            if (df.at[index, 'scrape_status'] == 'success' and
                    df.at[index, 'sod_types'] and
                    df.at[index, 'sod_types'] not in ['', '[]', 'null'] and
                    df.at[index, 'brief_description'] and
                    df.at[index, 'brief_description'] not in ['', 'null']):
                try:
                    sod_list = json.loads(df.at[index, 'sod_types'])
                    if len(sod_list) > 0 and df.at[index, 'brief_description']:
                        logger.info(
                            f"Row {index}: Already processed successfully with comprehensive data, skipping {url}")
                        continue
                    else:
                        logger.info(f"Row {index}: Previously processed but incomplete data, re-processing {url}")
                except:
                    logger.info(f"Row {index}: Invalid data format, re-processing {url}")
            else:
                logger.info(f"Row {index}: Not yet processed or incomplete, processing {url}")

            logger.info(f"Processing row {index}/{len(df) - 1}: {url}")

            try:
                # Scrape website content
                content = scrape_website(url, page, context)

                if content:
                    df.at[index, 'content_length'] = len(content)

                    # Extract all business data using AI
                    business_data = extract_business_data_with_ai(content, client, url)

                    # Update dataframe with all extracted data
                    df.at[index, 'sod_types'] = json.dumps(business_data['sod_types'])
                    df.at[index, 'service_area'] = business_data['service_area']
                    df.at[index, 'delivery_info'] = business_data['delivery_info']
                    df.at[index, 'installation_services'] = business_data['installation_services']
                    df.at[index, 'contact_email'] = business_data['contact_email']
                    df.at[index, 'certifications'] = business_data['certifications']
                    df.at[index, 'brief_description'] = business_data['brief_description']
                    df.at[index, 'scrape_status'] = 'success'
                    df.at[index, 'scrape_timestamp'] = pd.Timestamp.now()

                    logger.info(f"Row {index}: Extracted - Sod Types: {len(business_data['sod_types'])}, "
                                f"Service Area: {business_data['service_area'][:50]}..., "
                                f"Email: {business_data['contact_email']}")
                else:
                    df.at[index, 'scrape_status'] = 'failed_scrape'
                    df.at[index, 'scrape_timestamp'] = pd.Timestamp.now()
                    logger.warning(f"Row {index}: Failed to scrape content")

            except Exception as e:
                logger.error(f"Row {index}: Error processing {url}: {str(e)}")
                df.at[index, 'scrape_status'] = f'error: {str(e)[:100]}'
                df.at[index, 'scrape_timestamp'] = pd.Timestamp.now()

            # Save progress after each row
            try:
                df.to_csv("output/all_usa_sod_farms_citywise_progress.csv", index=False)
            except Exception as e:
                logger.error(f"Failed to save progress: {e}")

            # Random delay between requests
            delay = random.uniform(3, 7)
            logger.info(f"Waiting {delay:.1f} seconds before next request...")
            time.sleep(delay)

            # Optional: Process only first N rows for testing
            # if index >= 2:  # Uncomment to limit processing
            #     break

        # Close browser
        browser.close()

    # Save final results
    try:
        df.to_csv("output/all_usa_sod_farms_comprehensive_data.csv", index=False)
        logger.info("Processing complete! Results saved to output/all_usa_sod_farms_comprehensive_data.csv")
    except Exception as e:
        logger.error(f"Failed to save final results: {e}")

    # Print summary
    success_count = len(df[df['scrape_status'] == 'success'])
    total_sod_types = sum([len(json.loads(sod_types)) if sod_types and sod_types != '[]' else 0
                           for sod_types in df['sod_types'] if sod_types])

    businesses_with_email = len(df[df['contact_email'].notna() & (df['contact_email'] != '')])
    businesses_with_description = len(df[df['brief_description'].notna() & (df['brief_description'] != '')])

    logger.info(f"Summary: {success_count}/{len(df)} websites successfully processed")
    logger.info(f"Total sod types found: {total_sod_types}")
    logger.info(f"Businesses with email: {businesses_with_email}")
    logger.info(f"Businesses with description: {businesses_with_description}")

    # Show sample detailed results
    logger.info("\n--- SAMPLE RESULTS ---")
    for index, row in df.iterrows():
        if row['scrape_status'] == 'success' and row['sod_types']:
            sod_types = json.loads(row['sod_types']) if row['sod_types'] else []
            if sod_types:
                logger.info(f"Row {index} ({row.get('website', 'Unknown')}):")
                logger.info(f"  Sod Types: {sod_types}")
                logger.info(f"  Service Area: {row.get('service_area', 'N/A')}")
                logger.info(f"  Delivery: {row.get('delivery_info', 'N/A')}")
                logger.info(f"  Email: {row.get('contact_email', 'N/A')}")
                logger.info(f"  Description: {row.get('brief_description', 'N/A')[:100]}...")
                logger.info("---")

                # Show only first 5 detailed results to avoid spam
                if index >= 4:
                    break


if __name__ == "__main__":
    main()