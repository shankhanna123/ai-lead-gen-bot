import os
import time
import requests
import datetime
import google.generativeai as genai
from googlesearch import search

# --- 1. CONFIGURATION (Loaded from GitHub Secrets) ---
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --- 2. YOUR TARGETS (Edit this) ---
# Your ClickBank Niche Keyword
NICHE = "best weight loss supplement" 
# Keywords that signal "Buying Intent"
INTENT_KEYWORDS = ["recommend", "review", "help", "best", "advice", "worth it"]

# --- 3. SEARCH ENGINE (Google Hack) ---
def search_fresh_leads():
    leads = []
    # Get date for "Freshness" filter (Post-2025/2026)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # We search 3 major platforms via Google
    # "after:{today}" forces Google to show results indexed in the last 24h
    queries = [
        f'site:reddit.com "{NICHE}" after:{today}',
        f'site:quora.com "{NICHE}" after:{today}',
        f'site:twitter.com "{NICHE}" after:{today}'
    ]
    
    print(f"🔍 Scanning for: {NICHE}...")
    
    for q in queries:
        try:
            # num_results=10 keeps it fast and under rate limits
            for result in search(q, num_results=10, advanced=True):
                # Basic Keyword Match before AI (Saves API Tokens)
                if any(k in (result.title + result.description).lower() for k in INTENT_KEYWORDS):
                    leads.append({
                        "title": result.title,
                        "link": result.url,
                        "snippet": result.description,
                        "source": "Reddit" if "reddit" in result.url else "Twitter/Quora"
                    })
                time.sleep(1) # Be polite to Google servers
        except Exception as e:
            print(f"⚠️ Search Error: {e}")
            
    # Remove duplicates based on URL
    unique_leads = {v['link']: v for v in leads}.values()
    print(f"✅ Found {len(unique_leads)} potential leads.")
    return list(unique_leads)

# --- 4. AI FILTER (USA + Intent Check) ---
def filter_with_gemini(leads):
    if not leads: return []
    
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    high_quality_leads = []
    
    print("🤖 Analyzing leads with Gemini...")
    
    for lead in leads:
        # The Master Prompt
        prompt = f"""
        Act as a Lead Qualification Expert. Analyze this online post.
        
        Title: {lead['title']}
        Snippet: {lead['snippet']}
        Link: {lead['link']}
        
        CRITERIA:
        1. LOCATION: Is there any context implying the user is in the USA? (e.g. $, USD, US shipping, US slang, US brands). If ambiguous but English, assume YES.
        2. INTENT: Is the user looking for a solution/recommendation for '{NICHE}'?
        
        OUTPUT FORMAT:
        If PASS: Write a 1-sentence DM pitch starting with "PITCH:".
        If FAIL: Write "NO".
        """
        
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if "NO" not in text and "PITCH:" in text:
                lead['pitch'] = text.replace("PITCH:", "").strip()
                high_quality_leads.append(lead)
                print(f"🔥 Hot Lead: {lead['title']}")
            else:
                print(f"❄️ Cold Lead: {lead['title']}")
                
            time.sleep(2) # Avoid hitting Gemini rate limits
            
        except Exception as e:
            print(f"AI Error: {e}")
            
    return high_quality_leads

# --- 5. TELEGRAM NOTIFIER ---
def send_telegram(leads):
    if not leads: return

    for lead in leads:
        msg = (
            f"🚀 *New Lead Found!* ({lead['source']})\n\n"
            f"📝 *Post:* {lead['title']}\n"
            f"🔗 *Link:* {lead['link']}\n\n"
            f"💡 *Suggested Pitch:* \n{lead['pitch']}"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
        time.sleep(1)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    raw_leads = search_fresh_leads()
    verified_leads = filter_with_gemini(raw_leads)
    send_telegram(verified_leads)
