import os
import time
from playwright.sync_api import sync_playwright

# Folder where screenshots will be saved
OUTPUT_DIR = "everest_sidebar_screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Complete list of tabs from the Everest left sidebar
TABS_TO_CAPTURE = [
    # 1. Main Navigation
    ("01_Home", "https://everest.7span.work/home"),
    ("02_Inbox", "https://everest.7span.work/inbox"),
    ("03_Tasks", "https://everest.7span.work/tasks"),
    
    # 2. Work Section
    ("04_Work_Projects", "https://everest.7span.work/work/projects"),
    ("05_Work_Contracts", "https://everest.7span.work/work/contracts"),
    ("06_Work_Jobs", "https://everest.7span.work/work/jobs"),
    ("07_Work_Billables", "https://everest.7span.work/work/billables"),
    
    # 3. Timesheet Section
    ("08_Timesheet_Plan", "https://everest.7span.work/timesheet/plan"),
    ("09_Timesheet_Logs", "https://everest.7span.work/timesheet/logs"),
    ("10_Timesheet_Draft", "https://everest.7span.work/timesheet/draft"),
    ("11_Timesheet_Reviews", "https://everest.7span.work/timesheet/reviews"),
    ("12_Timesheet_My_Team", "https://everest.7span.work/timesheet/my-team"),
    
    # 4. Reports Section
    ("13_Reports_Jobs_Overview", "https://everest.7span.work/reports/jobs/overview"),
    ("14_Reports_Jobs_Overrun", "https://everest.7span.work/reports/jobs"),
    ("15_Reports_Revenue", "https://everest.7span.work/reports/revenue"),
    ("16_Reports_Billables", "https://everest.7span.work/reports/billables"),
    ("17_Reports_Timesheet", "https://everest.7span.work/reports/timesheet"),
    
    # 5. Organization & Support
    ("18_Org_Employees", "https://everest.7span.work/organization/employees"),
    ("19_Org_Needs_Attention", "https://everest.7span.work/organization/needs-attention"),
    ("20_Support", "https://everest.7span.work/support"),
]

def main():
    print("=" * 60)
    print("🚀 EVEREST SIDEBAR FULL LAYOUT CAPTURE TOOL")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("\n1. Opening Everest...")
        page.goto("https://everest.7span.work/")

        print("\n👉 ACTION REQUIRED:")
        print("Please log in with your account in the browser window.")
        input("Once you see the Everest dashboard, press [ENTER] here to start capturing...\n")

        print("=" * 60)
        print("📸 Starting automatic sidebar layout capture...")
        print("=" * 60)

        success_count = 0
        for index, (tab_name, url) in enumerate(TABS_TO_CAPTURE, 1):
            print(f"[{index}/{len(TABS_TO_CAPTURE)}] Capturing {tab_name}...")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                time.sleep(3)
                
                screenshot_path = os.path.join(OUTPUT_DIR, f"{tab_name}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"    ✅ Saved: {screenshot_path}")
                success_count += 1
            except Exception as e:
                print(f"    ❌ Failed to capture {tab_name}: {e}")

        print("\n" + "=" * 60)
        print(f"🎉 DONE! Successfully captured {success_count}/{len(TABS_TO_CAPTURE)} sidebar layouts.")
        print(f"📁 All images are saved in: {os.path.abspath(OUTPUT_DIR)}")
        print("=" * 60)
        
        browser.close()

if __name__ == "__main__":
    main()
