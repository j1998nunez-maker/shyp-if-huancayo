from flask import Flask, jsonify, request
import requests
import math

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
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,soil_moisture_0_to_7cm"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data.get("current", {})
        temp = current.get("temperature_2m", 20.0)
        humidity = current.get("relative_humidity_2m", 50.0)
        wind_speed = current.get("wind_speed_10m", 10.0)
        wind_dir = current.get("wind_direction_10m", 0.0)
        soil_moisture = current.get("soil_moisture_0_to_7cm", 0.25)
        
        riesgo_termico = max(0.0, min(100.0, (temp / 35.0) * 40.0))
        riesgo_humedad = max(0.0, min(100.0, ((100.0 - humidity) / 100.0) * 40.0))
        riesgo_viento = max(0.0, min(100.0, (wind_speed / 40.0) * 20.0))
        
        ricia_total = round(riesgo_termico + riesgo_humedad + riesgo_viento, 2)
        
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
            "direccion_viento_grados": wind_dir,
            "humedad_suelo": soil_moisture,
            "indice_riesgo_icia": ricia_total,
            "nivel_alerta": nivel,
            "fuente": "Open-Meteo API"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/propagacion", methods=["POST"])
def calcular_cono_propagacion():
    # Recibe las coordenadas de un foco detectado y calcula hacia dónde avanza el fuego
    try:
        data = request.get_json() or {}
        foco_lat = data.get("lat", LAT)
        foco_lon = data.get("lon", LON)
        
        # Consultamos el viento actual para calcular el vector
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=wind_speed_10m,wind_direction_10m"
        resp = requests.get(url, timeout=10).json()
        current = resp.get("current", {})
        wind_speed = current.get("wind_speed_10m", 5.0)
        wind_dir = current.get("wind_direction_10m", 180.0) # Dirección de donde viene el viento
        
        # El fuego se propaga en la dirección HACIA DONDE VA el viento (dirección opuesta + 180°)
        direccion_fuego_grados = (wind_dir + 180) % 360
        
        # Estimación geométrica simple del cono de avance (alcance en 1 hora según velocidad del viento)
        # Factor de propagación adaptado a pajonal andino (ichu)
        distancia_estimada_km = round(wind_speed * 0.15, 2) 

        return jsonify({
            "foco_origen": {"lat": foco_lat, "lon": foco_lon},
            "viento_actual": {"velocidad_kmh": wind_speed, "origen_grados": wind_dir},
            "vector_avance": {
                "direccion_hacia_grados": direccion_fuego_grados,
                "alcance_estimado_1h_km": distancia_estimada_km,
                "comportamiento": "El fuego es impulsado rápidamente cuesta arriba por efecto de ladera y viento."
            },
            "recomendacion_operativa": "Desplegar brigada de intercepción en el sector proyectado antes de que el frente alcance la cresta."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)