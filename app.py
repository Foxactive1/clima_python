"""
Weather App – Flask Backend
InNovaIdeia | Dione Castro Alves

Dependências:
    pip install flask requests geopy timezonefinder pytz

⚠️  Coloque sua chave real da OpenWeatherMap em OWM_API_KEY
    (crie grátis em https://openweathermap.org/api)
"""

import os
import requests
import pytz
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

app = Flask(__name__)

# ── Coloque aqui sua API Key da OpenWeatherMap ──────────────────────────────
OWM_API_KEY = os.getenv("OWM_API_KEY", "SUA_CHAVE_AQUI")
OWM_URL     = "https://api.openweathermap.org/data/2.5/weather"

# Mapeamento de condição → ícone emoji + classe CSS de fundo
CONDITION_MAP = {
    "clear"         : ("☀️",  "bg-clear"),
    "clouds"        : ("☁️",  "bg-cloudy"),
    "rain"          : ("🌧️", "bg-rain"),
    "drizzle"       : ("🌦️", "bg-rain"),
    "thunderstorm"  : ("⛈️", "bg-storm"),
    "snow"          : ("❄️",  "bg-snow"),
    "mist"          : ("🌫️", "bg-mist"),
    "fog"           : ("🌫️", "bg-mist"),
    "haze"          : ("🌫️", "bg-mist"),
    "smoke"         : ("🌫️", "bg-mist"),
    "dust"          : ("🌫️", "bg-mist"),
    "sand"          : ("🌫️", "bg-mist"),
    "ash"           : ("🌫️", "bg-mist"),
    "squall"        : ("💨",  "bg-storm"),
    "tornado"       : ("🌪️", "bg-storm"),
}


@app.route("/")
def index():
    """Renderiza a página principal."""
    return render_template("index.html")


@app.route("/weather", methods=["POST"])
def get_weather():
    """
    Recebe { city: str } via JSON.
    Retorna dados completos do tempo em JSON.
    """
    data = request.get_json(force=True)
    city = (data.get("city") or "").strip()

    if not city:
        return jsonify({"error": "Informe o nome de uma cidade."}), 400

    # ── 1. Geocodificação ──────────────────────────────────────────────────
    try:
        geolocator = Nominatim(user_agent="innova_weather_app")
        location   = geolocator.geocode(city, language="pt")
        if not location:
            return jsonify({"error": f"Cidade '{city}' não encontrada."}), 404
    except Exception as e:
        return jsonify({"error": f"Erro na geocodificação: {str(e)}"}), 502

    # ── 2. Fuso horário local ──────────────────────────────────────────────
    try:
        tf          = TimezoneFinder()
        tz_name     = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        home_tz     = pytz.timezone(tz_name)
        local_time  = datetime.now(home_tz).strftime("%H:%M  |  %d/%m/%Y")
    except Exception:
        local_time  = datetime.utcnow().strftime("%H:%M UTC  |  %d/%m/%Y")

    # ── 3. OpenWeatherMap ──────────────────────────────────────────────────
    try:
        resp = requests.get(OWM_URL, params={
            "q"     : city,
            "appid" : OWM_API_KEY,
            "units" : "metric",   # já em Celsius
            "lang"  : "pt_br",
        }, timeout=8)
        resp.raise_for_status()
        jd = resp.json()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else 0
        msg = ("API Key inválida ou não autorizada." if status == 401
               else f"Erro HTTP {status} ao consultar clima.")
        return jsonify({"error": msg}), 502
    except requests.RequestException as e:
        return jsonify({"error": f"Falha de rede: {str(e)}"}), 502

    # ── 4. Parsear resposta ────────────────────────────────────────────────
    main      = jd.get("main", {})
    wind      = jd.get("wind", {})
    weather   = jd.get("weather", [{}])[0]
    sys_data  = jd.get("sys", {})

    condition_raw = weather.get("main", "").lower()
    icon_emoji, bg_class = CONDITION_MAP.get(condition_raw, ("🌡️", "bg-default"))

    # Nascer / pôr do sol
    def fmt_ts(ts):
        if not ts:
            return "--:--"
        return datetime.fromtimestamp(ts, tz=home_tz).strftime("%H:%M")

    payload = {
        "city"        : location.address.split(",")[0],
        "full_address": location.address,
        "local_time"  : local_time,
        "temp"        : round(main.get("temp", 0), 1),
        "feels_like"  : round(main.get("feels_like", 0), 1),
        "temp_min"    : round(main.get("temp_min", 0), 1),
        "temp_max"    : round(main.get("temp_max", 0), 1),
        "condition"   : weather.get("main", "—"),
        "description" : weather.get("description", "—").capitalize(),
        "wind"        : round(wind.get("speed", 0), 1),
        "wind_deg"    : wind.get("deg", 0),
        "humidity"    : main.get("humidity", 0),
        "pressure"    : main.get("pressure", 0),
        "visibility"  : round(jd.get("visibility", 0) / 1000, 1),
        "clouds"      : jd.get("clouds", {}).get("all", 0),
        "sunrise"     : fmt_ts(sys_data.get("sunrise")),
        "sunset"      : fmt_ts(sys_data.get("sunset")),
        "icon_emoji"  : icon_emoji,
        "bg_class"    : bg_class,
        "country"     : sys_data.get("country", ""),
        "lat"         : round(location.latitude,  4),
        "lon"         : round(location.longitude, 4),
    }
    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True)
