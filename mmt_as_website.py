import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="MMT Debris Tracker", layout="wide")
st.title("EH Debris StdMg/Time Plots")
st.write("Light curves from satellite debris using the MMT Database. Please select a satellite to view ! :)")

Website = "http://mmt.favor2.info/satellites"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. CACHED SCRAPER ---
# We cache this function so the app doesn't re-scrape the website every time you click something
@st.cache_data(ttl=3600, show_spinner="Scraping satellite database...")
def fetch_satellite_list():
    search_payload = {
        "action": "search",
        "var_nonvariable": "on",
        "var_variable": "on",
        "var_periodic": "on",
        "type_4": "on" 
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

# Get the links
satellite_data = fetch_satellite_list()

# --- 2. USER INTERFACE ---
if not satellite_data:
    st.error("Failed to connect to the MMT database. Please check your connection.")
else:
    # Create a list of names for the dropdown
    sat_names = list(satellite_data.keys())
    
    # A searchable selectbox
    selected_sat = st.selectbox(
        "Search for a DEB Satellite:", 
        options=[""] + sat_names,
        format_func=lambda x: "Select a satellite..." if x == "" else x
    )

    # --- 3. DOWNLOAD & PARSE ---
    if selected_sat:
        target_url = satellite_data[selected_sat]
        
        with st.spinner(f"Downloading raw data for {selected_sat}..."):
            data_resp = requests.get(target_url, headers=headers)
            
        if data_resp.status_code == 200:
            times = []
            mags = []
            skipped_lines = 0
            
            for line in data_resp.text.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                
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
            
            # --- 4. INTERACTIVE PLOT ---
            if len(times) > 0:
                st.success(f"Successfully loaded {len(times)} data points.")
                if skipped_lines > 0:
                    st.warning(f"Note: Skipped {skipped_lines} lines of corrupted/missing data.")
                
                # Create interactive Plotly figure
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, 
                    y=mags, 
                    mode='lines+markers',
                    marker=dict(size=4, color='rgba(0, 100, 255, 0.7)'),
                    line=dict(width=1, color='rgba(0, 100, 255, 0.4)'),
                    name="Magnitude"
                ))
                
                # Format layout and invert Y-axis
                fig.update_layout(
                    title=f"Light Curve: {selected_sat}",
                    xaxis_title="Time (UTC)",
                    yaxis_title="Standard Magnitude",
                    yaxis=dict(autorange="reversed"), # Inverts the axis
                    hovermode="x unified",
                    height=600,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                # Render chart on the website
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 5. 24-HOUR SNAPSHOT VIEWER ---
                st.divider() 
                st.subheader("Let's take a closer look")
                st.write("Isolating 24 hours makes it easier to check if I'm right lol")
                
                # Find the first and last dates in the dataset
                min_date = min(times).date()
                max_date = max(times).date()
                
                # Create the calendar widget
                selected_date = st.date_input(
                    "Select a date to view:",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )
                
                # Filter the lists to ONLY include data from the chosen day
                daily_times = []
                daily_mags = []
                
                for t, m in zip(times, mags):
                    if t.date() == selected_date:
                        daily_times.append(t)
                        daily_mags.append(m)
                        
                # Plot the second graph
                if len(daily_times) > 0:
                    st.success(f"Loaded {len(daily_times)} data points for {selected_date}.")
                    
                    fig_daily = go.Figure()
                    fig_daily.add_trace(go.Scatter(
                        x=daily_times, 
                        y=daily_mags, 
                        mode='lines+markers',
                        marker=dict(size=4, color='rgba(255, 100, 0, 0.7)'), 
                        line=dict(width=1, color='rgba(255, 100, 0, 0.4)'),
                        name="Magnitude (24h)"
                    ))
                    
                    fig_daily.update_layout(
                        title=f"24-Hour Light Curve: {selected_sat} on {selected_date}",
                        xaxis_title="Time (UTC)",
                        yaxis_title="Standard Magnitude",
                        yaxis=dict(autorange="reversed"), 
                        hovermode="x unified",
                        height=500,
                        margin=dict(l=20, r=20, t=50, b=20)
                    )
                    
                    st.plotly_chart(fig_daily, use_container_width=True)
                else:
                    st.info(f"No tracking data recorded for {selected_sat} on {selected_date}.")

            else:
                st.error("Failed to extract any valid Time/Magnitude data from this file.")
        else:
            st.error(f"Failed to download the data file. Status: {data_resp.status_code}")import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="MMT Debris Tracker", layout="wide")
st.title("EH Debris StdMg/Time Plots")
st.write("Light curves from satellite debris using the MMT Database. Select one or more satellites to compare! :)")

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

# NEW: We cache the actual data downloads so we don't spam the server when changing calendar dates!
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

# Get the links
satellite_data = fetch_satellite_list()

# --- 2. USER INTERFACE ---
if not satellite_data:
    st.error("Failed to connect to the MMT database. Please check your connection.")
else:
    sat_names = list(satellite_data.keys())
    
    # NEW: Multiselect instead of a single selectbox
    selected_sats = st.multiselect(
        "Search and select DEB Satellites to compare:", 
        options=sat_names,
        placeholder="Choose one or more satellites..."
    )

    # --- 3. PROCESS MULTIPLE SATELLITES ---
    if selected_sats:
        fig = go.Figure()
        
        # We need master lists to track the absolute earliest and latest dates across ALL selected satellites
        global_min_date = None
        global_max_date = None
        
        # A dictionary to store the data so we can reuse it for the 24-hour viewer below
        all_downloaded_data = {}
        
        for sat in selected_sats:
            target_url = satellite_data[sat]
            
            with st.spinner(f"Loading data for {sat}..."):
                times, mags, skipped = fetch_light_curve(target_url)
                
            if len(times) > 0:
                # Store it for later
                all_downloaded_data[sat] = {"times": times, "mags": mags}
                
                # Update our global calendar boundaries
                sat_min = min(times).date()
                sat_max = max(times).date()
                if global_min_date is None or sat_min < global_min_date: global_min_date = sat_min
                if global_max_date is None or sat_max > global_max_date: global_max_date = sat_max
                
                # Add this satellite's line to the graph! 
                # (Notice I removed the hardcoded color so Plotly will auto-assign distinct colors to each satellite)
                fig.add_trace(go.Scatter(
                    x=times, y=mags, 
                    mode='lines+markers',
                    marker=dict(size=4),
                    line=dict(width=1),
                    name=sat # This ensures the legend works
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
            
            # --- 5. 24-HOUR SNAPSHOT VIEWER ---
            st.divider() 
            st.subheader("📅 24-Hour Snapshot Viewer")
            st.write("Isolate a single day to view specific rotation patterns across your selected debris.")
            
            selected_date = st.date_input(
                "Select a date to view:",
                value=global_min_date,
                min_value=global_min_date,
                max_value=global_max_date
            )
            
            fig_daily = go.Figure()
            data_found_for_date = False
            
            # Loop through the data we already downloaded and filter it by the selected date
            for sat, data in all_downloaded_data.items():
                daily_times = []
                daily_mags = []
                
                for t, m in zip(data["times"], data["magsimport streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import plotly.graph_objects as go

# --- PAGE SETUP ---
st.set_page_config(page_title="MMT Debris Tracker", layout="wide")
st.title("EH Debris StdMg/Time Plots")
st.write("Light curves from satellite debris using the MMT Database. Please select a satellite to view ! :)")

Website = "http://mmt.favor2.info/satellites"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- 1. CACHED SCRAPER ---
# We cache this function so the app doesn't re-scrape the website every time you click something
@st.cache_data(ttl=3600, show_spinner="Scraping satellite database...")
def fetch_satellite_list():
    search_payload = {
        "action": "search",
        "var_nonvariable": "on",
        "var_variable": "on",
        "var_periodic": "on",
        "type_4": "on" 
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

# Get the links
satellite_data = fetch_satellite_list()

# --- 2. USER INTERFACE ---
if not satellite_data:
    st.error("Failed to connect to the MMT database. Please check your connection.")
else:
    # Create a list of names for the dropdown
    sat_names = list(satellite_data.keys())
    
    # A searchable selectbox
    selected_sat = st.selectbox(
        "Search for a DEB Satellite:", 
        options=[""] + sat_names,
        format_func=lambda x: "Select a satellite..." if x == "" else x
    )

    # --- 3. DOWNLOAD & PARSE ---
    if selected_sat:
        target_url = satellite_data[selected_sat]
        
        with st.spinner(f"Downloading raw data for {selected_sat}..."):
            data_resp = requests.get(target_url, headers=headers)
            
        if data_resp.status_code == 200:
            times = []
            mags = []
            skipped_lines = 0
            
            for line in data_resp.text.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                
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
            
            # --- 4. INTERACTIVE PLOT ---
            if len(times) > 0:
                st.success(f"Successfully loaded {len(times)} data points.")
                if skipped_lines > 0:
                    st.warning(f"Note: Skipped {skipped_lines} lines of corrupted/missing data.")
                
                # Create interactive Plotly figure
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=times, 
                    y=mags, 
                    mode='lines+markers',
                    marker=dict(size=4, color='rgba(0, 100, 255, 0.7)'),
                    line=dict(width=1, color='rgba(0, 100, 255, 0.4)'),
                    name="Magnitude"
                ))
                
                # Format layout and invert Y-axis
                fig.update_layout(
                    title=f"Light Curve: {selected_sat}",
                    xaxis_title="Time (UTC)",
                    yaxis_title="Standard Magnitude",
                    yaxis=dict(autorange="reversed"), # Inverts the axis
                    hovermode="x unified",
                    height=600,
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                # Render chart on the website
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 5. 24-HOUR SNAPSHOT VIEWER ---
                st.divider() 
                st.subheader("Let's take a closer look")
                st.write("Isolating 24 hours makes it easier to check if I'm right lol")
                
                # Find the first and last dates in the dataset
                min_date = min(times).date()
                max_date = max(times).date()
                
                # Create the calendar widget
                selected_date = st.date_input(
                    "Select a date to view:",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )
                
                # Filter the lists to ONLY include data from the chosen day
                daily_times = []
                daily_mags = []
                
                for t, m in zip(times, mags):
                    if t.date() == selected_date:
                        daily_times.append(t)
                        daily_mags.append(m)
                        
                # Plot the second graph
                if len(daily_times) > 0:
                    st.success(f"Loaded {len(daily_times)} data points for {selected_date}.")
                    
                    fig_daily = go.Figure()
                    fig_daily.add_trace(go.Scatter(
                        x=daily_times, 
                        y=daily_mags, 
                        mode='lines+markers',
                        marker=dict(size=4, color='rgba(255, 100, 0, 0.7)'), 
                        line=dict(width=1, color='rgba(255, 100, 0, 0.4)'),
                        name="Magnitude (24h)"
                    ))
                    
                    fig_daily.update_layout(
                        title=f"24-Hour Light Curve: {selected_sat} on {selected_date}",
                        xaxis_title="Time (UTC)",
                        yaxis_title="Standard Magnitude",
                        yaxis=dict(autorange="reversed"), 
                        hovermode="x unified",
                        height=500,
                        margin=dict(l=20, r=20, t=50, b=20)
                    )
                    
                    st.plotly_chart(fig_daily, use_container_width=True)
                else:
                    st.info(f"No tracking data recorded for {selected_sat} on {selected_date}.")

            else:
                st.error("Failed to extract any valid Time/Magnitude data from this file.")
        else:
            st.error(f"Failed to download the data file. Status: {data_resp.status_code}")
