import os
import time
import csv
import io
import cv2
import numpy as np
import pytesseract
import pandas as pd
import streamlit as st
from datetime import datetime
from PIL import Image

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from pyvirtualdisplay import Display

# Start Virtual Display for Headless Cloud Environment
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
st.caption("Live OCR extraction and real-time multiplier logging dashboard.")

# Sidebar Configuration
st.sidebar.header("Configuration")
target_url = st.sidebar.text_input("Target URL", "https://odibets.com/casino/aviator")
scan_interval = st.sidebar.slider("OCR Scan Rate (seconds)", 0.5, 3.0, 1.0)

# Session State Initialization
if "records" not in st.session_state:
    st.session_state.records = []

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Live Screen Frame Capture")
    frame_box = st.empty()
    status_box = st.empty()

with col_right:
    st.subheader("Extracted Multipliers")
    metric_box = st.empty()
    table_box = st.empty()

# Control Button
start_tracking = st.button("🚀 Start Monitoring")

def setup_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Check system chromium path for Linux/Streamlit Cloud
    chrome_path = "/usr/bin/chromium"
    if os.path.exists(chrome_path):
        options.binary_location = chrome_path
        
    driver = webdriver.Chrome(options=options)
    return driver

if start_tracking:
    status_box.info("Initializing browser driver...")
    driver = None
    
    try:
        driver = setup_browser()
        status_box.info(f"Navigating to {target_url}...")
        driver.get(target_url)
        time.sleep(5) # Allow page scripts and canvas to load
        
        status_box.success("Connection established! Active tracking running...")
        last_multiplier = None

        while True:
            # Take screenshot of current browser window
            screenshot_bytes = driver.get_screenshot_as_png()
            pil_img = Image.open(io.BytesIO(screenshot_bytes))
            frame = np.array(pil_img)

            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            h, w, _ = frame_bgr.shape

            # Crop central game display region (where multiplier / round history renders)
            crop_region = frame_bgr[int(h*0.32):int(h*0.48), int(w*0.30):int(w*0.70)]

            # Display crop in dashboard UI
            frame_box.image(crop_region, channels="BGR", caption="Monitored OCR Region")

            # Image processing for OCR optimization
            gray = cv2.cvtColor(crop_region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

            # OCR Text Recognition
            raw_text = pytesseract.image_to_string(thresh, config="--psm 6").strip()

            if "x" in raw_text.lower():
                clean_text = raw_text.lower().replace("x", "").replace(" ", "").strip()
                try:
                    val = float(clean_text)
                    if val != last_multiplier:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        entry = {"Timestamp": timestamp, "Multiplier": val}
                        st.session_state.records.insert(0, entry)
                        
                        # Append to CSV locally
                        with open("aviator_live_records.csv", "a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow([timestamp, val])
                        
                        last_multiplier = val
                except ValueError:
                    pass

            # Render UI updates
            if st.session_state.records:
                metric_box.metric("Current Logged Value", f"{st.session_state.records[0]['Multiplier']}x")
                df = pd.DataFrame(st.session_state.records)
                table_box.dataframe(df, use_container_width=True)

            time.sleep(scan_interval)

    except Exception as err:
        status_box.error(f"Execution Error: {str(err)}")
    finally:
        if driver:
            driver.quit()
