import time
import csv
import cv2
import numpy as np
import pytesseract
import pandas as pd
import streamlit as st
from datetime import datetime
from mss import MSS

# Page Configuration
st.set_page_config(
    page_title="Aviator Live Multiplier Tracker",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ OdiBets Aviator Live Tracker & Dashboard")
st.caption("Real-time local screen capture & OCR multiplier extraction.")

# Sidebar Controls for Screen Capture Box
st.sidebar.header("🎯 Crop Region Coordinates")
st.sidebar.info("Adjust these values while looking at the preview image until it crops the latest multiplier box.")

top_pos = st.sidebar.number_input("Top (Y-axis offset)", value=390, step=5)
left_pos = st.sidebar.number_input("Left (X-axis offset)", value=340, step=5)
crop_width = st.sidebar.number_input("Width (Pixels)", value=120, step=5)
crop_height = st.sidebar.number_input("Height (Pixels)", value=50, step=5)
scan_interval = st.sidebar.slider("OCR Scan Rate (seconds)", 0.2, 2.0, 0.5)

# Initialize Session State Data
if "records" not in st.session_state:
    st.session_state.records = []

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Live OCR Monitored Box")
    frame_box = st.empty()
    status_box = st.empty()

with col_right:
    st.subheader("Extracted Multipliers")
    metric_box = st.empty()
    table_box = st.empty()

# Dashboard Control Button
start_tracking = st.sidebar.button("🚀 Start Live Monitoring")

if start_tracking:
    status_box.success("Monitoring desktop screen region...")
    last_multiplier = None

    monitor = {
        "top": int(top_pos),
        "left": int(left_pos),
        "width": int(crop_width),
        "height": int(crop_height)
    }

    with MSS() as sct:
        try:
            while True:
                # 1. Take local screen capture of specified region
                sct_img = sct.grab(monitor)
                frame = np.array(sct_img)

                # Convert BGRA to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                # Display live image snippet in Streamlit UI
                frame_box.image(frame_bgr, channels="BGR", caption="Exact Screen Box Monitored")

                # 2. Image Preprocessing for Clean OCR Reading
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)

                # 3. OCR Text Recognition via Tesseract
                raw_text = pytesseract.image_to_string(thresh, config="--psm 7").strip()

                # 4. Extract & Record Valid Multipliers
                if "x" in raw_text.lower():
                    clean_text = raw_text.lower().replace("x", "").replace(" ", "").strip()
                    try:
                        val = float(clean_text)
                        
                        # Only log when a NEW multiplier appears
                        if val != last_multiplier:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            entry = {"Timestamp": timestamp, "Multiplier": f"{val}x"}
                            st.session_state.records.insert(0, entry)

                            # Append to local CSV
                            with open("aviator_live_records.csv", "a", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow([timestamp, val])

                            last_multiplier = val
                    except ValueError:
                        pass # Ignore misread text frames

                # 5. Render Metric & Data Table Updates
                if st.session_state.records:
                    metric_box.metric("Latest Logged Value", st.session_state.records[0]["Multiplier"])
                    df = pd.DataFrame(st.session_state.records)
                    table_box.dataframe(df, use_container_width=True)

                time.sleep(scan_interval)

        except Exception as err:
            status_box.error(f"Execution Error: {str(err)}")
