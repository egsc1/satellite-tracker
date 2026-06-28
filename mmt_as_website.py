import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import plotly.graph_objects as go
import zipfile
import io
import time

# --- PAGE SETUP ---
st.set_page_config(page_title="MMT Debris Tracker", layout="wide")
st.title("EH Debris StdMg/Time Plots")
st.write("Light curves from satellite debris using the MMT Database. Select satellites to compare, or download raw data directly! :)")

Website = "http://mmt.favor2.info/satellites"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. CACHED SCRAPERS ---
@st.cache_data(ttl=3600, show_spinner="Scraping satellite database...")
def fetch_satellite_list():
    search_payload = {
        "action": "search", "var_nonvariable": "on",
        "var_variable": "on", "var_periodic": "on", "type_4": "on" 
    }
    response = requests.post(Website, headers=headers, data=search_payload)
    t_links = {}
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        for a_tag in soup.find_all('a'):
            if a_tag.text.strip() == 'T' and '/download' in a_tag.get('href', ''):
                parent_row = a_tag.find_parent('tr')
                if parent_row:
                    cols = parent_row.find_all(['td', 'th'])
                    if len(cols) >= 3:
                        track_name = cols[2].text.strip()
                        if "DEB" in track_name.upper():
                            t_links[track_name] = urljoin(Website, a_tag['href'])
    return t_links

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_light_curve(target_url):
    data_resp = requests.get(target_url, headers=headers)
    times = []
    mags = []
    skipped_lines = 0
    
    if data_resp.status_code == 200:
        for line in data_resp.text.split('\n'):
            if line.startswith('#') or not line.strip(): continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    datetime_str = f"{parts[0]} {parts[1]}"
                    if '.' in parts[1]:
                        time_val = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f") 
                    else:
                        time_val = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    mag_val = float(parts[2])
                    times.append(time_val)
                    mags.append(mag_val)
                except ValueError:
                    skipped_lines += 1
    return times, mags, skipped_lines

def convert_to_csv(times, mags, sat_name="Satellite"):
    csv_str = f"Satellite,Time (UTC),Standard Magnitude\n"
    for t, m in zip(times, mags):
        csv_str += f"{sat_name},{t},{m}\n"
    return csv_str.encode('utf-8')

# Get the links
satellite_data = fetch_satellite_list()

# --- 2. USER INTERFACE ---
if not satellite_data:
    st.error("Failed to connect to the MMT database. Please check your connection.")
else:
    sat_names = list(satellite_data.keys())
    
    col_graph, col_download = st.columns([2, 1])
    
    with col_graph:
        selected_sats = st.multiselect(
            "📊 Search and select DEB Satellites to graph/compare:", 
            options=sat_names,
            placeholder="Choose one or more satellites to plot..."
        )
        
    with col_download:
        # --- UNCAPPED BULK DOWNLOAD SECTION ---
        with st.expander("Super speedy data downloader 9000", expanded=True):
            st.write("So you don't have to experience the slog of waiting for the graphs to load to get the CSVs")
            
            # Master toggle for all satellites
            download_all = st.checkbox("Get EVERY CSV (do this at your own risk...)")
            
            if download_all:
                bulk_sats = sat_names
            else:
                # Removed the max_selections cap completely
                bulk_sats = st.multiselect(
                    "Pick the satellites you want :)",
                    options=sat_names,
                    key="bulk_dl_select"
                )
            
            if bulk_sats:
                if st.button("Make a 'definitely not' ZIP bomb ^_^", use_container_width=True):
                    
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, sat in enumerate(bulk_sats):
                            status_text.text(f"Fetching data for {sat}... ({i+1}/{len(bulk_sats)})")
                            dl_url = satellite_data[sat]
                            
                            # Fetch the data
                            dl_times, dl_mags, _ = fetch_light_curve(dl_url)
                            
                            if dl_times:
                                # Convert to CSV and add it to the ZIP folder
                                csv_data = convert_to_csv(dl_times, dl_mags, sat)
                                zip_file.writestr(f"{sat}_raw_data.csv", csv_data)
                                
                            # POLITE SCRAPING: Pause for 0.4 seconds to balance server limits and Streamlit timeouts
                            time.sleep(0.4) 
                            
                            progress_bar.progress((i + 1) / len(bulk_sats))
                            
                        status_text.success(f"Successfully stole {len(bulk_sats)} files!")
                        
                    st.download_button(
                        label="Download ZIPs",
                        data=zip_buffer.getvalue(),
                        file_name="mmt_debris_bulk_data.zip",
                        mime="application/zip",
                        use_container_width=True,
                        type="primary"
                    )

    # --- 3. PROCESS MULTIPLE SATELLITES FOR GRAPHING ---
    if selected_sats:
        fig = go.Figure()
        
        global_min_date = None
        global_max_date = None
        all_downloaded_data = {}
        
        for sat in selected_sats:
            target_url = satellite_data[sat]
            
            with st.spinner(f"Loading graph data for {sat}..."):
                times, mags, skipped = fetch_light_curve(target_url)
                
            if len(times) > 0:
                all_downloaded_data[sat] = {"times": times, "mags": mags}
                
                sat_min = min(times).date()
                sat_max = max(times).date()
                if global_min_date is None or sat_min < global_min_date: global_min_date = sat_min
                if global_max_date is None or sat_max > global_max_date: global_max_date = sat_max
                
                fig.add_trace(go.Scatter(
                    x=times, y=mags, 
                    mode='lines+markers',
                    marker=dict(size=4),
                    line=dict(width=1),
                    name=sat
                ))
                
                if skipped > 0:
                    st.toast(f"{sat}: Skipped {skipped} corrupted lines.", icon="⚠️")
            else:
                st.error(f"Failed to extract valid data for {sat}.")

        # --- 4. RENDER MASTER PLOT ---
        if all_downloaded_data:
            fig.update_layout(
                title="Master Light Curve Comparison",
                xaxis_title="Time (UTC)",
                yaxis_title="Standard Magnitude",
                yaxis=dict(autorange="reversed"), 
                hovermode="x unified",
                height=600,
                margin=dict(l=20, r=20, t=50, b=20),
                legend_title_text="Satellites"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- GRAPHED DATA DOWNLOAD SECTION ---
            with st.expander("Download Graphed Satellites"):
                st.write("Download the complete track data for the satellites currently displayed.")
                cols = st.columns(len(all_downloaded_data))
                for idx, (sat, data) in enumerate(all_downloaded_data.items()):
                    with cols[idx % len(cols)]:
                        csv_file = convert_to_csv(data["times"], data["mags"], sat)
                        st.download_button(
                            label=f"Download {sat}",
                            data=csv_file,
                            file_name=f"{sat}_full_data.csv",
                            mime="text/csv",
                            key=f"dl_{sat}"
                        )
            
            # --- 5. 24-HOUR SNAPSHOT VIEWER ---
            st.divider() 
            st.subheader("Let's take a closer look >:)")
            st.write("Make it easier to see the actual data lol")
            
            selected_date = st.date_input(
                "Select a date to view:",
                value=global_min_date,
                min_value=global_min_date,
                max_value=global_max_date
            )
            
            fig_daily = go.Figure()
            data_found_for_date = False
            combined_24h_csv = "Satellite,Time (UTC),Standard Magnitude\n"
            
            for sat, data in all_downloaded_data.items():
                daily_times = []
                daily_mags = []
                
                for t, m in zip(data["times"], data["mags"]):
                    if t.date() == selected_date:
                        daily_times.append(t)
                        daily_mags.append(m)
                        combined_24h_csv += f"{sat},{t},{m}\n"
                        
                if len(daily_times) > 0:
                    data_found_for_date = True
                    fig_daily.add_trace(go.Scatter(
                        x=daily_times, y=daily_mags, 
                        mode='lines+markers',
                        marker=dict(size=4), 
                        line=dict(width=1),
                        name=sat
                    ))
            
            if data_found_for_date:
                fig_daily.update_layout(
                    title=f"24-Hour Light Curves on {selected_date}",
                    xaxis_title="Time (UTC)",
                    yaxis_title="Standard Magnitude",
                    yaxis=dict(autorange="reversed"), 
                    hovermode="x unified",
                    height=500,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                st.plotly_chart(fig_daily, use_container_width=True)
                
                st.download_button(
                    label=f"Download CSV for {selected_date}",
                    data=combined_24h_csv.encode('utf-8'),
                    file_name=f"debris_snapshot_{selected_date}.csv",
                    mime="text/csv",
                    key="dl_snapshot"
                )
            else:
                st.info(f"Uhhh I got nothin'. (No data was found for this satellite on {selected_date}.")
