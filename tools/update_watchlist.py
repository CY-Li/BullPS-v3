
from playwright.sync_api import sync_playwright
import json
import time
import os
import random
from datetime import datetime

# Configuration
WATCHLIST_FILE = 'stock_watchlist.json'
TARGET_COUNT = 200
BASE_URL = "https://finance.yahoo.com/markets/options"

SLASH_TRADERS_URL = "https://slashtraders.com/tw/tools/most-active-options-today/"

def get_symbols_from_slashtraders(count=200):
    """
    Scrape symbols from SlashTraders using Playwright.
    Iterates through pagination to get ~200 stocks.
    """
    symbols = []
    
    print(f"Fetching most active options from SlashTraders...")
    
    with sync_playwright() as p:
        # Launch browser (Headless=True usually works for SlashTraders, but can be set to False if needed)
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        try:
            print(f"  Navigating to {SLASH_TRADERS_URL}...")
            page.goto(SLASH_TRADERS_URL, timeout=60000, wait_until='networkidle')
            
            # Wait for table to load
            try:
                page.wait_for_selector('table.ninja_table_pro tbody tr', timeout=20000)
            except:
                print("  ❌ Timeout: Table not found.")
                browser.close()
                return []

            # Pagination Loop
            page_num = 1
            while len(symbols) < count:
                print(f"  Processing page {page_num}...")
                
                # Extract symbols from current page
                rows_data = page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('table.ninja_table_pro tbody tr');
                        return Array.from(rows).map(row => {
                            // Symbol is usually in the first column (nth-child(1) or class ninja_column_0)
                            // We look for the 'a' tag or just text in the first cell
                            const symbolCell = row.querySelector('td.ninja_column_0'); 
                            if (symbolCell) {
                                return symbolCell.innerText.trim();
                            }
                            // Fallback to first td if class not found
                            const firstTd = row.querySelector('td');
                            return firstTd ? firstTd.innerText.trim() : null;
                        }).filter(s => s && /^[A-Z]+$/.test(s));
                    }
                """)
                
                if not rows_data:
                    print("  ⚠️ No symbols found on this page.")
                    break
                
                new_batch = [s for s in rows_data if s not in symbols]
                symbols.extend(new_batch)
                print(f"    Found {len(new_batch)} new symbols (Total: {len(symbols)})")
                
                if len(symbols) >= count:
                    break
                
                # Try to go to next page
                # The pagination usually looks like [1] [2] ... [Next] or just numbers.
                # We can try finding the 'Next' button or the link to page_num + 1.
                
                try:
                    # Look for the "Next" button specifically in the footable/ninja table pagination
                    # Because Ninja Tables pagination often has specific classes
                    
                    # Try clicking the next page number directly if 'Next' button is hard to identify reliable
                    # But usually Ninja Tables has a 'next' arrow/button.
                    # Let's try to find a link with the next page number first, as it's often more reliable.
                    
                    next_page_num = page_num + 1
                    
                    # Evaluation to find and click the next page button/link
                    clicked = page.evaluate(f"""
                        (nextPage) => {{
                            // Try finding a link/button with the exact text of the next page number
                            const links = Array.from(document.querySelectorAll('.nt_pagination a, .footable-page-link'));
                            const nextLink = links.find(el => el.innerText.trim() == nextPage.toString());
                            
                            if (nextLink) {{
                                nextLink.click();
                                return true;
                            }}
                            
                            // Fallback: Try looking for a "Next" or ">" button
                            const nextBtn = links.find(el => el.innerText.includes('›') || el.innerText.includes('Next') || el.getAttribute('aria-label') == 'Next');
                             if (nextBtn) {{
                                nextBtn.click();
                                return true;
                            }}
                            
                            return false;
                        }}
                    """, next_page_num)
                    
                    if clicked:
                         # Wait for table to update. 
                         # We can wait for a generic short time or try to wait for a loading spinner to disappear
                         time.sleep(3) 
                         page_num += 1
                    else:
                        print("  ⚠️ Could not find Next page link. Reached end?")
                        break
                        
                except Exception as e:
                    print(f"  ⚠️ Error navigating to next page: {e}")
                    break
                    
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        browser.close()
        
    return symbols

def update_watchlist_file(new_symbols):
    """
    Update the watchlist JSON file while preserving settings.
    """
    current_data = {}
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading existing file: {e}. Creating new one.")
            
    # Preserve settings, update stocks
    settings = current_data.get('settings', {
        "analysis_period": 60,
        "rsi_oversold": 30,
        "rsi_overbought": 70
    })
    
    # Create new data structure
    new_data = {
        "stocks": new_symbols,
        "settings": settings,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Backup existing file
    if os.path.exists(WATCHLIST_FILE):
        backup_name = f"{WATCHLIST_FILE}.bak"
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as source:
                with open(backup_name, 'w', encoding='utf-8') as dest:
                    dest.write(source.read())
            print(f"✅ Backup created: {backup_name}")
        except Exception as e:
            print(f"⚠️ Failed to create backup: {e}")

    # Write new file
    try:
        with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully updated {WATCHLIST_FILE} with {len(new_symbols)} stocks.")
    except Exception as e:
        print(f"❌ Failed to write file: {e}")

def run_update():
    """
    Main function to run the watchlist update.
    Returns True if successful, False otherwise.
    """
    print("🚀 Starting Watchlist Update (Playwright Edition)...")
    
    # Try to import playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright is not installed. Please run: pip install playwright && playwright install")
        return False

    # Fetch Top Stocks from SlashTraders
    try:
        final_list = get_symbols_from_slashtraders(count=TARGET_COUNT)
        
        # Limit to Target Count
        final_list = final_list[:TARGET_COUNT]
        
        print(f"\n📊 Summary:")
        print(f"  - Total Stocks Found: {len(final_list)}")
        
        if final_list and len(final_list) > 0:
            update_watchlist_file(final_list)
            return True
        else:
            print("❌ No stocks found. Watchlist not updated.")
            return False
            
    except Exception as e:
        print(f"❌ Update failed with error: {e}")
        return False

if __name__ == "__main__":
    run_update()
