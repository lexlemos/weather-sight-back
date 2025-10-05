# app.py
from flask import Flask, request, jsonify
import requests
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)

# --- SOLUÇÃO SIMPLIFICADA E ROBUSTA ---
# Esta única linha é suficiente. 
# Ela diz ao Flask-CORS para permitir requisições da sua origem do frontend
# e para lidar automaticamente com as requisições OPTIONS.
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8081')
CORS(app, origins=frontend_url)
print("--- SUCESSO: A configuração do CORS foi aplicada ao app! ---")
# --- O resto do seu código permanece o mesmo ---
weather_cache = {}

def analyze_data(weather_data, target_date_str):
    # ... (sua função analyze_data sem alterações)
    # ... (cole sua função analyze_data aqui)
    THRESHOLDS = {"hot": 32.0, "cold": 10.0, "windy": 35.0, "rainy": 1.0}
    counters = {"matching_days": 0, "hot_days": 0, "cold_days": 0, "windy_days": 0, "rainy_days": 0, "any_rain_days": 0}
    daily_temps, daily_humidity, daily_wind_speeds = [], [], []
    yearly_data = {}
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    target_month, target_day = target_date.month, target_date.day
    daily_data = weather_data['daily']
    time_list, temp_max_list, temp_min_list, wind_max_list, precipitation_list, humidity_list = (
        daily_data['time'], daily_data['temperature_2m_max'], daily_data['temperature_2m_min'],
        daily_data['wind_speed_10m_max'], daily_data['precipitation_sum'], daily_data['relative_humidity_2m_mean']
    )
    for i, date_entry in enumerate(time_list):
        historical_date = datetime.strptime(date_entry, '%Y-%m-%d')
        if historical_date.month == target_month and historical_date.day == target_day:
            counters["matching_days"] += 1
            avg_day_temp = None
            if temp_max_list[i] is not None and temp_min_list[i] is not None:
                avg_day_temp = (temp_max_list[i] + temp_min_list[i]) / 2
                daily_temps.append(avg_day_temp)
            if humidity_list[i] is not None: daily_humidity.append(humidity_list[i])
            if wind_max_list[i] is not None: daily_wind_speeds.append(wind_max_list[i])
            if temp_max_list[i] is not None and temp_max_list[i] > THRESHOLDS["hot"]: counters["hot_days"] += 1
            if temp_min_list[i] is not None and temp_min_list[i] < THRESHOLDS["cold"]: counters["cold_days"] += 1
            if wind_max_list[i] is not None and wind_max_list[i] > THRESHOLDS["windy"]: counters["windy_days"] += 1
            if precipitation_list[i] is not None and precipitation_list[i] >= THRESHOLDS["rainy"]: counters["rainy_days"] += 1
            if precipitation_list[i] is not None and precipitation_list[i] > 0.0: counters["any_rain_days"] += 1
            current_year = historical_date.year
            yearly_data[current_year] = {
                "temperature": round(avg_day_temp, 1) if avg_day_temp is not None else None,
                "humidity": humidity_list[i],
                "wind_speed": wind_max_list[i],
                "rain_chance_percent": 100 if precipitation_list[i] is not None and precipitation_list[i] > 0.0 else 0
            }
    if counters["matching_days"] == 0: return {"error": "No historical data found for this date."}
    def calculate_average(data_list): return round(sum(data_list) / len(data_list), 1) if data_list else 0
    results = {
        "average_temperature_celsius": calculate_average(daily_temps),
        "average_humidity_percent": calculate_average(daily_humidity),
        "average_wind_speed_kmh": calculate_average(daily_wind_speeds),
        "chance_of_any_rain_percent": round((counters["any_rain_days"] / counters["matching_days"]) * 100),
        "analysis_based_on_years": counters["matching_days"]
    }
    sorted_years = sorted(yearly_data.keys(), reverse=True)[:10]
    results["historical_trends"] = {
        "years": sorted_years,
        "temperatures": [yearly_data[year]["temperature"] for year in sorted_years],
        "humidities": [yearly_data[year]["humidity"] for year in sorted_years],
        "wind_speeds": [yearly_data[year]["wind_speed"] for year in sorted_years],
        "rain_chances_percent": [yearly_data[year]["rain_chance_percent"] for year in sorted_years]
    }
    return results

def get_nasa_image_url(latitude, longitude, date_str):
    # ... (sua função get_nasa_image_url sem alterações)
    # ... (cole sua função get_nasa_image_url aqui)
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        last_year = datetime.now().year - 1
        historical_date = target_date.replace(year=last_year)
        formatted_date = historical_date.strftime('%Y-%m-%d')
        lon_min, lon_max, lat_min, lat_max = longitude - 0.25, longitude + 0.25, latitude - 0.25, latitude + 0.25
        bbox = f"{lon_min},{lat_min},{lon_max},{lat_max}"
        base_url = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/"
        return f"{base_url}{formatted_date}/250m/{bbox}?format=image/jpeg"
    except Exception as e:
        print(f"Error generating NASA image URL: {e}")
        return None

def get_historical_weather(location_name):
    # ... (sua função get_historical_weather sem alterações)
    # ... (cole sua função get_historical_weather aqui)
    if location_name in weather_cache:
        print(f"CACHE HIT: Found data for '{location_name}' in cache.")
        cached_data = weather_cache[location_name]
        return cached_data['weather_data'], cached_data['lat'], cached_data['lon'], None
    print(f"CACHE MISS: Fetching new data for '{location_name}' from API.")
    try:
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": location_name, "count": 1, "language": "en", "format": "json"}
        geo_response = requests.get(geocoding_url, params=geo_params, timeout=30)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        if not geo_data.get("results"): return None, None, None, f"Could not find coordinates for '{location_name}'"
        result = geo_data["results"][0]
        latitude, longitude = result["latitude"], result["longitude"]
        historical_api_url = "https://archive-api.open-meteo.com/v1/archive"
        end_year = datetime.now().year - 1
        start_year = end_year - 20 
        daily_params = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,relative_humidity_2m_mean"
        params = {"latitude": latitude, "longitude": longitude, "start_date": f"{start_year}-01-01", "end_date": f"{end_year}-12-31", "daily": daily_params, "timezone": "auto"}
        response = requests.get(historical_api_url, params=params, timeout=30)
        response.raise_for_status()
        weather_data = response.json()
        weather_cache[location_name] = {
            "weather_data": weather_data,
            "lat": latitude,
            "lon": longitude
        }
        return weather_data, latitude, longitude, None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            error_msg = "API rate limit exceeded. Please wait a minute and try again."
            print(f"ERROR: {error_msg}")
            return None, None, None, error_msg
        error_msg = f"HTTP Error fetching data: {e}"
        print(f"ERROR: {error_msg}")
        return None, None, None, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error fetching data: {e}"
        print(f"ERROR: {error_msg}")
        return None, None, None, error_msg


# --- ROTA CORRIGIDA ---
# Remova 'OPTIONS' daqui. Flask-CORS vai cuidar disso.
@app.route('/analyze', methods=['POST'])
def analyze_weather():
    # Agora esta linha é segura, pois a rota só aceita POST
    data = request.get_json()
    location = data.get('location')
    date_str = data.get('date')

    if not location or not date_str:
        return jsonify({"error": "Location and date are required"}), 400

    weather_data, lat, lon, error_message = get_historical_weather(location)
    
    if error_message:
        status_code = 503 if "rate limit" in error_message else 500
        return jsonify({"error": error_message}), status_code
    
    analysis_results = analyze_data(weather_data, date_str)
    nasa_image_url = get_nasa_image_url(lat, lon, date_str)

    final_response = {
        "location": location,
        "requested_date": date_str,
        "weather_analysis": analysis_results,
        "nasa_satellite_view_url": nasa_image_url
    }
    
    return jsonify(final_response)

if __name__ == '__main__':
    app.run(debug=True)