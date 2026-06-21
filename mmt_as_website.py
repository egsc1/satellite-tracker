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
        options=[""] + sat_names, # Add an empty option at the start
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
                
            else:
                st.error("Failed to extract any valid Time/Magnitude data from this file.")
        else:

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
        options=[""] + sat_names, # Add an empty option at the start
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
                
            else:
                st.error("Failed to extract any valid Time/Magnitude data from this file.")
        else:
            st.error(f"Failed to download the data file. Status: {data_resp.status_code}")
            st.error(f"Failed to download the data file. Status: {data_resp.status_code}")
