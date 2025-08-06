# 🗺️ Google Maps Scraper

A powerful Python scraper to extract **business data**, **customer reviews**, and **photos** from Google Maps. Built with `patchright` (a stealth-enhanced Playwright) to avoid detection.

Perfect for:
- Market research
- Competitor analysis
- Reputation monitoring
- Lead generation

---

## 🚀 Features

✅ Extracts:
- Business name, address, phone, website  
- Average rating and total review count  
- Full customer reviews (text, rating, date, author)  
- Business replies to reviews  
- All image URLs from the "All" photos section  

📁 Outputs:
- `output/business.csv` – All business data  
- `output/reviews/reviews_{name}.csv` – Per-business customer reviews  
- `output/images/images_{name}.csv` – All image URLs  

🖱️ Fully automated:
- Clicks **"Reviews" tab** → scrapes all reviews  
- Returns to **"Overview"** → clicks **"All" photos** → scrapes all images  
- Handles dynamic loading and scrolling  

---
profile
Qwen3-235B-A22B-2507
4:40 pm
Absolutely! Here's a professional and comprehensive README.md for your Google Maps Scraper project. It includes CLI usage, features, installation, and structure — perfect for documentation or GitHub.

✅ README.md
markdown


1
2
3
4
5
6
7
8
9
10
11
12
13
14
15
16
17
18
19
20
21
22
23
24
25
26
27
28
29
30
31
32
33
34
35
36
37
38
39
40
41
42
43
44
45
46
47
48
⌄
⌄
⌄
⌄
# 🗺️ Google Maps Scraper

A powerful Python scraper to extract **business data**, **customer reviews**, and **photos** from Google Maps. Built with `patchright` (a stealth-enhanced Playwright) to avoid detection.

Perfect for:
- Market research
- Competitor analysis
- Reputation monitoring
- Lead generation

---

## 🚀 Features

✅ Extracts:
- Business name, address, phone, website  
- Average rating and total review count  
- Full customer reviews (text, rating, date, author)  
- Business replies to reviews  
- All image URLs from the "All" photos section  

📁 Outputs:
- `output/business.csv` – All business data  
- `output/reviews/reviews_{name}.csv` – Per-business customer reviews  
- `output/images/images_{name}.csv` – All image URLs  

🖱️ Fully automated:
- Clicks **"Reviews" tab** → scrapes all reviews  
- Returns to **"Overview"** → clicks **"All" photos** → scrapes all images  
- Handles dynamic loading and scrolling  

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/google-maps-scraper.git
cd google-maps-scraper

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install patchright pandas
⚠️ patchright is a patched version of Playwright with anti-bot evasion. 

🖥️ CLI Usage
Option 1: Search directly
bash


1
python main.py -s "sod farms in usa" -t 5
Option 2: Use input.txt for multiple searches
Create input.txt:



1
2
3
sod farms in Texas
grass nurseries in Oklahoma
turf farms in Florida
Then run:

bash


1
python main.py
💡 You can also combine: python main.py -s "farms in California" 

🛠️ Arguments
-s
,
--search
Search query (e.g., "sod farms")
(from
input.txt
)
-t
,
--total
Max number of listings to scrape
1,000,000

📁 Output Structure
output/
├── business.csv                # All scraped businesses
├── business.xlsx
├── reviews/
│   ├── reviews_Biograss_Sod_Farms.csv
│   └── reviews_Tulsa_Grass.csv
└── images/
    ├── images_Biograss_Sod_Farms.csv
    └── images_Tulsa_Grass.csv

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/Ahmad-0021/SOD_FARM_SCRAPER.git
cd SOD_FARM_SCRAPER


# Install dependencies
pip install patchright pandas

🖥️ CLI Usage
Option 1: Search directly
python main.py -s "sod farms in usa" -t 5