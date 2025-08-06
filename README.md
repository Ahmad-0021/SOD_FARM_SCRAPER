# 🗺️ Google Maps Scraper using Python & Playwright

This script serves as an example of how to use **Python** and **Playwright** to scrape/extract business data, reviews, and images from **Google Maps**.

---

## 📦 Features

- ✅ Scrape business name, address, website, phone number, coordinates, and reviews
- ✅ Extract customer reviews using `review_scraper.py`
- ✅ Download images using `image_scraper.py`
- ✅ Save output as both `.csv` and `.xlsx`
- ✅ Use command-line arguments or a list from `input.txt`

---

## ⚙️ Requirements

- Python 3.10+
- patchright
- Pandas

### 🧪 Installation

Install the dependencies:

```bash
pip install -r requirements.txt
playwright install

 ## 🚀 HOW TO USE

bash
Copy
Edit
python main.py -s "restaurants in New York" -t 10
Argument	Description
-s / --search	Search term (e.g., "hotels in London")
-t / --total	Maximum number of listings to scrape