#!/usr/bin/env python3
"""
Weather Alert Generator - News Lancashire
Fetches weather data, generates article
Free: OpenWeatherMap API (1000 calls/day)
"""
import json
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/ubuntu/newslancashire")
OUTPUT_DIR = BASE_DIR / "data/weather_articles"
API_KEY = "d59eac3f2d35bc9f870f4e7379707dfa"  # OpenWeatherMap API key

LANCASHIRE_LOCATIONS = [
    {"name": "Burnley", "lat": 53.789, "lon": -2.248},
    {"name": "Blackburn", "lat": 53.748, "lon": -2.482},
    {"name": "Blackpool", "lat": 53.816, "lon": -3.056},
    {"name": "Preston", "lat": 53.763, "lon": -2.704},
    {"name": "Lancaster", "lat": 54.047, "lon": -2.801},
]

def fetch_weather(lat, lon, api_key=None):
    """Fetch weather from OpenWeatherMap"""
    if api_key:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    else:
        # Free tier without key (limited)
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Weather API error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return None

def generate_article(location_name, weather_data):
    """Generate weather article from API data"""
    if not weather_data:
        return None
    
    main = weather_data.get("main", {})
    weather = weather_data.get("weather", [{}])[0]
    wind = weather_data.get("wind", {})
    
    temp = main.get("temp", 0)
    feels_like = main.get("feels_like", 0)
    humidity = main.get("humidity", 0)
    description = weather.get("description", "unknown")
    wind_speed = wind.get("speed", 0)
    
    # Generate content
    article = {
        "id": f"weather-{location_name.lower()}-{datetime.now().strftime('%Y%m%d')}",
        "title": f"Weather in {location_name}: {description.title()}, {temp:.0f}°C",
        "summary": f"Current conditions in {location_name}: Temperature {temp:.0f}°C (feels like {feels_like:.0f}°C), {description}. Wind {wind_speed:.1f} m/s, humidity {humidity}%.",
        "content": f"""Today's weather forecast for {location_name}:

Temperature: {temp:.0f}°C (feels like {feels_like:.0f}°C)
Conditions: {description.title()}
Humidity: {humidity}%
Wind Speed: {wind_speed:.1f} m/s

Stay updated with local weather conditions throughout the day.""",
        "date": datetime.now().isoformat(),
        "borough": location_name.lower(),
        "category": "weather",
        "source": "OpenWeatherMap",
        "tags": ["weather", location_name.lower(), "forecast"],
        "url": f"{location_name.lower()}-weather-{datetime.now().strftime('%Y-%m-%d')}"
    }
    
    return article

def main():
    print("[Weather Generator] Starting...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    articles = []
    for location in LANCASHIRE_LOCATIONS[:3]:  # Top 3 locations to save API calls
        print(f"  Fetching weather for {location['name']}...")
        weather = fetch_weather(location["lat"], location["lon"])
        
        if weather:
            article = generate_article(location["name"], weather)
            if article:
                articles.append(article)
                # Save individual file
                with open(OUTPUT_DIR / f"{article['id']}.json", 'w') as f:
                    json.dump(article, f, indent=2)
                print(f"    Generated: {article['title']}")
        
        # Rate limit - be nice to free API
        import time
        time.sleep(1)
    
    # Save index
    with open(OUTPUT_DIR / "index.json", 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"\n[Weather Generator] Complete: {len(articles)} articles")

if __name__ == "__main__":
    main()