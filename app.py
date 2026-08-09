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
# GET CITY COORDINATES
#
# Cached for 24 hours.
# Same city won't repeatedly hit the geocoding API.
# =========================================================

@st.cache_data(
    ttl=86400,
    max_entries=500
)
def get_coordinates(city):

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": city,
        "count": 10,
        "language": "en",
        "format": "json",
        "countryCode": "IN"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        if response.status_code == 429:
            return {
                "error": "rate_limit"
            }

        response.raise_for_status()

        data = response.json()

    except requests.exceptions.Timeout:

        return {
            "error": "timeout"
        }

    except requests.exceptions.ConnectionError:

        return {
            "error": "connection"
        }

    except requests.exceptions.RequestException:

        return {
            "error": "request"
        }

    if "results" not in data:
        return None

    if len(data["results"]) == 0:
        return None

    # Prefer the most populated/prominent location
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
# GET WEATHER DATA
#
# Cached for 30 minutes.
# This dramatically reduces repeated API calls.
# =========================================================

@st.cache_data(
    ttl=1800,
    max_entries=200
)
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

        # ---------------------------------------------
        # RATE LIMIT
        # ---------------------------------------------

        if response.status_code == 429:

            return {
                "error": "rate_limit"
            }

        # ---------------------------------------------
        # OTHER API ERROR
        # ---------------------------------------------

        if response.status_code != 200:

            return {
                "error": "api",
                "status": response.status_code,
                "message": response.text
            }

        data = response.json()

        # ---------------------------------------------
        # OPEN-METEO ERROR
        # ---------------------------------------------

        if data.get("error"):

            return {
                "error": "api",
                "message": data.get(
                    "reason",
                    "Unknown weather API error"
                )
            }

        return {
            "success": True,
            "data": data,
            "updated_at": datetime.now().strftime(
                "%d %b %Y, %I:%M %p"
            )
        }

    except requests.exceptions.Timeout:

        return {
            "error": "timeout"
        }

    except requests.exceptions.ConnectionError:

        return {
            "error": "connection"
        }

    except requests.exceptions.RequestException:

        return {
            "error": "request"
        }

    except ValueError:

        return {
            "error": "invalid_data"
        }


# =========================================================
# HEADER
# =========================================================

st.title("🌤️ Weather App")

st.markdown(
    """
    <div class="subtitle">
        Get current weather and a 7-day forecast for cities in India.
    </div>
    """,
    unsafe_allow_html=True
)


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
# WEATHER PROCESSING
# =========================================================

if search_button:

    if not city.strip():

        st.warning("Please enter a city name.")

    else:

        # =============================================
        # FIND CITY
        # =============================================

        with st.spinner("Finding your city..."):

            location = get_coordinates(
                city.strip().lower()
            )

        # ---------------------------------------------
        # LOCATION RATE LIMIT
        # ---------------------------------------------

        if location and location.get("error") == "rate_limit":

            st.warning(
                "🌐 The location service is temporarily "
                "rate-limited. Please try again later."
            )

        elif location is None:

            st.error(
                f"Couldn't find '{city}' in India. "
                "Please check the spelling."
            )

        elif location.get("error"):

            st.error(
                "Unable to connect to the location service."
            )

        else:

            # =============================================
            # GET WEATHER
            # =============================================

            with st.spinner("Getting weather information..."):

                weather_result = get_weather(
                    location["latitude"],
                    location["longitude"]
                )

            # =============================================
            # WEATHER RATE LIMIT
            # =============================================

            if (
                weather_result
                and weather_result.get("error")
                == "rate_limit"
            ):

                st.warning(
                    """
                    🌐 **Weather service rate limit reached.**

                    Open-Meteo has temporarily stopped new
                    requests. This is a limit from the weather
                    service, not an error with your app.

                    Please try again later.
                    """
                )

            # =============================================
            # TIMEOUT
            # =============================================

            elif (
                weather_result
                and weather_result.get("error")
                == "timeout"
            ):

                st.error(
                    "⏱️ The weather service took too long "
                    "to respond. Please try again."
                )

            # =============================================
            # CONNECTION ERROR
            # =============================================

            elif (
                weather_result
                and weather_result.get("error")
                == "connection"
            ):

                st.error(
                    "🌐 Could not connect to the weather "
                    "service. Please try again."
                )

            # =============================================
            # OTHER REQUEST ERROR
            # =============================================

            elif (
                weather_result
                and weather_result.get("error")
                == "request"
            ):

                st.error(
                    "⚠️ The weather request failed. "
                    "Please try again later."
                )

            # =============================================
            # API ERROR
            # =============================================

            elif (
                weather_result
                and weather_result.get("error")
                == "api"
            ):

                st.error(
                    "⚠️ Weather service returned an error."
                )

            # =============================================
            # INVALID DATA
            # =============================================

            elif (
                weather_result
                and weather_result.get("error")
                == "invalid_data"
            ):

                st.error(
                    "⚠️ The weather service returned "
                    "unexpected data."
                )

            # =============================================
            # NO RESPONSE
            # =============================================

            elif weather_result is None:

                st.error(
                    "Unable to retrieve weather data right now."
                )

            # =============================================
            # SUCCESS
            # =============================================

            else:

                weather = weather_result["data"]

                current = weather["current"]

                weather_name, weather_icon = (
                    get_weather_description(
                        current["weather_code"]
                    )
                )

                # =========================================
                # LOCATION
                # =========================================

                state_text = ""

                if location.get("state"):
                    state_text = (
                        f', {location["state"]}'
                    )

                st.markdown(
                    f"""
                    <div class="location">
                        📍 {location["name"]}
                        {state_text},
                        {location["country"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # =========================================
                # WEATHER CARD
                # =========================================

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
                        Feels like
                        {current["apparent_temperature"]}°C
                    </div>

                </div>
                """

                st.html(weather_card)

                # =========================================
                # CURRENT CONDITIONS
                # =========================================

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

                # =========================================
                # LAST UPDATED
                # =========================================

                st.caption(
                    f'🕒 Data fetched: '
                    f'{weather_result["updated_at"]}'
                )

                # =========================================
                # 7 DAY FORECAST
                # =========================================

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
                            f"{forecast_icon} "
                            f"{forecast_name}"
                        )

                    with col3:
                        st.write(
                            f"🌡️ {max_temp}°C / "
                            f"{min_temp}°C"
                        )

                    with col4:
                        st.write(
                            f"🌧️ "
                            f"{rain_probability}%"
                        )

                    st.divider()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">

        Built with Python + Streamlit

        <br>

        Weather data provided by
        <a href="https://open-meteo.com/"
           target="_blank">
            Open-Meteo
        </a>

        <br>

        Data licensed under CC BY 4.0

    </div>
    """,
    unsafe_allow_html=True
)