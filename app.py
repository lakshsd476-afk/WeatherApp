import streamlit as st
import requests
from datetime import datetime


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Weather App",
    page_icon="🌤️",
    layout="centered"
)


# =========================================================
# LOAD CSS
# =========================================================

def load_css():
    try:
        with open("assets/style.css", "r", encoding="utf-8") as f:
            st.html(f"<style>{f.read()}</style>")
    except FileNotFoundError:
        pass


load_css()


# =========================================================
# WEATHER CODE → DESCRIPTION + ICON
# =========================================================

def get_weather_description(code):

    weather_codes = {
        0: ("Clear Sky", "☀️"),
        1: ("Mainly Clear", "🌤️"),
        2: ("Partly Cloudy", "⛅"),
        3: ("Overcast", "☁️"),

        45: ("Fog", "🌫️"),
        48: ("Rime Fog", "🌫️"),

        51: ("Light Drizzle", "🌦️"),
        53: ("Moderate Drizzle", "🌦️"),
        55: ("Dense Drizzle", "🌧️"),

        61: ("Slight Rain", "🌦️"),
        63: ("Moderate Rain", "🌧️"),
        65: ("Heavy Rain", "🌧️"),

        71: ("Slight Snow", "🌨️"),
        73: ("Moderate Snow", "🌨️"),
        75: ("Heavy Snow", "❄️"),

        80: ("Rain Showers", "🌦️"),
        81: ("Moderate Rain Showers", "🌧️"),
        82: ("Heavy Rain Showers", "⛈️"),

        95: ("Thunderstorm", "⛈️"),
        96: ("Thunderstorm with Hail", "⛈️"),
        99: ("Heavy Thunderstorm with Hail", "⛈️")
    }

    return weather_codes.get(
        code,
        ("Unknown Weather", "🌍")
    )


# =========================================================
# GET LOCATION
# =========================================================

@st.cache_data(ttl=86400)
def get_coordinates(city):

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city,
        "count": 10,
        "language": "en",
        "format": "json",

        # IMPORTANT:
        # Search specifically within India
        "countryCode": "IN"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

    except requests.RequestException:
        return None

    if "results" not in data:
        return None

    if len(data["results"]) == 0:
        return None

    # Pick the most populated / prominent result
    results = sorted(
        data["results"],
        key=lambda x: x.get("population", 0),
        reverse=True
    )

    location = results[0]

    return {
        "name": location.get("name"),
        "country": location.get("country"),
        "country_code": location.get("country_code"),
        "state": location.get("admin1"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude")
    }


# =========================================================
# GET WEATHER
# =========================================================

@st.cache_data(ttl=1800)
def get_weather(latitude, longitude):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "weather_code,"
            "wind_speed_10m,"
            "is_day"
        ),

        "daily": (
            "weather_code,"
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_probability_max"
        ),

        "timezone": "auto",
        "forecast_days": 7
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        # THIS IS IMPORTANT
        # If Open-Meteo rejects the request,
        # show us exactly why.
        if response.status_code != 200:

            st.error(
                f"Weather API error: "
                f"{response.status_code}"
            )

            st.code(response.text)

            return None

        data = response.json()

        # Check whether API returned an error
        if data.get("error"):

            st.error(
                data.get(
                    "reason",
                    "Unknown Open-Meteo error"
                )
            )

            return None

        return data

    except requests.exceptions.Timeout:

        st.error(
            "The weather service took too long to respond."
        )

        return None

    except requests.exceptions.ConnectionError:

        st.error(
            "Could not connect to the weather service."
        )

        return None

    except requests.exceptions.RequestException as e:

        st.error(
            f"Request failed: {e}"
        )

        return None

    except ValueError:

        st.error(
            "The weather service returned invalid data."
        )

        return None


# =========================================================
# SEARCH
# =========================================================

city = st.text_input(
    "🔎 Search for a city",
    placeholder="Try Bangalore, Mumbai, Chennai, Hyderabad..."
)


search_button = st.button(
    "Get Weather",
    use_container_width=True
)


# =========================================================
# MAIN LOGIC
# =========================================================

if search_button:

    if not city.strip():

        st.warning("Please enter a city name.")

    else:

        # -----------------------------------------
        # LOCATION
        # -----------------------------------------

        with st.spinner("Finding your city..."):

            location = get_coordinates(
                city.strip()
            )

        if location is None:

            st.error(
                f"Couldn't find '{city}' in India. "
                "Try checking the spelling."
            )

        else:

            # -----------------------------------------
            # WEATHER
            # -----------------------------------------

            with st.spinner("Getting weather information..."):

                weather = get_weather(
                    location["latitude"],
                    location["longitude"]
                )

            if weather is None:

                st.error(
                    "Unable to retrieve weather data right now."
                )

            else:

                current = weather["current"]

                weather_name, weather_icon = (
                    get_weather_description(
                        current["weather_code"]
                    )
                )

                # -----------------------------------------
                # LOCATION
                # -----------------------------------------

                state_text = ""

                if location["state"]:
                    state_text = f', {location["state"]}'

                st.markdown(
                    f"""
                    <div class="location">
                        📍 {location["name"]}{state_text},
                        {location["country"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # -----------------------------------------
                # WEATHER CARD
                # -----------------------------------------

                weather_card = f"""
                <div class="weather-card">

                    <div class="weather-icon">
                        {weather_icon}
                    </div>

                    <div class="temperature">
                        {current["temperature_2m"]}°C
                    </div>

                    <div class="weather-description">
                        {weather_name}
                    </div>

                    <div class="feels-like">
                        Feels like {current["apparent_temperature"]}°C
                    </div>

                </div>
                """

                st.html(weather_card)

                # -----------------------------------------
                # WEATHER DETAILS
                # -----------------------------------------

                st.subheader("Current Conditions")

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "💧 Humidity",
                        f'{current["relative_humidity_2m"]}%'
                    )

                with col2:

                    st.metric(
                        "💨 Wind",
                        f'{current["wind_speed_10m"]} km/h'
                    )

                with col3:

                    st.metric(
                        "🌧️ Precipitation",
                        f'{current["precipitation"]} mm'
                    )

                # -----------------------------------------
                # 7 DAY FORECAST
                # -----------------------------------------

                st.subheader("📅 7-Day Forecast")

                daily = weather["daily"]

                for i in range(7):

                    date = datetime.strptime(
                        daily["time"][i],
                        "%Y-%m-%d"
                    )

                    day_name = date.strftime("%A")

                    forecast_name, forecast_icon = (
                        get_weather_description(
                            daily["weather_code"][i]
                        )
                    )

                    max_temp = daily[
                        "temperature_2m_max"
                    ][i]

                    min_temp = daily[
                        "temperature_2m_min"
                    ][i]

                    rain_probability = daily[
                        "precipitation_probability_max"
                    ][i]

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.write(
                            f"**{day_name}**"
                        )

                    with col2:
                        st.write(
                            f"{forecast_icon} {forecast_name}"
                        )

                    with col3:
                        st.write(
                            f"🌡️ {max_temp}°C / {min_temp}°C"
                        )

                    with col4:
                        st.write(
                            f"🌧️ {rain_probability}%"
                        )

                    st.divider()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        Built with Python + Streamlit + Open-Meteo
    </div>
    """,
    unsafe_allow_html=True
)