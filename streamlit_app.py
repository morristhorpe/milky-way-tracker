import streamlit as st
import ephem
import datetime
import requests
from geopy.geocoders import Nominatim

# --- CONFIGURATION & SECRETS ---
# Ensure these are set in the Streamlit Cloud "Secrets" tab
WEATHER_API_KEY = st.secrets.get("b8f2bbfb54a879f5c173bbc112f9807a")

# Initialize Geocoder
geolocator = Nominatim(user_agent="milky_way_tracker_v1")

def get_astronomy_data(lat, lon):
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)
    obs.date = datetime.datetime.utcnow()

    # Sun position for darkness check
    sun = ephem.Sun(obs)
    sun.compute(obs)
    sun_alt = sun.alt * 57.2958 # Radians to Degrees
    
    # Moon position and phase
    moon = ephem.Moon(obs)
    moon.compute(obs)
    moon_alt = moon.alt * 57.2958
    moon_phase = moon.phase # 0 to 100
    
    # Galactic Center (Sagittarius A*)
    # RA: 17:45:40, Dec: -29:00:28
    ga_center = ephem.FixedBody()
    ga_center._ra = '17:45:40'
    ga_center._dec = '-29:00:28'
    ga_center.compute(obs)
    core_alt = ga_center.alt * 57.2958

    return {
        "is_dark": sun_alt < -18, # Astronomical Twilight
        "sun_alt": sun_alt,
        "moon_visible": moon_alt > 0,
        "moon_alt": moon_alt,
        "moon_phase": moon_phase,
        "core_alt": core_alt
    }

def get_weather(lat, lon):
    if not WEATHER_API_KEY:
        return None
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial"
    try:
        response = requests.get(url)
        data = response.json()
        return {
            "clouds": data['clouds']['all'],
            "temp": data['main']['temp'],
            "city_name": data['name']
        }
    except:
        return None

# --- STREAMLIT UI SETUP ---
st.set_page_config(page_title="Milky Way Tracker", page_icon="🌌", layout="centered")

st.title("🌌 Milky Way Visibility Tracker")
st.markdown("Check if the Galactic Core is visible from your location tonight.")

# --- SIDEBAR LOCATION SEARCH ---
st.sidebar.header("📍 Set Location")
city_input = st.sidebar.text_input("Enter City, State or Landmark", "Woodstock, VT")

# Geocoding logic
try:
    location = geolocator.geocode(city_input, timeout=10)
    if location:
        lat, lon = location.latitude, location.longitude
        st.sidebar.success(f"Location Found!")
        st.sidebar.write(f"**{location.address}**")
    else:
        st.sidebar.error("Location not found. Using default coordinates.")
        lat, lon = 43.6245, -72.5187
except:
    st.sidebar.warning("Geocoding service timed out. Using default.")
    lat, lon = 43.6245, -72.5187

# --- DATA PROCESSING ---
astro = get_astronomy_data(lat, lon)
weather = get_weather(lat, lon)

# --- VISIBILITY LOGIC ---
is_clear = weather['clouds'] < 25 if weather else False
is_dark_enough = astro['is_dark']
is_core_up = astro['core_alt'] > 0
# Moon is favorable if it's below horizon OR if it's a very slim crescent
is_moon_ok = (not astro['moon_visible']) or (astro['moon_phase'] < 15)

# Calculate Final Score
if is_clear and is_dark_enough and is_core_up and is_moon_ok:
    st.balloons()
    st.success("### ✅ THE MILKY WAY IS VISIBLE!")
    st.write("Conditions are perfect. Grab your camera and head to a dark spot.")
else:
    st.error("### ❌ NOT VISIBLE RIGHT NOW")
    
# --- DASHBOARD METRICS ---
st.divider()
col1, col2, col3 = st.columns(3)
def get_forecast_data(lat, lon):
    if not WEATHER_API_KEY:
        return []
    
    # OpenWeatherMap 5-day/3-hour forecast URL
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=imperial"
    response = requests.get(url).json()
    
    forecast_list = []
    obs = ephem.Observer()
    obs.lat, obs.lon = str(lat), str(lon)

    # The Core coordinates
    ga_center = ephem.FixedBody()
    ga_center._ra = '17:45:40'
    ga_center._dec = '-29:00:28'

    for entry in response.get('list', []):
        dt = datetime.datetime.fromtimestamp(entry['dt'])
        obs.date = dt
        
        # Calculate Astro data for this future time
        sun = ephem.Sun(obs)
        ga_center.compute(obs)
        moon = ephem.Moon(obs)
        
        core_alt = ga_center.alt * 57.2958
        sun_alt = sun.alt * 57.2958
        clouds = entry['clouds']['all']
        
        # Logic: Dark + Core Up + Clear
        is_visible = sun_alt < -12 and core_alt > 0 and clouds < 30
        
        forecast_list.append({
            "time": dt.strftime("%a %I%p"),
            "clouds": clouds,
            "core_alt": core_alt,
            "visible": is_visible
        })
    return forecast_list
    st.header("📅 5-Day Visibility Roadmap")
forecast = get_forecast_data(lat, lon)

if forecast:
    # We only care about the windows where the Milky Way is technically "Up"
    cols = st.columns(len(forecast[:12])) # Show next 36 hours
    for i, day in enumerate(forecast[:12]):
        with cols[i]:
            st.caption(day['time'])
            if day['visible']:
                st.write("🌌 **YES**")
            else:
                st.write("☁️" if day['clouds'] > 30 else "🚫")
