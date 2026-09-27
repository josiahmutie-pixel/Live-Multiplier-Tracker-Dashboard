import os
import time
import csv
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

# Sidebar Configuration
st.sidebar.header("Room & Scan Settings")

selected_room = st.sidebar.radio(
    "Choose Aviator Room:",
    options=["Room 1", "Room 2"],
    index=0
)

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.1, 1.5, 0.2)

# Session State Storage Initialization
if "records" not in st.session_state:
    st.session_state.records = []

# Sidebar Action Buttons
start_btn = st.sidebar.button("🚀 Start Monitoring")
reset_btn = st.sidebar.button("🗑️ Reset Recorded Data")

if reset_btn:
    st.session_state.records = []
    if os.path.exists("aviator_records.csv"):
        open("aviator_records.csv", "w").close()
    st.sidebar.success("Recorded data cleared!")

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
    options.add_argument("--window-size=1920,1080")
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

            driver = setup_browser()
            driver.get("https://odibets.com/casino/aviator")
            time.sleep(5)

            # Switch Room tab on main container
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

            # Switch into game frame ONCE to maximize speed
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                driver.switch_to.frame(iframes[0])

            status_box.success(f"Connected to {selected_room}! Real-time tracking active...")

            # Ultra-fast real-time loop
            while True:
                try:
                    # Target latest multiplier bubble directly (index 0)
                    latest_bubble = driver.find_elements(
                        By.CSS_SELECTOR, 
                        ".payouts-block .bubble-multiplier, .payout-tag, .payouts-wrapper div"
                    )

                    if latest_bubble:
                        text = latest_bubble[0].text.strip()
                        if "x" in text.lower():
                            clean = text.lower().replace("x", "").replace(" ", "").strip()
                            val = float(clean)

                            # Check if value is new
                            if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                entry = {
                                    "Timestamp": ts,
                                    "Multiplier": f"{val:.2f}",
                                    "Raw_Val": val
                                }
                                
                                st.session_state.records.insert(0, entry)

                                # Append to CSV log file
                                with open("aviator_records.csv", "a", newline="") as f:
                                    writer = csv.writer(f)
                                    writer.writerow([ts, selected_room, val])

                                # Update UI immediately on new detection
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

                time.sleep(scan_interval)

        except Exception as e:
            status_box.warning(f"Re-synchronizing room stream... ({str(e)[:40]})")
            time.sleep(2)
