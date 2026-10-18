from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Coordenadas piloto para Huancayo, Junín
LAT = -12.0464
LON = -75.2049

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "online",
        "system": "SHYp-IF (Sistema Híbrido Predictivo de Incendios Forestales)",
        "location": "Huancayo, Perú"
    })

@app.route("/api/riesgo", methods=["GET"])
def obtener_riesgo_incendio():
    try:
        # Consulta gratuita a Open-Meteo (Variables meteorológicas clave para incendios)
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,soil_moisture_0_to_7cm"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        temp = current.get("temperature_2m", 20.0)
        humidity = current.get("relative_humidity_2m", 50.0)
        wind_speed = current.get("wind_speed_10m", 10.0)
        soil_moisture = current.get("soil_moisture_0_to_7cm", 0.25)
        
        # Algoritmo simplificado de Riesgo de Ignición (ICIA) de 0 a 100%
        # A menor humedad, mayor temperatura y menor humedad en suelo, mayor el riesgo
        riesgo_termico = max(0.0, min(100.0, (temp / 35.0) * 40.0))
        riesgo_humedad = max(0.0, min(100.0, ((100.0 - humidity) / 100.0) * 40.0))
        riesgo_viento = max(0.0, min(100.0, (wind_speed / 40.0) * 20.0))
        
        ricia_total = round(riesgo_termico + riesgo_humedad + riesgo_viento, 2)
        
        # Determinación de estado de alerta
        if ricia_total >= 70:
            nivel = "CRÍTICO (ALTO RIESGO DE IGNICIÓN)"
        elif ricia_total >= 40:
            nivel = "ALERTA MODERADA"
        else:
            nivel = "CONDICIONES SEGURAS"

        return jsonify({
            "ubicacion": "Huancayo - Valle del Mantaro",
            "temperatura_c": temp,
            "humedad_relativa_pct": humidity,
            "velocidad_viento_kmh": wind_speed,
            "humedad_suelo": soil_moisture,
            "indice_riesgo_icia": ricia_total,
            "nivel_alerta": nivel,
            "fuente": "Open-Meteo API (Cero costo de almacenamiento local)"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)