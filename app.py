import os
import gc
import time
import csv
import glob
import pandas as pd
import streamlit as st
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# Fallback manager import
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.core.os_manager import ChromeType
except ImportError:
    ChromeDriverManager = None

st.set_page_config(
    page_title="Aviator Live Multiplier Dashboard",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ OdiBets Aviator Live Tracker")

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

cleanup_temp_files()

# Sidebar Configuration
st.sidebar.header("Room & Scan Settings")

selected_room = st.sidebar.radio(
    "Choose Aviator Room:",
    options=["Room 1", "Room 2"],
    index=0
)

scan_interval = st.sidebar.slider("Check Interval (seconds)", 0.5, 3.0, 1.0)

# Session state setup
if "records" not in st.session_state:
    st.session_state.records = []
    if os.path.exists("aviator_records.csv"):
        try:
            records_df = pd.read_csv("aviator_records.csv", names=["Timestamp", "Room", "Raw_Val"])
            records_df = records_df[records_df["Room"] == selected_room].tail(50)
            for _, row in records_df.iloc[::-1].iterrows():
                st.session_state.records.append({
                    "Timestamp": str(row["Timestamp"]),
                    "Multiplier": f"{float(row['Raw_Val']):.2f}x",
                    "Raw_Val": float(row["Raw_Val"])
                })
        except Exception:
            pass

start_btn = st.sidebar.button("🚀 Start Monitoring")
reset_btn = st.sidebar.button("🗑️ Reset Recorded Data")

if reset_btn:
    st.session_state.records = []
    if os.path.exists("aviator_records.csv"):
        open("aviator_records.csv", "w").close()
    cleanup_temp_files()
    st.sidebar.success("Recorded data cleared!")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Connection Status")
    status_box = st.empty()
    status_box.info("Ready. Click 'Start Monitoring' to connect.")

with col_right:
    st.subheader(f"Live Multipliers ({selected_room})")
    metric_box = st.empty()
    table_box = st.empty()

def render_dashboard():
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
        table_box.dataframe(df, use_container_width=True, height=400)
    else:
        metric_box.markdown("### Latest Value: `--`")
        table_box.info("No multipliers recorded yet.")

render_dashboard()

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Locate Chromium
    for binary in ["/usr/bin/chromium", "/usr/bin/chromium-browser"]:
        if os.path.exists(binary):
            options.binary_location = binary
            break

    # Try APT system driver path
    for driver_path in ["/usr/bin/chromedriver", "/usr/lib/chromium-browser/chromedriver"]:
        if os.path.exists(driver_path):
            return webdriver.Chrome(service=Service(driver_path), options=options)

    # Try Webdriver Manager fallback
    if ChromeDriverManager:
        try:
            return webdriver.Chrome(
                service=Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
                options=options
            )
        except Exception:
            pass

    return webdriver.Chrome(options=options)

# Helper function to find game iframe recursively
def switch_to_game_iframe(driver):
    driver.switch_to.default_content()
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    
    for index, iframe in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            # Check if nested iframe exists inside this iframe
            inner_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if inner_iframes:
                driver.switch_to.frame(inner_iframes[0])
            
            # Check if payout tags are present in this context
            test_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                ".payouts-block, .payout-tag, .bubble-multiplier, app-stats-widget, .payouts-wrapper"
            )
            if test_elements:
                return True
        except Exception:
            continue
            
    # Fallback to first iframe if matching elements aren't immediately found
    driver.switch_to.default_content()
    if iframes:
        driver.switch_to.frame(iframes[0])
        return True
    return False

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
            time.sleep(8)

            # Click selected room tab if present
            try:
                target_label = "Room 1" if selected_room == "Room 1" else "Room 2"
                tab_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{target_label}')]")
                for tab in tab_elements:
                    if tab.is_displayed():
                        driver.execute_script("arguments[0].click();", tab)
                        time.sleep(4)
                        break
            except Exception:
                pass

            # Switch to active game iframe
            switch_to_game_iframe(driver)

            status_box.success(f"Connected to {selected_room}! Tracking active...")

            loop_counter = 0
            while True:
                loop_counter += 1
                try:
                    # Broad selector list covering Spribe Aviator DOM revisions
                    elements = driver.find_elements(
                        By.CSS_SELECTOR, 
                        ".payouts-block .bubble-multiplier, .payout-tag, .payouts-wrapper div, app-stats-widget div, .payout-item"
                    )

                    found_text = None
                    for el in elements:
                        txt = el.text.strip()
                        if "x" in txt.lower() and len(txt) <= 8:
                            found_text = txt
                            break

                    if found_text:
                        clean = found_text.lower().replace("x", "").replace(" ", "").strip()
                        val = float(clean)

                        if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            entry = {
                                "Timestamp": ts,
                                "Multiplier": f"{val:.2f}x",
                                "Raw_Val": val
                            }
                            
                            st.session_state.records.insert(0, entry)

                            if len(st.session_state.records) > 50:
                                st.session_state.records = st.session_state.records[:50]

                            with open("aviator_records.csv", "a", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow([ts, selected_room, val])

                            render_dashboard()

                except Exception:
                    # Re-verify iframe focus if element context was lost
                    switch_to_game_iframe(driver)

                if loop_counter % 20 == 0:
                    gc.collect()
                    cleanup_temp_files()

                time.sleep(scan_interval)

        except Exception as e:
            status_box.warning(f"Re-synchronizing room stream... ({str(e)[:40]})")
            time.sleep(3)
