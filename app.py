import os
import time
import csv
import pandas as pd
import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.3, 2.0, 0.5)

# Target URLs
if selected_room == "Room 1":
    target_url = "https://odibets.com/casino/aviator?room=aviator"
else:
    target_url = "https://odibets.com/casino/aviator?room=aviator2"

st.sidebar.info(f"Targeting: **{selected_room}**\nURL: `{target_url}`")

# Session State Storage
if "records" not in st.session_state:
    st.session_state.records = []
if "last_batch" not in st.session_state:
    st.session_state.last_batch = []

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
    """Applies color to numerical text directly."""
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
    st.session_state.last_batch = []
    driver = None
    attempt = 0

    # Continuous long-running loop
    while True:
        try:
            attempt += 1
            status_box.info(f"Connecting to {selected_room} (Session #{attempt})...")
            
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

            driver = setup_browser()
            driver.get(target_url)
            time.sleep(5)  # Initial DOM load

            # Target precise room inside iframe structure
            if selected_room == "Room 2":
                try:
                    room2_tabs = driver.find_elements(By.XPATH, "//*[contains(text(), 'Room 2')]")
                    for tab in room2_tabs:
                        if tab.is_displayed():
                            tab.click()
                            time.sleep(2)
                            break
                except Exception:
                    pass

            status_box.success(f"Active Live Tracker: {selected_room}")

            # Sub-loop for real-time high-speed DOM polling
            while True:
                # 1. Access active game iframe
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if len(iframes) > 0:
                    driver.switch_to.frame(iframes[0])

                # 2. Extract DOM Page Source
                html_source = driver.page_source
                soup = BeautifulSoup(html_source, "html.parser")

                # 3. Target payout history bubbles
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

                # 5. Process newly landed multiplier rounds only
                if current_batch:
                    # Case A: Initial run load
                    if not st.session_state.last_batch:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        for val in reversed(current_batch):
                            entry = {
                                "Timestamp": ts,
                                "Multiplier": f"{val:.2f}",
                                "Raw_Val": val
                            }
                            st.session_state.records.insert(0, entry)
                        st.session_state.last_batch = current_batch

                    # Case B: Subsequent checks — isolate only newly added top elements
                    elif current_batch != st.session_state.last_batch:
                        new_items = []
                        for val in current_batch:
                            if val == st.session_state.last_batch[0]:
                                break
                            new_items.append(val)

                        if new_items:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            for val in reversed(new_items):
                                entry = {
                                    "Timestamp": ts,
                                    "Multiplier": f"{val:.2f}",
                                    "Raw_Val": val
                                }
                                st.session_state.records.insert(0, entry)

                                # Save single unique entry to CSV
                                with open("aviator_records.csv", "a", newline="") as f:
                                    writer = csv.writer(f)
                                    writer.writerow([ts, selected_room, val])

                        st.session_state.last_batch = current_batch

                # 6. Render Dashboard Table & Badge
                if st.session_state.records:
                    latest_val = st.session_state.records[0]["Raw_Val"]
                    
                    if latest_val < 2.0:
                        badge_color = "#3498db"
                    elif 2.0 <= latest_val < 10.0:
                        badge_color = "#9b59b6"
                    else:
                        badge_color = "#e91e63"

                    metric_box.markdown(
                        f"### Latest Value: <span style='color: {badge_color}; font-weight: bold;'>{latest_val:.2f}x</span>",
                        unsafe_allow_html=True
                    )
                    
                    df = pd.DataFrame(st.session_state.records)[["Timestamp", "Multiplier"]]
                    styled_df = df.style.map(color_multiplier_text, subset=["Multiplier"])
                    
                    table_box.dataframe(styled_df, use_container_width=True)

                time.sleep(scan_interval)

        except Exception as e:
            status_box.warning(f"Re-synchronizing session... ({str(e)[:50]})")
            time.sleep(2)
