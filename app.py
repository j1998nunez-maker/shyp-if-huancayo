import math
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Base de datos operacional de Cuarteles CGBVP y Zonas Forestales de Cobertura
REGIONES_CONFIG = {
    "Huancayo (Junín)": {
        "base_nombre": "Cía. Bomberos Huancayo B-30 (Jr. Áncash 603)",
        "base_lat": -12.06915,
        "base_lon": -75.20985,
        "dir_maps": "Compañia+de+Bomberos+Huancayo+30,+Jiron+Ancash+603,+Huancayo",
        "bosque_nombre": "Bosque Acopalca - Quebrada Shullcas",
        "bosque_lat": -11.9960,
        "bosque_lon": -75.1380
    },
    "Cusco": {
        "base_nombre": "Cía. Bomberos Cusco B-39 (Av. Garcilaso 313)",
        "base_lat": -13.52055,
        "base_lon": -71.97235,
        "dir_maps": "Compañia+de+Bomberos+Cusco+39,+Avenida+Garcilaso+313,+Cusco",
        "bosque_nombre": "Alto Tambomachay",
        "bosque_lat": -13.4750,
        "bosque_lon": -71.9680
    },
    "Puno": {
        "base_nombre": "Cía. Bomberos Puno B-42 (Av. El Sol 829)",
        "base_lat": -15.83685,
        "base_lon": -70.02295,
        "dir_maps": "Compañia+de+Bomberos+Puno+42,+Avenida+El+Sol+829,+Puno",
        "bosque_nombre": "Pajonales Cerros Yanamayo",
        "bosque_lat": -15.8120,
        "bosque_lon": -70.0450
    },
    "Abancay (Apurímac)": {
        "base_nombre": "Cía. Bomberos Abancay B-68 (Av. Seoane)",
        "base_lat": -13.63585,
        "base_lon": -72.87815,
        "dir_maps": "Compañia+de+Bomberos+Abancay+68,+Avenida+Seoane,+Abancay",
        "bosque_nombre": "Santuario Nal. Ampay - Bosque Intimpa",
        "bosque_lat": -13.5950,
        "bosque_lon": -72.8780
    },
    "Huaraz (Áncash)": {
        "base_nombre": "Cía. Bomberos Huaraz B-84",
        "base_lat": -9.52985,
        "base_lon": -77.52875,
        "dir_maps": "Compañia+de+Bomberos+Huaraz+84,+Huaraz",
        "bosque_nombre": "Pajonales Quebrada Llaca - Huascarán",
        "bosque_lat": -9.4780,
        "bosque_lon": -77.4950
    }
}

# Almacenamiento volátil de última posición satelital reportada
ULTIMO_GPS_USUARIO = {
    "lat": None,
    "lon": None,
    "accuracy": None
}

@app.route('/')
def home():
    return jsonify({
        "sistema": "SHYp-IF Backend API",
        "estado": "Operativo",
        "version": "2.0",
        "endpoints": ["/api/riesgo", "/api/guardar_gps", "/api/ruta_optima", "/movil"]
    })

@app.route('/api/guardar_gps', methods=['POST'])
def guardar_gps():
    global ULTIMO_GPS_USUARIO
    data = request.get_json(silent=True) or {}
    lat = data.get('lat')
    lon = data.get('lon')
    acc = data.get('accuracy', 0.0)

    if lat is not None and lon is not None:
        ULTIMO_GPS_USUARIO["lat"] = float(lat)
        ULTIMO_GPS_USUARIO["lon"] = float(lon)
        ULTIMO_GPS_USUARIO["accuracy"] = float(acc)
        return jsonify({"status": "success", "gps": ULTIMO_GPS_USUARIO}), 200

    return jsonify({"status": "error", "mensaje": "Coordenadas no validas"}), 400

@app.route('/api/riesgo', methods=['GET'])
def obtener_riesgo():
    region_nombre = request.args.get('region', 'Huancayo (Junín)')
    reg = REGIONES_CONFIG.get(region_nombre, REGIONES_CONFIG["Huancayo (Junín)"])

    lat = reg["bosque_lat"]
    lon = reg["bosque_lon"]

    # Consulta meteorológica en tiempo real a Open-Meteo
    url_meteo = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
    
    try:
        r = requests.get(url_meteo, timeout=6)
        clima = r.json().get('current', {})
        t = clima.get('temperature_2m', 20.0)
        hr = clima.get('relative_humidity_2m', 45.0)
        w = clima.get('wind_speed_10m', 15.0)
    except Exception:
        t, hr, w = 22.0, 40.0, 18.0

    # Algoritmo ICIA (Índice de Combustibilidad e Ignición Ambiental)
    peso_temp = (t / 35.0) * 35.0
    peso_hum = ((100.0 - hr) / 100.0) * 40.0
    peso_viento = (w / 50.0) * 25.0
    icia = round(max(5.0, min(99.0, peso_temp + peso_hum + peso_viento)), 1)

    if icia >= 70.0:
        alerta = "ALTO RIESGO / EXTREMO"
    elif icia >= 40.0:
        alerta = "RIESGO MODERADO"
    else:
        alerta = "CONDICIÓN SEGURA"

    return jsonify({
        "region": region_nombre,
        "sector": reg["bosque_nombre"],
        "temperatura_c": t,
        "humedad_relativa_pct": hr,
        "velocidad_viento_kmh": w,
        "indice_riesgo_icia": icia,
        "nivel_alerta": alerta,
        "base_oficial": reg["base_nombre"]
    })

@app.route('/api/ruta_optima', methods=['GET'])
def calcular_ruta():
    region_nombre = request.args.get('region', 'Huancayo (Junín)')
    usar_gps = request.args.get('usar_gps', 'false').lower() == 'true'
    reg = REGIONES_CONFIG.get(region_nombre, REGIONES_CONFIG["Huancayo (Junín)"])

    if usar_gps and ULTIMO_GPS_USUARIO["lat"] is not None:
        origen_lat = ULTIMO_GPS_USUARIO["lat"]
        origen_lon = ULTIMO_GPS_USUARIO["lon"]
        origen_tipo = "GPS Usuario en Terreno"
    else:
        origen_lat = reg["base_lat"]
        origen_lon = reg["base_lon"]
        origen_tipo = reg["base_nombre"]

    dest_lat = reg["bosque_lat"]
    dest_lon = reg["bosque_lon"]

    # Consulta OSRM vial por carretera
    url_osrm = f"https://router.project-osrm.org/route/v1/driving/{origen_lon},{origen_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    try:
        resp = requests.get(url_osrm, timeout=8)
        data = resp.json()
        if "routes" in data and len(data["routes"]) > 0:
            ruta = data["routes"][0]
            dist_km = round(ruta["distance"] / 1000.0, 2)
            dur_min = round(ruta["duration"] / 60.0, 1)
            coords = ruta["geometry"]["coordinates"]
            return jsonify({
                "status": "success",
                "origen": origen_tipo,
                "destino": reg["bosque_nombre"],
                "distancia_km": dist_km,
                "duracion_min": dur_min,
                "coordenadas": coords
            })
    except Exception:
        pass

    return jsonify({"status": "error", "mensaje": "No se pudo calcular la ruta vial"}), 500

# ==========================================
# VISTA MÓVIL DIRECTA PARA LA APP INDEPENDIENTE
# ==========================================
@app.route('/movil')
def vista_movil():
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SHYp-IF Táctico</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 16px; display: flex; flex-direction: column; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 18px; }
        .header h1 { font-size: 22px; color: #ff5722; font-weight: 800; letter-spacing: 0.5px; }
        .header p { font-size: 13px; color: #94a3b8; margin-top: 4px; }
        .card { background-color: #1c2541; border-radius: 12px; padding: 14px; margin-bottom: 14px; border: 1px solid #3a506b; }
        label { font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: bold; margin-bottom: 6px; display: block; }
        select { width: 100%; padding: 12px; border-radius: 8px; background: #0b132b; color: white; border: 1px solid #48cae4; font-size: 15px; font-weight: bold; }
        .risk-box { text-align: center; padding: 18px; border-radius: 12px; margin-bottom: 14px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 46px; font-weight: 900; color: #00f5d4; }
        .risk-status { font-size: 15px; font-weight: bold; color: #00f5d4; margin-top: 4px; letter-spacing: 0.5px; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 14px; }
        .metric-item { background: #1c2541; padding: 12px 6px; border-radius: 8px; text-align: center; width: 31%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 10px; color: #94a3b8; display: block; margin-bottom: 4px; }
        .metric-item strong { font-size: 16px; color: #48cae4; }
        .btn { width: 100%; padding: 15px; border: none; border-radius: 10px; font-size: 15px; font-weight: bold; cursor: pointer; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 8px; text-decoration: none; }
        .btn-gps { background-color: #10b981; color: white; }
        .btn-nav { background-color: #0284c7; color: white; }
        .gps-status { font-size: 12px; text-align: center; color: #a7f3d0; margin-top: -4px; margin-bottom: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 SHYp-IF Táctico</h1>
        <p>Sistema Operativo de Despacho y Ruteo Forestal</p>
    </div>

    <div class="card">
        <label>Seleccionar Región Operativa:</label>
        <select id="regionSelect" onchange="actualizarRegion()">
            <option value="Huancayo (Junín)">Huancayo (Bosque Acopalca)</option>
            <option value="Cusco">Cusco (Alto Tambomachay)</option>
            <option value="Puno">Puno (Pajonales Yanamayo)</option>
            <option value="Abancay (Apurímac)">Abancay (Bosque Intimpa)</option>
            <option value="Huaraz (Áncash)">Huaraz (Quebrada Llaca)</option>
        </select>
    </div>

    <div class="risk-box" id="riskBox">
        <div style="font-size: 13px; color: #94a3b8; font-weight: 600;" id="sectorName">Bosque Acopalca - Quebrada Shullcas</div>
        <div class="risk-val" id="riskVal">--%</div>
        <div class="risk-status" id="riskStatus">Consultando...</div>
    </div>

    <div class="metrics">
        <div class="metric-item">
            <span>TEMPERATURA</span>
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

    <button class="btn btn-gps" onclick="obtenerGPS()">🎯 Fijar Mi Posición Satelital GPS</button>
    <div class="gps-status" id="gpsStatus">GPS: No fijado (Origen: Cuartel Oficial CGBVP)</div>

    <button class="btn btn-nav" onclick="abrirNavegacion()">🧭 Iniciar Navegación por Carretera / Trocha</button>

    <script>
        let posActual = null;
        const regionesData = {
            "Huancayo (Junín)": { destLat: -11.9960, destLon: -75.1380, sector: "Bosque Acopalca - Quebrada Shullcas", base: "Compañia+de+Bomberos+Huancayo+30,+Jiron+Ancash+603,+Huancayo" },
            "Cusco": { destLat: -13.4750, destLon: -71.9680, sector: "Alto Tambomachay", base: "Compañia+de+Bomberos+Cusco+39,+Avenida+Garcilaso+313,+Cusco" },
            "Puno": { destLat: -15.8120, destLon: -70.0450, sector: "Pajonales Cerros Yanamayo", base: "Compañia+de+Bomberos+Puno+42,+Avenida+El+Sol+829,+Puno" },
            "Abancay (Apurímac)": { destLat: -13.5950, destLon: -72.8780, sector: "Santuario Nal. Ampay - Bosque Intimpa", base: "Compañia+de+Bomberos+Abancay+68,+Avenida+Seoane,+Abancay" },
            "Huaraz (Áncash)": { destLat: -9.4780, destLon: -77.4950, sector: "Pajonales Quebrada Llaca - Huascarán", base: "Compañia+de+Bomberos+Huaraz+84,+Huaraz" }
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
                        document.getElementById('gpsStatus').innerText = `GPS Activo: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)} (±${Math.round(pos.coords.accuracy)}m)`;
                        fetch('/api/guardar_gps', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy})
                        });
                    },
                    (err) => { alert('Por favor activa los permisos de ubicación GPS en tu celular.'); },
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
            window.open(url, '_system');
        }

        actualizarRegion();
    </script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)