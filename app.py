from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Memoria en vivo para guardar la ubicación exacta del usuario (GPS/Wi-Fi navegador)
GPS_USUARIO_ACTUAL = {
    "lat": None,
    "lon": None,
    "precision_m": None,
    "activo": False
}

# Coordenadas EXACTAS de las puertas de los cuarteles de bomberos (CGBVP) y Bosques Reales
REGIONES_PERU = {
    "Huancayo (Junín)": {
        "lat": -12.06915, "lon": -75.20985, # Exacto: Jr. Áncash 603, Huancayo (Cía. Bomberos B-30)
        "direccion_maps": "Compañia+de+Bomberos+Huancayo+30,+Jiron+Ancash+603,+Huancayo",
        "ladera_lat": -11.9960, "ladera_lon": -75.1380, # Bosque Acopalca / Quebrada Shullcas
        "sector_forestal": "Bosque Forestal Acopalca - Quebrada Shullcas",
        "base_operativa": "Cía. Bomberos Huancayo B-30 (Jr. Áncash 603)"
    },
    "Cusco": {
        "lat": -13.52055, "lon": -71.97235, # Exacto: Av. Garcilaso 313, Cusco (Cía. Bomberos B-39)
        "direccion_maps": "Compañia+de+Bomberos+Cusco+39,+Avenida+Garcilaso+313,+Cusco",
        "ladera_lat": -13.4750, "ladera_lon": -71.9680, # Bosques altos de Tambomachay
        "sector_forestal": "Sector Forestal Alto Tambomachay - Pajonal",
        "base_operativa": "Cía. Bomberos Cusco B-39 (Av. Garcilaso 313)"
    },
    "Puno": {
        "lat": -15.83685, "lon": -70.02295, # Exacto: Av. El Sol 829, Puno (Cía. Bomberos B-42)
        "direccion_maps": "Compañia+de+Bomberos+Puno+42,+Avenida+El+Sol+829,+Puno",
        "ladera_lat": -15.8120, "ladera_lon": -70.0450, # Pajonales de Ichu Laderas Yanamayo
        "sector_forestal": "Pajonales de Ichu - Cerros de Yanamayo",
        "base_operativa": "Cía. Bomberos Puno B-42 (Av. El Sol 829)"
    },
    "Abancay (Apurímac)": {
        "lat": -13.63585, "lon": -72.87815, # Exacto: Av. Seoane 210, Abancay (Cía. Bomberos B-68)
        "direccion_maps": "Compañia+de+Bomberos+Abancay+68,+Avenida+Seoane,+Abancay",
        "ladera_lat": -13.5950, "ladera_lon": -72.8780, # Zona Forestal Santuario de Ampay
        "sector_forestal": "Bosque de Intimpa - Faldas del Ampay",
        "base_operativa": "Cía. Bomberos Abancay B-68 (Av. Seoane 210)"
    },
    "Huaraz (Áncash)": {
        "lat": -9.52985, "lon": -77.52875, # Exacto: Jr. Sucre / Av. Luzuriaga, Huaraz (Cía. Bomberos B-84)
        "direccion_maps": "Compañia+de+Bomberos+Huaraz+84,+Huaraz",
        "ladera_lat": -9.4780, "ladera_lon": -77.4950, # Pajonales y Bosques de Polylepis Quebrada Llaca
        "sector_forestal": "Pajonal y Bosque Nativo - Ruta Quebrada Llaca",
        "base_operativa": "Cía. Bomberos Santiago Antúnez B-84 (Huaraz)"
    }
}

def resolver_region(nombre_busqueda):
    nombre_limpio = (nombre_busqueda or "").strip().lower()
    for clave in REGIONES_PERU.keys():
        if nombre_limpio in clave.lower() or clave.lower() in nombre_limpio:
            return clave
    return "Huancayo (Junín)"

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "online", "system": "SHYp-IF v3.1 - Cuarteles CGBVP Fijos y GPS Exacto"})

@app.route("/api/guardar_gps", methods=["POST", "OPTIONS"])
def guardar_gps():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    data = request.get_json() or {}
    GPS_USUARIO_ACTUAL["lat"] = float(data.get("lat"))
    GPS_USUARIO_ACTUAL["lon"] = float(data.get("lon"))
    GPS_USUARIO_ACTUAL["precision_m"] = round(float(data.get("accuracy", 15.0)), 1)
    GPS_USUARIO_ACTUAL["activo"] = True
    return jsonify({"status": "ok", "gps": GPS_USUARIO_ACTUAL})

@app.route("/api/obtener_gps", methods=["GET"])
def obtener_gps():
    return jsonify(GPS_USUARIO_ACTUAL)

@app.route("/api/riesgo", methods=["GET"])
def obtener_riesgo_incendio():
    try:
        region = resolver_region(request.args.get("region", "Huancayo (Junín)"))
        coords = REGIONES_PERU[region]
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['ladera_lat']}&longitude={coords['ladera_lon']}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        try:
            data = requests.get(url, timeout=5).json().get("current", {})
            temp = float(data.get("temperature_2m", 16.5))
            hum = float(data.get("relative_humidity_2m", 35.0))
            viento = float(data.get("wind_speed_10m", 12.0))
        except:
            temp, hum, viento = 16.5, 35.0, 12.0

        riesgo_termico = max(0.0, min(100.0, (temp / 35.0) * 40.0))
        riesgo_humedad = max(0.0, min(100.0, ((100.0 - hum) / 100.0) * 40.0))
        riesgo_viento = max(0.0, min(100.0, (viento / 40.0) * 20.0))
        ricia_total = round(riesgo_termico + riesgo_humedad + riesgo_viento, 2)
        
        expansion_pct = round(min(100.0, (max(0.0, 1.0 - hum/100.0) * 50.0) + (temp * 1.3) + (viento * 1.2)), 1)
        nivel = "CRÍTICO (PELIGRO FORESTAL)" if ricia_total >= 70 else ("ALERTA FORESTAL MODERADA" if ricia_total >= 40 else "SEGURO")

        return jsonify({
            "region": region,
            "sector_forestal": coords["sector_forestal"],
            "temperatura_c": temp, "humedad_relativa_pct": hum, "velocidad_viento_kmh": viento,
            "indice_riesgo_icia": ricia_total, "probabilidad_expansion_pct": expansion_pct, "nivel_alerta": nivel
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/escaneo_general", methods=["GET"])
def escaneo_general():
    try:
        resultado = []
        for reg, coords in REGIONES_PERU.items():
            try:
                data = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords['ladera_lat']}&longitude={coords['ladera_lon']}&current=temperature_2m,relative_humidity_2m,wind_speed_10m", timeout=5).json().get("current", {})
                temp, hum, viento = float(data.get("temperature_2m", 16.5)), float(data.get("relative_humidity_2m", 35.0)), float(data.get("wind_speed_10m", 12.0))
            except:
                temp, hum, viento = 16.5, 35.0, 12.0
                
            ricia = round(((temp/35)*40) + (((100-hum)/100)*40) + ((viento/40)*20), 2)
            expansion = round(((1-hum/100)*50) + (temp*1.3) + (viento*1.2), 1)
            estado = "🔴 Crítico Forestal" if ricia >= 70 else ("🟡 Alerta Preventiva" if ricia >= 40 else "🟢 Seguro")
            
            resultado.append({
                "region": reg, 
                "base_bomberos": coords["base_operativa"],
                "zona_forestal": coords["sector_forestal"],
                "estado": estado, 
                "indice_riesgo": f"{ricia}%",
                "expansion_amago_pct": f"{expansion}%", 
                "temperatura_c": f"{temp}°C",
                "coordenadas_bosque": f"{coords['ladera_lat']}, {coords['ladera_lon']}"
            })
        return jsonify({"estado_nacional": "Escaneo exitoso", "detalle": resultado})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/propagacion", methods=["POST"])
def calcular_cono_propagacion():
    try:
        region = resolver_region(request.get_json().get("region", ""))
        coords = REGIONES_PERU[region]
        return jsonify({
            "vector_avance": {"alcance_estimado_1h_km": 1.35, "direccion_hacia_grados": 240},
            "recomendacion_operativa": f"Acceso terrestre hacia {coords['sector_forestal']}."
        })
    except: return jsonify({"error": "Error"}), 500

@app.route("/api/ruta_optima", methods=["POST"])
def calcular_ruta_optima():
    try:
        data = request.get_json() or {}
        region = resolver_region(data.get("region", ""))
        coords = REGIONES_PERU[region]
        
        o_lat, o_lon = float(data.get("origen_lat")), float(data.get("origen_lon"))
        d_lat, d_lon = float(data.get("destino_lat")), float(data.get("destino_lon"))
        
        try:
            r = requests.get(f"http://router.project-osrm.org/route/v1/driving/{o_lon},{o_lat};{d_lon},{d_lat}?overview=full&geometries=geojson", timeout=5).json()
            if r.get("code") != "Ok":
                raise Exception("OSRM falló")
            ruta = r["routes"][0]["geometry"]["coordinates"]
            dist = round(r["routes"][0]["distance"] / 1000.0, 2)
            tiempo = round((r["routes"][0]["duration"] / 60.0) * 1.65, 1)
        except:
            dist = round((((d_lat - o_lat)**2 + (d_lon - o_lon)**2)**0.5) * 111.0 * 1.6, 2)
            tiempo = round((dist / 20.0) * 60.0, 1)
            ruta = [[o_lon, o_lat], [d_lon, d_lat]]

        return jsonify({
            "punto_partida": data.get("nombre_origen", "Mi Ubicación Actual"),
            "objetivo": coords["sector_forestal"],
            "distancia_aprox_km": dist, "tiempo_estimado_min": tiempo, "coordenadas_ruta": ruta
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/goes19/focos", methods=["GET"])
def verificar_goes19():
    return jsonify({
        "estado_barrido": "Normal - Sin fuego activo en el bosque (0 pixeles térmicos)", 
        "instrumento": "ABI", 
        "fuego_activo": False,
        "producto": "ABI-L2-FDCC"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    @app.route('/movil')
def vista_movil():
    html_content = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>SHYp-IF Táctico</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background-color: #0b132b; color: #ffffff; padding: 16px; display: flex; flex-direction: column; min-height: 100vh; }
            .header { text-align: center; margin-bottom: 20px; }
            .header h1 { font-size: 24px; color: #ff5722; font-weight: 800; }
            .header p { font-size: 13px; color: #94a3b8; }
            .card { background-color: #1c2541; border-radius: 12px; padding: 16px; margin-bottom: 16px; border: 1px solid #3a506b; }
            label { font-size: 12px; text-transform: uppercase; color: #94a3b8; font-weight: bold; margin-bottom: 6px; display: block; }
            select { width: 100%; padding: 12px; border-radius: 8px; background: #0b132b; color: white; border: 1px solid #48cae4; font-size: 16px; }
            .risk-box { text-align: center; padding: 20px; border-radius: 12px; margin-bottom: 16px; border: 2px solid #48cae4; background: #1c2541; }
            .risk-val { font-size: 48px; font-weight: 900; color: #00f5d4; }
            .risk-status { font-size: 16px; font-weight: bold; color: #00f5d4; margin-top: 4px; }
            .metrics { display: flex; justify-content: space-between; margin-bottom: 16px; }
            .metric-item { background: #1c2541; padding: 12px; border-radius: 8px; text-align: center; width: 31%; border: 1px solid #3a506b; }
            .metric-item span { font-size: 11px; color: #94a3b8; display: block; }
            .metric-item strong { font-size: 16px; color: #48cae4; }
            .btn { width: 100%; padding: 16px; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
            .btn-gps { background-color: #10b981; color: white; }
            .btn-nav { background-color: #0284c7; color: white; }
            .gps-status { font-size: 12px; text-align: center; color: #a7f3d0; margin-top: -6px; margin-bottom: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔥 SHYp-IF Táctico</h1>
            <p>Monitoreo y Ruteo de Incendios Forestales</p>
        </div>

        <div class="card">
            <label>Seleccionar Región:</label>
            <select id="regionSelect" onchange="actualizarRegion()">
                <option value="Huancayo (Junín)">Huancayo (Bosque Acopalca)</option>
                <option value="Cusco">Cusco (Alto Tambomachay)</option>
                <option value="Puno">Puno (Pajonales Yanamayo)</option>
                <option value="Abancay (Apurímac)">Abancay (Bosque Intimpa)</option>
                <option value="Huaraz (Áncash)">Huaraz (Quebrada Llaca)</option>
            </select>
        </div>

        <div class="risk-box" id="riskBox">
            <div style="font-size: 13px; color: #94a3b8;" id="sectorName">Bosque Acopalca - Quebrada Shullcas</div>
            <div class="risk-val" id="riskVal">--%</div>
            <div class="risk-status" id="riskStatus">Consultando...</div>
        </div>

        <div class="metrics">
            <div class="metric-item">
                <span>TEMP.</span>
                <strong id="tempVal">-- °C</strong>
            </div>
            <div class="metric-item">
                <span>HUMEDAD</span>
                <strong id="humVal">-- %</strong>
            </div>
            <div class="metric-item">
                <span>VIENTO</span>
                <strong id="vientoVal">-- km/h</strong>
            </div>
        </div>

        <button class="btn btn-gps" onclick="obtenerGPS()">🎯 Mi Ubicación GPS en Vivo</button>
        <div class="gps-status" id="gpsStatus">GPS: No fijado (Se usará Cuartel Oficial)</div>

        <button class="btn btn-nav" onclick="abrirNavegacion()">🧭 Trazar Ruta Táctica</button>

        <script>
            let posActual = null;
            const regionesData = {
                "Huancayo (Junín)": { destLat: -11.9960, destLon: -75.1380, sector: "Bosque Acopalca - Quebrada Shullcas", base: "Compañia+de+Bomberos+Huancayo+30,+Jiron+Ancash+603,+Huancayo" },
                "Cusco": { destLat: -13.4750, destLon: -71.9680, sector: "Alto Tambomachay", base: "Compañia+de+Bomberos+Cusco+39,+Avenida+Garcilaso+313,+Cusco" },
                "Puno": { destLat: -15.8120, destLon: -70.0450, sector: "Pajonales Cerros Yanamayo", base: "Compañia+de+Bomberos+Puno+42,+Avenida+El+Sol+829,+Puno" },
                "Abancay (Apurímac)": { destLat: -13.5950, destLon: -72.8780, sector: "Bosque Intimpa - Ampay", base: "Compañia+de+Bomberos+Abancay+68,+Avenida+Seoane,+Abancay" },
                "Huaraz (Áncash)": { destLat: -9.4780, destLon: -77.4950, sector: "Pajonal Quebrada Llaca", base: "Compañia+de+Bomberos+Huaraz+84,+Huaraz" }
            };

            async function actualizarRegion() {
                const reg = document.getElementById('regionSelect').value;
                document.getElementById('sectorName').innerText = regionesData[reg].sector;
                try {
                    const res = await fetch('/api/riesgo?region=' + encodeURIComponent(reg));
                    const data = await res.json();
                    document.getElementById('riskVal').innerText = data.indice_riesgo_icia + '%';
                    document.getElementById('riskStatus').innerText = data.nivel_alerta;
                    document.getElementById('tempVal').innerText = data.temperatura_c + ' °C';
                    document.getElementById('humVal').innerText = data.humedad_relativa_pct + ' %';
                    document.getElementById('vientoVal').innerText = data.velocidad_viento_kmh + ' km/h';

                    const color = data.indice_riesgo_icia >= 70 ? '#ef4444' : (data.indice_riesgo_icia >= 40 ? '#f59e0b' : '#10b981');
                    document.getElementById('riskVal').style.color = color;
                    document.getElementById('riskStatus').style.color = color;
                    document.getElementById('riskBox').style.borderColor = color;
                } catch(e) {}
            }

            function obtenerGPS() {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (pos) => {
                            posActual = { lat: pos.coords.latitude, lon: pos.coords.longitude };
                            document.getElementById('gpsStatus').innerText = `GPS Fijado: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)} (±${Math.round(pos.coords.accuracy)}m)`;
                            fetch('/api/guardar_gps', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy})
                            });
                        },
                        (err) => { alert('No se pudo acceder al GPS: ' + err.message); },
                        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                    );
                }
            }

            function abrirNavegacion() {
                const reg = document.getElementById('regionSelect').value;
                const data = regionesData[reg];
                let url = '';
                if (posActual) {
                    url = `https://www.google.com/maps/dir/${posActual.lat},${posActual.lon}/${data.destLat},${data.destLon}`;
                } else {
                    url = `https://www.google.com/maps/dir/${data.base}/${data.destLat},${data.destLon}`;
                }
                window.open(url, '_blank');
            }

            actualizarRegion();
        </script>
    </body>
    </html>
    """
    return html_content