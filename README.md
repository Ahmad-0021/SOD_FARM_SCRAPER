# 🗺️ Google Maps Scraper

A powerful Python scraper to extract **business data**, **customer reviews**, and **photos** from Google Maps.  
Built with `patchright` (a stealth-enhanced Playwright) to avoid detection and scraping blocks.

---

## 🎯 Use Cases

Perfect for:

- ✅ Market research  
- ✅ Competitor analysis  
- ✅ Reputation monitoring  
- ✅ Lead generation  

---

## 🚀 Features

### ✅ Extracts:
- Business name, address, phone, website  
- Average rating and total review count  
- Full customer reviews (text, rating, date, author)  
- Business replies to reviews  
- All image URLs from the "All" photos section  

### 📁 Outputs:
- `output/business.csv` – All business data  
- `output/reviews/reviews_{name}.csv` – Per-business customer reviews  
- `output/images/images_{name}.csv` – All image URLs  

### 🖱️ Fully automated:
- Clicks **"Reviews" tab** → scrapes all reviews  
- Returns to **"Overview"** → clicks **"All" photos** → scrapes all images  
- Handles dynamic loading and scrolling automatically  

---

## 📦 Installation

```bash
# Clone the repo
git clone https://github.com/Ahmad-0021/SOD_FARM_SCRAPER.git
cd SOD_FARM_SCRAPER

# (Optional) Create virtual environment
python -m venv venv
# For Windows:
venv\Scripts\activate
# For Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install patchright pandas
🖥️ CLI Usage
Option 1: Direct search using arguments
python main.py -s "sod farms in usa" -t 5
