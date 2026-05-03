import streamlit as st
import ephem
import datetime
import requests
import pandas as pd
from geopy.geocoders import Nominatim

# --- CONFIGURATION ---
# Set your OpenWeatherMap API key in Streamlit Secrets
WEATHER_API_KEY = st.secrets.get("WEATHER_KEY")

# Initialize Geocoder
geolocator = Nominatim(user_agent="milky_way_tracker_v2")

def get_astronomy_data(lat, lon, date=None):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.date = date if date else datetime.datetime.utcnow()

    sun = ephem.Sun(obs)
    sun_alt = sun.alt * 57.2958
    
    moon = ephem.Moon(obs)
    moon_alt = moon.alt * 57.2958
    moon_phase = moon.phase
    
    ga_center = ephem.FixedBody()
    ga_center._ra = '17:45:40'
    ga_center._dec = '-29:00:28'
    ga_center.compute(obs)
    core_alt = ga_center.alt * 57.2958

    return {
        "is_dark": sun_alt < -18,
        "sun_alt": sun_alt,
        "moon_visible": moon_alt > 0,
        "moon_phase": moon_phase,
        "core_alt": core_alt
    }

def get_weather_and_forecast(lat, lon):
    if not WEATHER_API_KEY:
        st.error("Missing Weather API Key in Secrets!")
        return None, None
    
    # Current Weather
    curr_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial"
    # 5-Day Forecast
    fore_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial"
    
    try:
        curr_data = requests.get(curr_url).json()
        fore_data = requests.get(fore_url).json()
        return curr_data, fore_data
    except:
        return None, None

# --- UI SETUP ---
st.set_page_config(page_title="Milky Way Tracker Pro", page_icon="🌌")
# --- CUSTOM CSS ---
st.markdown("""
    <style>
    /* Background and Main Container */
    .stApp {
        background: linear-gradient(to bottom, #000428, #004e92);
        color: #ffffff;
    }
    
    /* Custom Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.5);
    }
    
    /* Glassmorphism Cards for Metrics */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
    }
    
    /* Glowing Success Header */
    .stSuccess {
        background-color: rgba(0, 255, 127, 0.1) !important;
        border: 1px solid #00ff7f !important;
        color: #00ff7f !important;
        text-shadow: 0 0 10px #00ff7f;
    }
    
    /* Metric Labels */
    label[data-testid="stMetricLabel"] {
        color: #8892b0 !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
st.title("🌌 Milky Way Visibility Tracker")

# Sidebar Location
st.sidebar.header("📍 Location Settings")
city_input = st.sidebar.text_input("Enter City/State", "Woodstock, VT")

try:
    location = geolocator.geocode(city_input, timeout=10)
    if location:
        lat, lon = location.latitude, location.longitude
        st.sidebar.success(f"Viewing: {location.address.split(',')[0]}")
    else:
        lat, lon = 43.6245, -72.5187
except:
    lat, lon = 43.6245, -72.5187

# --- DATA FETCHING ---
curr_w, fore_w = get_weather_and_forecast(lat, lon)
astro_now = get_astronomy_data(lat, lon)

# --- CURRENT STATUS ---
if curr_w:
    clouds_now = curr_w['clouds']['all']
    is_clear = clouds_now < 25
    is_dark = astro_now['is_dark']
    is_core_up = astro_now['core_alt'] > 0
    is_moon_ok = (not astro_now['moon_visible']) or (astro_now['moon_phase'] < 15)

    if is_clear and is_dark and is_core_up and is_moon_ok:
        st.balloons()
        st.success("✅ PERFECT CONDITIONS RIGHT NOW!")
    else:
        st.warning("🔭 Conditions aren't perfect yet. Check the forecast below.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Cloud Cover", f"{clouds_now}%")
    col2.metric("Core Altitude", f"{astro_now['core_alt']:.1f}°")
    col3.metric("Moon Phase", f"{astro_now['moon_phase']:.0f}%" if astro_now['moon_visible'] else "Down")

# --- FORECAST & CHART ---
if fore_w:
    st.divider()
    st.header("📈 5-Day Visibility Forecast")
    
    forecast_records = []
    for entry in fore_w['list']:
        dt = datetime.datetime.fromtimestamp(entry['dt'])
        a = get_astronomy_data(lat, lon, date=dt)
        
        forecast_records.append({
            "Time": dt,
            "Core Altitude": max(0, a['core_alt']),
            "Cloud Cover": entry['clouds']['all']
        })
    
    df = pd.DataFrame(forecast_records)
    
    # Render the Chart
    st.subheader("Plan Your Session")
    st.line_chart(df.set_index("Time"), color=["#FF4B4B", "#1F77B4"])
    st.caption("🔴 Red = Core Height (Higher is better) | 🔵 Blue = Cloud Cover (Lower is better)")

    # 5-Day Roadmap (Condensed)
    st.subheader("Best Windows")
    road_cols = st.columns(5)
    # Group by day and find best windows
    for i in range(5):
        day_data = df.iloc[i*8 : (i+1)*8] # 3-hour increments
        day_name = day_data['Time'].iloc[0].strftime("%a")
        with road_cols[i]:
            best_hour = day_data.loc[day_data['Core Altitude'].idxmax()]
            is_good = best_hour['Core Altitude'] > 0 and best_hour['Cloud Cover'] < 20
            st.write(f"**{day_name}**")
            st.write("🌌 OK" if is_good else "☁️ No")

st.divider()
st.info("💡 **Pro-Tip:** The best shots are taken during 'Astronomical Night' when the sun is below -18°.")
