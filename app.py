import os
import gc
import time
import csv
import glob
import pandas as pd
import streamlit as st
from datetime import datetime

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

# Cleanup any temporary screenshot/image artifacts to free RAM/disk space
def cleanup_temp_files():
    try:
        temp_files = glob.glob("/tmp/*.png") + glob.glob("*.png")
        for f in temp_files:
            try:
                os.remove(f)
            except Exception:
                pass
    except Exception:
        pass

# Run initial disk/memory cleanup
cleanup_temp_files()

# Sidebar Configuration
st.sidebar.header("Room & Scan Settings")

selected_room = st.sidebar.radio(
    "Choose Aviator Room:",
    options=["Room 1", "Room 2"],
    index=0
)

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.3, 2.0, 0.5)

# Session State Storage Initialization (Capped to prevent RAM overflow)
if "records" not in st.session_state:
    st.session_state.records = []

# Sidebar Action Buttons
start_btn = st.sidebar.button("🚀 Start Monitoring")
reset_btn = st.sidebar.button("🗑️ Reset Recorded Data")

if reset_btn:
    st.session_state.records = []
    if os.path.exists("aviator_records.csv"):
        open("aviator_records.csv", "w").close()
    cleanup_temp_files()
    st.sidebar.success("Data cleared and memory freed!")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Connection Status")
    status_box = st.empty()

with col_right:
    st.subheader(f"Live Multipliers ({selected_room})")
    metric_box = st.empty()
    table_box = st.empty()

def color_multiplier_text(val):
    """Applies color formatting strictly to text numbers."""
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
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disk-cache-size=1")
    options.add_argument("--media-cache-size=1")
    options.add_argument("--window-size=1280,720")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    chrome_path = "/usr/bin/chromium"
    if os.path.exists(chrome_path):
        options.binary_location = chrome_path

    return webdriver.Chrome(options=options)

if start_btn:
    driver = None

    while True:
        try:
            status_box.info(f"Connecting to {selected_room}...")
            
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

            cleanup_temp_files()
            gc.collect()

            driver = setup_browser()
            driver.get("https://odibets.com/casino/aviator")
            time.sleep(5)

            # Explicitly trigger Room Tab on OdiBets UI
            try:
                target_label = "Room 1" if selected_room == "Room 1" else "Room 2"
                tab_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{target_label}')]")
                for tab in tab_elements:
                    if tab.is_displayed():
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(3)
                        break
            except Exception:
                pass

            # Focus into main game frame once
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                driver.switch_to.frame(iframes[0])

            status_box.success(f"Connected to {selected_room}! Tracking active...")

            # Real-time Extraction Loop
            loop_counter = 0
            while True:
                loop_counter += 1
                try:
                    # Extract latest multiplier bubble
                    latest_bubble = driver.find_elements(
                        By.CSS_SELECTOR, 
                        ".payouts-block .bubble-multiplier, .payout-tag, .payouts-wrapper div"
                    )

                    if latest_bubble:
                        text = latest_bubble[0].text.strip()
                        if "x" in text.lower():
                            clean = text.lower().replace("x", "").replace(" ", "").strip()
                            val = float(clean)

                            # Record only new incoming values
                            if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                entry = {
                                    "Timestamp": ts,
                                    "Multiplier": f"{val:.2f}",
                                    "Raw_Val": val
                                }
                                
                                st.session_state.records.insert(0, entry)

                                # Cap in-memory history to last 50 items to keep RAM low
                                if len(st.session_state.records) > 50:
                                    st.session_state.records = st.session_state.records[:50]

                                # Save full long-term data to CSV file on disk
                                with open("aviator_records.csv", "a", newline="") as f:
                                    writer = csv.writer(f)
                                    writer.writerow([ts, selected_room, val])

                                # Update display metrics
                                if val < 2.0:
                                    badge_color = "#3498db"
                                elif 2.0 <= val < 10.0:
                                    badge_color = "#9b59b6"
                                else:
                                    badge_color = "#e91e63"

                                metric_box.markdown(
                                    f"### Latest Value: <span style='color: {badge_color}; font-weight: bold;'>{val:.2f}</span>",
                                    unsafe_allow_html=True
                                )
                                
                                df = pd.DataFrame(st.session_state.records)[["Timestamp", "Multiplier"]]
                                styled_df = df.style.map(color_multiplier_text, subset=["Multiplier"])
                                table_box.dataframe(styled_df, use_container_width=True)

                except Exception:
                    pass

                # Perform memory garbage collection every 20 checks
                if loop_counter % 20 == 0:
                    gc.collect()
                    cleanup_temp_files()

                time.sleep(scan_interval)

        except Exception as e:
            status_box.warning(f"Re-synchronizing stream... ({str(e)[:40]})")
            time.sleep(2)
