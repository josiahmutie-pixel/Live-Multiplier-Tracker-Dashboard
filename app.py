import os
import time
import csv
import pandas as pd
import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from pyvirtualdisplay import Display

# Start headless virtual display for Streamlit Cloud
try:
    display = Display(visible=0, size=(1920, 1080))
    display.start()
except Exception:
    pass

st.set_page_config(
    page_title="Aviator Live Multiplier Dashboard",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS for Color Badges
st.markdown("""
<style>
.badge-blue {
    background-color: #3498db;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: bold;
}
.badge-purple {
    background-color: #9b59b6;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: bold;
}
.badge-pink {
    background-color: #e91e63;
    color: white;
    padding: 4px 10px;
    border-radius: 6px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("✈️ OdiBets Aviator Live Tracker")
st.caption("Auto-reconnecting live DOM tracker with color-coded multiplier categories.")

# Sidebar Configuration
st.sidebar.header("Room & Scan Settings")

selected_room = st.sidebar.radio(
    "Choose Aviator Room:",
    options=["Room 1", "Room 2"],
    index=0
)

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.5, 3.0, 1.0)

# Build Target URL dynamically based on room selection
if selected_room == "Room 1":
    target_url = "https://odibets.com/casino/aviator?room=aviator"
else:
    target_url = "https://odibets.com/casino/aviator?room=aviator2"

st.sidebar.info(f"Targeting: **{selected_room}**\nURL: `{target_url}`")

# Session State Storage
if "records" not in st.session_state:
    st.session_state.records = []

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Connection Status")
    status_box = st.empty()

with col_right:
    st.subheader(f"Live Multipliers ({selected_room})")
    metric_box = st.empty()
    table_box = st.empty()

start_btn = st.sidebar.button("🚀 Start Monitoring")

def get_category_and_color(val):
    if val < 2.0:
        return "Blue (< 2.0x)", "#3498db"
    elif 2.0 <= val < 10.0:
        return "Purple (2x - 10x)", "#9b59b6"
    else:
        return "Pink (>= 10x)", "#e91e63"

def highlight_rows(row):
    val = row["Raw_Val"]
    _, color = get_category_and_color(val)
    return [f'background-color: {color}; color: white; font-weight: bold;' if col in ["Multiplier", "Category"] else '' for col in row.index]

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    chrome_path = "/usr/bin/chromium"
    if os.path.exists(chrome_path):
        options.binary_location = chrome_path

    return webdriver.Chrome(options=options)

if start_btn:
    st.session_state.records = []
    driver = None
    
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            status_box.info(f"Launching browser for {selected_room} (Attempt {retry_count + 1})...")
            
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

            driver = setup_browser()
            status_box.info(f"Connecting to {target_url}...")
            driver.get(target_url)
            time.sleep(7)  # Wait for iframe load

            # Explicitly click room tab if present in main DOM
            try:
                room_btn = driver.find_element(By.XPATH, f"//*[contains(text(), '{selected_room}')]")
                room_btn.click()
                time.sleep(2)
            except Exception:
                pass

            status_box.success(f"Connected to {selected_room}! Live tracking active...")
            
            # Reset retry count on successful connection
            retry_count = 0

            # Main Parsing Loop
            while True:
                # 1. Switch to Aviator game iframe if present
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if len(iframes) > 0:
                    driver.switch_to.frame(iframes[0])

                # 2. Extract DOM Page Source
                html_source = driver.page_source
                soup = BeautifulSoup(html_source, "html.parser")

                # 3. Find history bubble elements
                payout_elements = soup.find_all(class_=lambda c: c and ("payout" in c.lower() or "bubble" in c.lower()))

                driver.switch_to.default_content()

                # 4. Extract numerical values
                current_batch = []
                for el in payout_elements:
                    text = el.get_text().strip()
                    if "x" in text.lower():
                        clean = text.lower().replace("x", "").replace(" ", "").strip()
                        try:
                            val = float(clean)
                            current_batch.append(val)
                        except ValueError:
                            continue

                # 5. Reverse batch to maintain chronological order
                for val in reversed(current_batch):
                    if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        category, _ = get_category_and_color(val)
                        
                        entry = {
                            "Timestamp": ts,
                            "Multiplier": f"{val}x",
                            "Category": category,
                            "Room": selected_room,
                            "Raw_Val": val
                        }
                        
                        st.session_state.records.insert(0, entry)

                        # Write log entry to CSV
                        with open("aviator_grouped_records.csv", "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow([ts, selected_room, val, category])

                # 6. Render Updates
                if st.session_state.records:
                    latest = st.session_state.records[0]
                    val_num = latest["Raw_Val"]
                    badge_cls = "badge-blue" if val_num < 2.0 else ("badge-purple" if val_num < 10.0 else "badge-pink")
                    
                    metric_box.markdown(
                        f"### Latest Value: <span class='{badge_cls}'>{latest['Multiplier']} ({latest['Category']})</span>",
                        unsafe_allow_html=True
                    )
                    
                    df = pd.DataFrame(st.session_state.records)[["Timestamp", "Room", "Multiplier", "Category", "Raw_Val"]]
                    styled_df = df.style.apply(highlight_rows, axis=1).drop(columns=["Raw_Val"])
                    
                    table_box.dataframe(styled_df, use_container_width=True)

                time.sleep(scan_interval)

        except Exception as e:
            retry_count += 1
            status_box.warning(f"Connection glitch encountered: {str(e)}. Reconnecting ({retry_count}/{max_retries})...")
            time.sleep(4)

    if retry_count >= max_retries:
        status_box.error("Max reconnect attempts reached. Please click 'Start Monitoring' to restart.")
        if driver:
            driver.quit()
