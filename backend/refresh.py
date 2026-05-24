import os
import re
import json
import time
import datetime
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

# Define targets
USCIS_FEED_URL = "https://www.uscis.gov/newsroom/all-news/feed"
FED_REG_API_URL = "https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=u-s-citizenship-and-immigration-services&conditions[type][]=RULE&conditions[type][]=PRORULE&order=newest"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q=H-1B+visa+OR+US+citizenship+OR+USCIS+OR+EB5+visa&hl=en-US&gl=US&ceid=US:en"

FRONTEND_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "news_data.json")

# Ensure directory exists
os.makedirs(os.path.dirname(FRONTEND_DATA_PATH), exist_ok=True)

STOPWORDS = {
    'the', 'a', 'an', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'by', 'from',
    'to', 'in', 'of', 'for', 'with', 'about', 'against', 'between', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in',
    'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 'is',
    'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do',
    'does', 'did', 'doing', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',
    'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
    'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those'
}

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(separator=" ")
    # Clean whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def parse_date(date_str):
    # Try different date formats and return a datetime object
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",  # "Sat, 23 May 2026 14:30:00 GMT"
        "%a, %d %b %Y %H:%M:%S %z",  # "Sat, 23 May 2026 14:30:00 +0000"
        "%Y-%m-%dT%H:%M:%S%z",       # "2026-05-23T14:30:00-04:00"
        "%Y-%m-%d",                  # "2026-05-23"
    ]
    # Clean up timezone abbreviations standard python strptime might not like
    date_str_clean = re.sub(r'\s(GMT|EST|EDT|PST|PDT|UTC)$', ' +0000', date_str)
    date_str_clean = date_str_clean.strip()
    
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str_clean, fmt)
        except ValueError:
            continue
            
    # Fallback to current time if unparseable
    return datetime.datetime.utcnow()

def fetch_xml_feed(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return ET.fromstring(response.content)
    except Exception as e:
        print(f"Error fetching XML feed {url}: {e}")
        return None

def fetch_uscis_news():
    print("Fetching USCIS Newsroom...")
    root = fetch_xml_feed(USCIS_FEED_URL)
    articles = []
    if root is None:
        return articles
        
    for item in root.findall(".//item"):
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else ""
        pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
        desc_html = item.find("description").text if item.find("description") is not None else ""
        
        description = clean_html(desc_html)
        pub_date = parse_date(pub_date_str)
        
        articles.append({
            "title": title.strip(),
            "link": link.strip(),
            "pub_date": pub_date.isoformat(),
            "description": description,
            "source": "USCIS Official",
            "source_type": "official"
        })
    return articles

def fetch_federal_register():
    print("Fetching Federal Register Documents...")
    articles = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(FED_REG_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for doc in data.get("results", []):
            title = doc.get("title", "")
            link = doc.get("html_url", "")
            pub_date_str = doc.get("publication_date", "")
            abstract = doc.get("abstract", "")
            
            pub_date = parse_date(pub_date_str)
            
            articles.append({
                "title": title.strip(),
                "link": link.strip(),
                "pub_date": pub_date.isoformat(),
                "description": abstract if abstract else title,
                "source": "Federal Register",
                "source_type": "official"
            })
    except Exception as e:
        print(f"Error fetching Federal Register: {e}")
    return articles

def fetch_google_news():
    print("Fetching Google News feeds...")
    root = fetch_xml_feed(GOOGLE_NEWS_URL)
    articles = []
    if root is None:
        return articles
        
    for item in root.findall(".//item"):
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else ""
        pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
        desc_html = item.find("description").text if item.find("description") is not None else ""
        
        description = clean_html(desc_html)
        pub_date = parse_date(pub_date_str)
        
        # Google News titles usually contain the publisher at the end: "Title - Publisher"
        # Let's clean that up and extract the actual publisher
        publisher = "Google News"
        if " - " in title:
            parts = title.split(" - ")
            publisher = parts[-1].strip()
            title = " - ".join(parts[:-1]).strip()
            
        # Google News redirects links through news.google.com. 
        # We can extract the target URL if needed, but the redirect URL works fine.
        
        articles.append({
            "title": title,
            "link": link,
            "pub_date": pub_date.isoformat(),
            "description": description,
            "source": publisher,
            "source_type": "media"
        })
    return articles

def calculate_jaccard_similarity(str1, str2):
    # Tokenize and lowercase words, stripping punctuation
    words1 = set(re.findall(r'\w+', str1.lower()))
    words2 = set(re.findall(r'\w+', str2.lower()))
    
    # Filter stopwords and short terms to focus on keywords
    words1 = words1 - STOPWORDS
    words2 = words2 - STOPWORDS
    
    if not words1 or not words2:
        return 0.0
        
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

def deduplicate_articles(articles):
    print("Deduplicating articles...")
    deduplicated = []
    
    # Sort articles: Official sources first, then by date (newest first)
    articles.sort(key=lambda x: (0 if x["source_type"] == "official" else 1, x["pub_date"]), reverse=True)
    
    for art in articles:
        is_duplicate = False
        for existing in deduplicated:
            # Check title Jaccard similarity
            similarity = calculate_jaccard_similarity(art["title"], existing["title"])
            if similarity > 0.65:
                # Add duplicate link as an alternative coverage link
                if "related_coverage" not in existing:
                    existing["related_coverage"] = []
                # Ensure we don't add the same link twice
                if art["link"] != existing["link"] and art["link"] not in [r["link"] for r in existing["related_coverage"]]:
                    existing["related_coverage"].append({
                        "source": art["source"],
                        "link": art["link"]
                    })
                is_duplicate = True
                break
        
        if not is_duplicate:
            deduplicated.append(art)
            
    print(f"Reduced from {len(articles)} to {len(deduplicated)} articles.")
    return deduplicated

def categorize_article(title, description):
    combined = (title + " " + description).lower()
    
    # Visa bulletin takes priority
    if "visa bulletin" in combined or "priority date" in combined:
        return "Visa Bulletin"
    # H-1B
    elif "h-1b" in combined or "h1b" in combined or "h-4" in combined or "prevailing wage" in combined:
        return "H-1B Visa"
    # Citizenship / Naturalization
    elif "citizenship" in combined or "naturalization" in combined or "n-400" in combined or "civics test" in combined:
        return "US Citizenship"
    # EB-5
    elif "eb-5" in combined or "eb5" in combined or "regional center" in combined or "immigrant investor" in combined:
        return "EB-5 Visa"
    # USCIS Alert specific
    elif "uscis" in combined and ("alert" in combined or "announcement" in combined or "fee increase" in combined):
        return "USCIS Announcements"
    else:
        return "General Policy"

def local_extractive_summary(text, title):
    if not text or len(text.strip()) < 50:
        return text if text else title

    # Simple extractive summarizer: score sentences based on word frequency
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= 2:
        return text
        
    # Build word frequency table
    words = re.findall(r'\w+', text.lower())
    freq_table = {}
    for word in words:
        if word not in STOPWORDS and len(word) > 2:
            freq_table[word] = freq_table.get(word, 0) + 1
            
    if not freq_table:
        return ". ".join(sentences[:2]) + "."
        
    # Score sentences
    sentence_scores = {}
    for i, sent in enumerate(sentences):
        sent_words = re.findall(r'\w+', sent.lower())
        score = 0
        for word in sent_words:
            if word in freq_table:
                score += freq_table[word]
        # Normalize by length to prevent bias towards long sentences
        if len(sent_words) > 0:
            sentence_scores[i] = score / len(sent_words)
            
    # Get top 2 sentences (preserving chronological order)
    top_indices = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:2]
    top_indices.sort()
    
    summary = " ".join([sentences[idx].strip() for idx in top_indices])
    return summary

def generate_ai_summary(title, description, api_key):
    # Directly invoke the Gemini REST API to ensure no dependency issues
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"Summarize this US immigration news article in 2-3 concise bullet points. "
        f"Focus on key dates, filing actions, fee changes, or eligibility requirements. "
        f"Do not write introductions or conversational text. Speak directly.\n\n"
        f"Title: {title}\n"
        f"Snippet: {description}"
    )
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 250,
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        # Parse the response text
        candidates = result.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                ai_text = parts[0].get("text", "").strip()
                if ai_text:
                    return ai_text
    except Exception as e:
        print(f"Gemini API summarization failed: {e}")
    
    return None

def process_summaries(articles):
    api_key = os.environ.get("GEMINI_API_KEY")
    has_api = bool(api_key)
    
    if has_api:
        print("Using Gemini API for high-quality summaries (with rate limiting)...")
    else:
        print("Using local extractive NLP for summaries (offline/free)...")
        
    for idx, art in enumerate(articles):
        # Only summarize if it doesn't already have one
        if "summary" in art and art["summary"]:
            continue
            
        safe_title = art['title'][:40].encode('ascii', 'ignore').decode('ascii')
        print(f"Summarizing article {idx+1}/{len(articles)}: {safe_title}...")
        
        # Rule-based categorization
        art["category"] = categorize_article(art["title"], art["description"])
        
        summary = None
        if has_api:
            # Stagger requests to stay under 15 RPM for free tier (1 request per 4.5 seconds)
            time.sleep(4.5)
            summary = generate_ai_summary(art["title"], art["description"], api_key)
            
        if not summary:
            # Fallback to local extractive summary
            summary = local_extractive_summary(art["description"], art["title"])
            
        art["summary"] = summary
        
    return articles

def load_existing_data():
    if os.path.exists(FRONTEND_DATA_PATH):
        try:
            with open(FRONTEND_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading existing data: {e}")
    return []

def save_data(data):
    try:
        # Keep only the last 30 days of data or limit to 100 articles to avoid Git bloat
        # Sort by date (newest first)
        data.sort(key=lambda x: x["pub_date"], reverse=True)
        
        # Clean data (remove older than 30 days)
        cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat()
        trimmed_data = [art for art in data if art["pub_date"] >= cutoff_date]
        
        # Hard limit to top 80 articles to guarantee low payload sizes
        trimmed_data = trimmed_data[:80]
        
        with open(FRONTEND_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(trimmed_data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(trimmed_data)} articles to {FRONTEND_DATA_PATH}")
    except Exception as e:
        print(f"Error saving data: {e}")

def main():
    print("=== STARTING IMMIGRATION NEWS AGGREGATOR ===")
    
    # 1. Fetch from all sources
    all_articles = []
    all_articles.extend(fetch_uscis_news())
    all_articles.extend(fetch_federal_register())
    all_articles.extend(fetch_google_news())
    
    if not all_articles:
        print("No articles fetched from any source. Terminating.")
        return
        
    # 2. Deduplicate new articles
    unique_new = deduplicate_articles(all_articles)
    
    # 3. Load existing historical data
    existing = load_existing_data()
    
    # Create dictionary mapping link -> article to merge safely
    merged_dict = {art["link"]: art for art in existing}
    
    # Add new articles (updating existing or adding new)
    for art in unique_new:
        link = art["link"]
        if link in merged_dict:
            # Retain existing summary if present to avoid re-calling Gemini
            if "summary" in merged_dict[link] and merged_dict[link]["summary"]:
                art["summary"] = merged_dict[link]["summary"]
            if "category" in merged_dict[link] and merged_dict[link]["category"]:
                art["category"] = merged_dict[link]["category"]
            
            # Merge related coverages
            if "related_coverage" in merged_dict[link]:
                existing_rel = merged_dict[link]["related_coverage"]
                new_rel = art.get("related_coverage", [])
                # Combine and deduplicate links
                combined_rel = {r["link"]: r for r in existing_rel + new_rel}
                art["related_coverage"] = list(combined_rel.values())
                
        merged_dict[link] = art
        
    merged_list = list(merged_dict.values())
    
    # 4. Generate Summaries & Categories
    final_list = process_summaries(merged_list)
    
    # 5. Save database
    save_data(final_list)
    print("=== PROCESS COMPLETE ===")

if __name__ == "__main__":
    main()
