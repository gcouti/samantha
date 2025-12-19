"""
Weather tool for fetching real weather information from internet APIs.
"""
import aiohttp
import os
import logging
from typing import Dict, Any, Optional
from .base_tool import BaseTool

logger = logging.getLogger(__name__)

class WeatherTool(BaseTool):
    """Tool for fetching real weather information from online APIs."""
    
    def __init__(self):
        super().__init__(
            name="weather_tool",
            description="Fetch real weather information from internet APIs"
        )
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
        # Fallback to free weather API if OpenWeather key not available
        self.weather_api_url = "https://api.weatherapi.com/v1"
        self.weather_api_key = os.getenv("WEATHERAPI_KEY")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch weather information for a given location.
        
        Args:
            parameters: Dict containing 'location' (city name) and optional 'units'
            
        Returns:
            Dict containing weather information and metadata
        """
        try:
            location = parameters.get("location", "")
            units = parameters.get("units", "metric")  # metric, imperial, kelvin
            
            if not location:
                return {
                    "success": False,
                    "error": "Location parameter is required",
                    "data": None
                }
            
            # Try different weather APIs in order of preference
            weather_data = await self._fetch_openweather(location, units)
            if not weather_data:
                weather_data = await self._fetch_weatherapi(location, units)
            
            if not weather_data:
                weather_data = await self._fetch_weather_gov(location)
            
            if weather_data:
                return {
                    "success": True,
                    "data": weather_data,
                    "location": location,
                    "units": units,
                    "source": weather_data.get("source", "unknown")
                }
            else:
                return {
                    "success": False,
                    "error": "Could not fetch weather data from any source",
                    "data": None
                }
                
        except Exception as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _fetch_openweather(self, location: str, units: str) -> Optional[Dict[str, Any]]:
        """Fetch weather from OpenWeatherMap API."""
        if not self.api_key:
            return None
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key,
                "units": units,
                "lang": "pt_br"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_openweather_data(data, units)
                    else:
                        logger.warning(f"OpenWeather API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching from OpenWeather: {str(e)}")
            return None
    
    async def _fetch_weatherapi(self, location: str, units: str) -> Optional[Dict[str, Any]]:
        """Fetch weather from WeatherAPI.com."""
        if not self.weather_api_key:
            return None
        
        try:
            url = f"{self.weather_api_url}/current.json"
            params = {
                "key": self.weather_api_key,
                "q": location,
                "lang": "pt",
                "aqi": "no"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_weatherapi_data(data, units)
                    else:
                        logger.warning(f"WeatherAPI error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching from WeatherAPI: {str(e)}")
            return None
    
    async def _fetch_weather_gov(self, location: str) -> Optional[Dict[str, Any]]:
        """Fetch weather from weather.gov (US only, free)."""
        try:
            # First get location coordinates
            geo_url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
            geo_params = {
                "address": location,
                "benchmark": "Public_AR_Current",
                "format": "json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(geo_url, params=geo_params) as response:
                    if response.status != 200:
                        return None
                    
                    geo_data = await response.json()
                    if not geo_data.get("result", {}).get("addressMatches"):
                        return None
                    
                    coords = geo_data["result"]["addressMatches"][0]["coordinates"]
                    lat, lon = coords["y"], coords["x"]
                    
                    # Get weather using coordinates
                    points_url = f"https://api.weather.gov/points/{lat},{lon}"
                    async with session.get(points_url) as points_response:
                        if points_response.status != 200:
                            return None
                        
                        points_data = await points_response.json()
                        forecast_url = points_data["properties"]["forecast"]
                        
                        async with session.get(forecast_url) as forecast_response:
                            if forecast_response.status != 200:
                                return None
                            
                            forecast_data = await forecast_response.json()
                            return self._format_weather_gov_data(forecast_data, location)
                            
        except Exception as e:
            logger.error(f"Error fetching from weather.gov: {str(e)}")
            return None
    
    def _format_openweather_data(self, data: Dict[str, Any], units: str) -> Dict[str, Any]:
        """Format OpenWeatherMap data."""
        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})
        
        return {
            "source": "openweathermap",
            "location": data.get("name", ""),
            "country": data.get("sys", {}).get("country", ""),
            "temperature": main.get("temp", 0),
            "feels_like": main.get("feels_like", 0),
            "humidity": main.get("humidity", 0),
            "pressure": main.get("pressure", 0),
            "description": weather.get("description", ""),
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "visibility": data.get("visibility", 0) / 1000,  # Convert to km
            "units": units
        }
    
    def _format_weatherapi_data(self, data: Dict[str, Any], units: str) -> Dict[str, Any]:
        """Format WeatherAPI.com data."""
        current = data.get("current", {})
        location = data.get("location", {})
        
        return {
            "source": "weatherapi",
            "location": location.get("name", ""),
            "country": location.get("country", ""),
            "temperature": current.get("temp_c" if units == "metric" else "temp_f", 0),
            "feels_like": current.get("feelslike_c" if units == "metric" else "feelslike_f", 0),
            "humidity": current.get("humidity", 0),
            "pressure": current.get("pressure_mb", 0),
            "description": current.get("condition", {}).get("text", ""),
            "wind_speed": current.get("wind_kph" if units == "metric" else "wind_mph", 0),
            "wind_direction": current.get("wind_degree", 0),
            "visibility": current.get("vis_km", 0),
            "units": units
        }
    
    def _format_weather_gov_data(self, data: Dict[str, Any], location: str) -> Dict[str, Any]:
        """Format weather.gov data."""
        periods = data.get("properties", {}).get("periods", [])
        if not periods:
            return None
        
        current = periods[0]  # Get current/next period
        
        return {
            "source": "weather.gov",
            "location": location,
            "country": "US",
            "temperature": current.get("temperature", 0),
            "feels_like": current.get("temperature", 0),  # Not provided by weather.gov
            "humidity": 0,  # Not provided in basic forecast
            "pressure": 0,  # Not provided in basic forecast
            "description": current.get("detailedForecast", current.get("shortForecast", "")),
            "wind_speed": current.get("windSpeed", "0"),
            "wind_direction": current.get("windDirection", "N"),
            "visibility": 0,  # Not provided in basic forecast
            "units": "metric" if current.get("temperatureUnit") == "C" else "imperial"
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema."""
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location (e.g., 'São Paulo', 'New York')"
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units: 'metric' (Celsius), 'imperial' (Fahrenheit), 'kelvin'",
                    "default": "metric",
                    "enum": ["metric", "imperial", "kelvin"]
                }
            },
            "required": ["location"]
        }
    
    async def get_weather_forecast(self, location: str, days: int = 5, units: str = "metric") -> Dict[str, Any]:
        """Get weather forecast for multiple days."""
        try:
            if not self.weather_api_key:
                return {
                    "success": False,
                    "error": "WeatherAPI key required for forecasts"
                }
            
            url = f"{self.weather_api_url}/forecast.json"
            params = {
                "key": self.weather_api_key,
                "q": location,
                "days": min(days, 10),  # API limit
                "lang": "pt",
                "aqi": "no"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        forecast_days = data.get("forecast", {}).get("forecastday", [])
                        
                        formatted_forecast = []
                        for day in forecast_days:
                            day_data = {
                                "date": day.get("date"),
                                "max_temp": day.get("day", {}).get("maxtemp_c" if units == "metric" else "maxtemp_f"),
                                "min_temp": day.get("day", {}).get("mintemp_c" if units == "metric" else "mintemp_f"),
                                "description": day.get("day", {}).get("condition", {}).get("text", ""),
                                "humidity": day.get("day", {}).get("avghumidity", 0),
                                "wind_speed": day.get("day", {}).get("maxwind_kph" if units == "metric" else "maxwind_mph", 0)
                            }
                            formatted_forecast.append(day_data)
                        
                        return {
                            "success": True,
                            "location": location,
                            "forecast": formatted_forecast,
                            "units": units,
                            "source": "weatherapi"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"WeatherAPI error: {response.status}"
                        }
                        
        except Exception as e:
            logger.error(f"Error fetching forecast: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
