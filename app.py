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

scan_interval = st.sidebar.slider("Check Interval (seconds)", 1.0, 5.0, 2.0)

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
    debug_box = st.empty()
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
        table_box.dataframe(df, use_container_width=True, height=450)
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
    options.add_argument("--window-size=1280,720")
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-site-isolation-trials")
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

def extract_multipliers_javascript(driver):
    """Deep JS DOM traversal across all frames without relying on driver frame switching."""
    script = """
    function getMultipliers() {
        let results = [];
        
        function scanDoc(doc) {
            if (!doc) return;
            
            // Query elements
            let selectors = ['.bubble-multiplier', '.payout-tag', '.payout-item', 'app-stats-item', '.payouts-block div'];
            selectors.forEach(sel => {
                let els = doc.querySelectorAll(sel);
                els.forEach(el => {
                    let txt = el.innerText || el.textContent || '';
                    if (txt.toLowerCase().includes('x') && txt.length <= 8) {
                        results.push(txt.trim());
                    }
                });
            });

            // Recurse into iframes
            let iframes = doc.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                try {
                    if (iframe.contentDocument) {
                        scanDoc(iframe.contentDocument);
                    }
                } catch(e) {}
            });
        }

        scanDoc(document);
        return results;
    }
    return getMultipliers();
    """
    try:
        return driver.execute_script(script)
    except Exception:
        return []

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

            status_box.success(f"Connected to {selected_room}! Tracking active...")

            loop_counter = 0
            while True:
                loop_counter += 1
                
                # Execute JS extraction
                raw_extracted = extract_multipliers_javascript(driver)
                
                # Fallback to standard frame traversal if JS recursive scan was blocked by cross-origin security
                if not raw_extracted:
                    driver.switch_to.default_content()
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        try:
                            driver.switch_to.default_content()
                            driver.switch_to.frame(iframe)
                            inner_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                            if inner_iframes:
                                driver.switch_to.frame(inner_iframes[0])
                            
                            elements = driver.find_elements(
                                By.CSS_SELECTOR, 
                                "app-stats-item, .bubble-multiplier, .payout-tag, .payout-item"
                            )
                            for el in elements:
                                txt = el.text.strip()
                                if "x" in txt.lower() and len(txt) <= 8:
                                    raw_extracted.append(txt)
                            if raw_extracted:
                                break
                        except Exception:
                            continue

                current_history = []
                for txt in raw_extracted:
                    clean = txt.lower().replace("x", "").replace(" ", "").strip()
                    try:
                        val = float(clean)
                        current_history.append(val)
                    except ValueError:
                        pass

                # Update status debug box
                debug_box.caption(f"Last scan found {len(current_history)} values in DOM at {datetime.now().strftime('%H:%M:%S')}")

                if current_history:
                    updated = False
                    # Process top history (oldest to newest)
                    for val in reversed(current_history[:20]):
                        if not st.session_state.records or st.session_state.records[0]["Raw_Val"] != val:
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            entry = {
                                "Timestamp": ts,
                                "Multiplier": f"{val:.2f}x",
                                "Raw_Val": val
                            }
                            st.session_state.records.insert(0, entry)
                            updated = True

                            with open("aviator_records.csv", "a", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow([ts, selected_room, val])

                    if updated:
                        if len(st.session_state.records) > 50:
                            st.session_state.records = st.session_state.records[:50]
                        render_dashboard()

                if loop_counter % 20 == 0:
                    gc.collect()
                    cleanup_temp_files()

                time.sleep(scan_interval)

        except Exception as e:
            status_box.warning(f"Re-synchronizing room stream... ({str(e)[:50]})")
            time.sleep(3)
