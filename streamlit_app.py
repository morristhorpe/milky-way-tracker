import streamlit as st
import ephem
import datetime
import requests
import pandas as pd
from geopy.geocoders import Nominatim

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="Milky Way Pro", page_icon="🌌", layout="wide")

# Custom Deep Space CSS
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to bottom, #000428, #004e92);
        color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.7);
    }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        backdrop-filter: blur(10px);
    }
    .stSuccess {
        background-color: rgba(0, 255, 127, 0.1) !important;
        border: 1px solid #00ff7f !important;
        color: #00ff7f !important;
        text-shadow: 0 0 10px #00ff7f;
    }
    hr { border-top: 1px solid rgba(255,255,255,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC FUNCTIONS ---
WEATHER_API_KEY = st.secrets.get("WEATHER_KEY")
geolocator = Nominatim(user_agent="milky_way_tracker_pro")

def get_astronomy_data(lat, lon, date=None):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.date = date if date else datetime.datetime.utcnow()
    
    sun = ephem.Sun(obs)
    sun_alt = sun.alt * 57.2958
    
    moon = ephem.Moon(obs)
    moon_alt = moon.alt * 57.2958
    
    ga_center = ephem.FixedBody()
    ga_center._ra, ga_center._dec = '17:45:40', '-29:00:28'
    ga_center.compute(obs)
    
    return {
        "is_dark": sun_alt < -18,
        "moon_visible": moon_alt > 0,
        "moon_phase": moon.phase,
        "core_alt": ga_center.alt * 57.2958
    }

def get_weather_forecast(lat, lon):
    if not WEATHER_API_KEY: return None, None
    curr = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial").json()
    fore = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial").json()
    return curr, fore

# --- 3. SIDEBAR & LOCATION ---
st.sidebar.title("🔭 Navigation")
city_input = st.sidebar.text_input("Search Location", "Woodstock, VT")

try:
    loc = geolocator.geocode(city_input, timeout=10)
    lat, lon = (loc.latitude, loc.longitude) if loc else (43.62, -72.51)
    display_name = loc.address.split(',')[0] if loc else "Woodstock"
except:
    lat, lon, display_name = 43.62, -72.51, "Woodstock"

# --- 4. HERO SECTION ---
st.title("🌌 Milky Way Tracker Pro")
st.write(f"**Live Analysis for:** {display_name} | {datetime.datetime.now().strftime('%A, %b %d')}")
st.markdown("---")

# --- 5. CURRENT CONDITIONS ---
curr_w, fore_w = get_weather_forecast(lat, lon)
astro = get_astronomy_data(lat, lon)

if curr_w:
    clouds = curr_w['clouds']['all']
    is_good = clouds < 25 and astro['is_dark'] and astro['core_alt'] > 0 and (not astro['moon_visible'] or astro['moon_phase'] < 15)
    
    if is_good:
        st.balloons()
        st.success("✨ THE STARS ARE ALIGNED: GO OUTSIDE NOW!")
    else:
        st.info("🔭 Galactic Core is not perfectly visible right now. See forecast below.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sky Clarity", f"{100-clouds}% Clear")
    c2.metric("Core Altitude", f"{astro['core_alt']:.1f}°")
    moon_label = "New Moon" if astro['moon_phase'] < 5 else f"{astro['moon_phase']:.0f}% Lit"
    c3.metric("Moon Status", "Hidden" if not astro['moon_visible'] else moon_label)

# --- 6. FORECAST CHART ---
if fore_w:
    st.markdown("### 📈 5-Day Visibility Roadmap")
    data = []
    for e in fore_w['list']:
        dt = datetime.datetime.fromtimestamp(e['dt'])
        a = get_astronomy_data(lat, lon, date=dt)
        data.append({
            "Time": dt,
            "Galaxy Altitude": max(0, a['core_alt']),
            "Cloud Cover": e['clouds']['all']
        })
    
    df = pd.DataFrame(data)
    # Using a vibrant color palette: Cyan for Galaxy, Pink for Clouds
    st.line_chart(df.set_index("Time"), color=["#00f2ff", "#ff007f"])
    st.caption("Look for the 'Golden Window': Cyan Peaks + Pink Valleys.")

    # --- 7. BEST WINDOWS TABLE ---
    st.markdown("### 📅 Next Best Windows")
    best_windows = df[(df['Galaxy Altitude'] > 10) & (df['Cloud Cover'] < 30)].head(5)
    if not best_windows.empty:
        for _, row in best_windows.iterrows():
            st.write(f"✨ **{row['Time'].strftime('%a %I:%M %p')}**: {100-row['Cloud Cover']}% Clear sky with the Galaxy at {row['Galaxy Altitude']:.1f}°")
    else:
        st.write("No perfect windows found in the next 48 hours. Keep checking!")

st.markdown("---")
st.caption("Created for stargazers. Data provided by OpenWeather and PyEphem.")
