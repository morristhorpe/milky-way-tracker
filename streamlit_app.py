import streamlit as st
import ephem
import datetime
import requests

# --- CONFIGURATION ---
# Get a free API key from openweathermap.org
WEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY" 

def get_astronomy_data(lat, lon):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.date = datetime.datetime.utcnow()

    # Sun Logic
    sun = ephem.Sun(obs)
    sun_alt = sun.alt * 57.2958 # Radians to Degrees
    
    # Moon Logic
    moon = ephem.Moon(obs)
    moon_alt = moon.alt * 57.2958
    
    # Galactic Core (Sagittarius A*)
    ga_center = ephem.FixedBody()
    ga_center._ra = '17:45:40'
    ga_center._dec = '-29:00:28'
    ga_center.compute(obs)
    core_alt = ga_center.alt * 57.2958

    return {
        "is_dark": sun_alt < -18,
        "moon_visible": moon_alt > 0,
        "moon_phase": moon.phase,
        "core_alt": core_alt,
        "sun_alt": sun_alt
    }

def get_weather(lat, lon):
    # Mocking weather if no API key is provided, otherwise fetching real data
    if WEATHER_API_KEY == "YOUR_OPENWEATHERMAP_API_KEY":
        return {"clouds": 0, "city": "Unknown (Set API Key)"}
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}"
    data = requests.get(url).json()
    return {"clouds": data['clouds']['all'], "city": data['name']}

# --- STREAMLIT UI ---
st.set_page_config(page_title="Milky Way Tracker", page_icon="🌌")
st.title("🌌 Milky Way Visibility Tracker")

# Sidebar for Location
st.sidebar.header("Location Settings")
lat = st.sidebar.number_input("Latitude", value=43.62, format="%.4f")
lon = st.sidebar.number_input("Longitude", value=-72.51, format="%.4f")

if st.button("Check Visibility Now"):
    astro = get_astronomy_data(lat, lon)
    weather = get_weather(lat, lon)
    
    # Score Logic
    is_clear = weather['clouds'] < 20
    is_core_up = astro['core_alt'] > 0
    is_moon_favorable = not (astro['moon_visible'] and astro['moon_phase'] > 25)
    
    # Hero Result
    if astro['is_dark'] and is_clear and is_core_up and is_moon_favorable:
        st.balloons()
        st.success("### YES! The Milky Way is likely visible!")
    else:
        st.error("### Not Ideal for viewing right now.")

    # Details Grid
    col1, col2, col3 = st.columns(3)
    col1.metric("Cloud Cover", f"{weather['clouds']}%", delta="Clear" if is_clear else "Cloudy", delta_color="inverse")
    col2.metric("Core Altitude", f"{astro['core_alt']:.1f}°", delta="Above Horizon" if is_core_up else "Below")
    col3.metric("Moon Phase", f"{astro['moon_phase']:.0f}%", delta="Dark" if is_moon_favorable else "Too Bright", delta_color="inverse")

    if not astro['is_dark']:
        st.warning(f"Note: It is currently daylight or twilight (Sun altitude: {astro['sun_alt']:.1f}°). Wait for true night!")
