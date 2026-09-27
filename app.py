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

st.title("✈️ OdiBets Aviator Live Tracker")

# Sidebar Configuration
st.sidebar.header("Room & Scan Settings")

selected_room = st.sidebar.radio(
    "Choose Aviator Room:",
    options=["Room 1", "Room 2"],
    index=0
)

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.5, 3.0, 1.0)

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

def color_multiplier_text(val):
    """Applies color to the numerical text only."""
    try:
        num = float(val)
        if num < 2.0:
            return 'color: #3498db; font-weight: bold;'  # Blue
        elif 2.0 <= num < 10.0:
            return 'color: #9b59b6; font-weight: bold;'  # Purple
        else:
            return 'color: #e91e63; font-weight: bold;'  # Pink
    except ValueError:
        return ''

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
            status_box.info(f"Connecting to {selected_room}...")
            
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

            driver = setup_browser()
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
            retry_count = 0

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

                # 4. Extract numerical values (cleaned without 'x')
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

                # 5. Add new records chronologically
                for val in reversed(current_batch):
                    if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        entry = {
                            "Timestamp": ts,
                            "Multiplier": f"{val:.2f}",
                            "Raw_Val": val
                        }
                        
                        st.session_state.records.insert(0, entry)

                        # Write to CSV log file
                        with open("aviator_records.csv", "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow([ts, selected_room, val])

                # 6. Render Updates
                if st.session_state.records:
                    latest_val = st.session_state.records[0]["Raw_Val"]
                    
                    if latest_val < 2.0:
                        badge_color = "#3498db"
                    elif 2.0 <= latest_val < 10.0:
                        badge_color = "#9b59b6"
                    else:
                        badge_color = "#e91e63"

                    metric_box.markdown(
                        f"### Latest Value: <span style='color: {badge_color}; font-weight: bold;'>{latest_val:.2f}</span>",
                        unsafe_allow_html=True
                    )
                    
                    # Clean table generation
                    df = pd.DataFrame(st.session_state.records)[["Timestamp", "Multiplier"]]
                    styled_df = df.style.map(color_multiplier_text, subset=["Multiplier"])
                    
                    table_box.dataframe(styled_df, use_container_width=True)

                time.sleep(scan_interval)

        except Exception as e:
            retry_count += 1
            status_box.warning(f"Reconnecting ({retry_count}/{max_retries})...")
            time.sleep(3)

    if retry_count >= max_retries:
        status_box.error("Max reconnect attempts reached. Click 'Start Monitoring' to restart.")
        if driver:
            driver.quit()
