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
st.caption("Automated live DOM multiplier tracker built for Streamlit Cloud.")

# Sidebar Controls
st.sidebar.header("Configuration")
target_url = st.sidebar.text_input("Target URL", "https://odibets.com/casino/aviator")
scan_interval = st.sidebar.slider("Check Interval (seconds)", 1.0, 5.0, 2.0)

# Session State Storage
if "records" not in st.session_state:
    st.session_state.records = []

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Connection Status")
    status_box = st.empty()

with col_right:
    st.subheader("Live Multipliers Log")
    metric_box = st.empty()
    table_box = st.empty()

start_btn = st.sidebar.button("🚀 Start Monitoring")

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Chromium binary path on Linux
    chrome_path = "/usr/bin/chromium"
    if os.path.exists(chrome_path):
        options.binary_location = chrome_path

    return webdriver.Chrome(options=options)

if start_btn:
    status_box.info("Initializing cloud browser driver...")
    driver = None

    try:
        driver = setup_browser()
        status_box.info(f"Connecting to {target_url}...")
        driver.get(target_url)
        time.sleep(8)  # Wait for dynamic iframe scripts to load

        status_box.success("Connected! Scraper running successfully...")
        last_multiplier = None

        while True:
            # 1. Switch to Aviator game iframe if present
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if len(iframes) > 0:
                driver.switch_to.frame(iframes[0])

            # 2. Extract DOM Page Source
            html_source = driver.page_source
            soup = BeautifulSoup(html_source, "html.parser")

            # 3. Search for payout/round history elements in DOM
            payout_elements = soup.find_all(class_=lambda c: c and ("payout" in c.lower() or "bubble" in c.lower() or "history" in c.lower()))

            extracted_val = None
            for el in payout_elements:
                text = el.get_text().strip()
                if "x" in text.lower():
                    clean = text.lower().replace("x", "").replace(" ", "").strip()
                    try:
                        extracted_val = float(clean)
                        break
                    except ValueError:
                        continue

            # Revert back to main page context
            driver.switch_to.default_content()

            # 4. Log extracted multipliers
            if extracted_val and extracted_val != last_multiplier:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.records.insert(0, {"Timestamp": ts, "Multiplier": f"{extracted_val}x"})

                # Save to CSV
                with open("aviator_records.csv", "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([ts, extracted_val])

                last_multiplier = extracted_val

            # 5. Update UI
            if st.session_state.records:
                metric_box.metric("Latest Captured Value", st.session_state.records[0]["Multiplier"])
                table_box.dataframe(pd.DataFrame(st.session_state.records), use_container_width=True)

            time.sleep(scan_interval)

    except Exception as e:
        status_box.error(f"Execution Error: {str(e)}")
    finally:
        if driver:
            driver.quit()
