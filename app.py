import math
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuración táctica de Cuarteles CGBVP y Zonas Forestales
REGIONES_CONFIG = {
    "Huancayo (Junín)": {
        "base_nombre": "Cía. Bomberos Huancayo B-30 (Jr. Áncash 603)",
        "base_lat": -12.06915,
        "base_lon": -75.20985,
        "bosque_nombre": "Bosque Acopalca - Quebrada Shullcas",
        "bosque_lat": -11.9960,
        "bosque_lon": -75.1380
    },
    "Cusco": {
        "base_nombre": "Cía. Bomberos Cusco B-39 (Av. Garcilaso 313)",
        "base_lat": -13.52055,
        "base_lon": -71.97235,
        "bosque_nombre": "Alto Tambomachay",
        "bosque_lat": -13.4750,
        "bosque_lon": -71.9680
    },
    "Puno": {
        "base_nombre": "Cía. Bomberos Puno B-42 (Av. El Sol 829)",
        "base_lat": -15.83685,
        "base_lon": -70.02295,
        "bosque_nombre": "Pajonales Cerros Yanamayo",
        "bosque_lat": -15.8120,
        "bosque_lon": -70.0450
    },
    "Abancay (Apurímac)": {
        "base_nombre": "Cía. Bomberos Abancay B-68 (Av. Seoane)",
        "base_lat": -13.63585,
        "base_lon": -72.87815,
        "bosque_nombre": "Santuario Nal. Ampay - Bosque Intimpa",
        "bosque_lat": -13.5950,
        "bosque_lon": -72.8780
    },
    "Huaraz (Áncash)": {
        "base_nombre": "Cía. Bomberos Huaraz B-84",
        "base_lat": -9.52985,
        "base_lon": -77.52875,
        "bosque_nombre": "Pajonales Quebrada Llaca - Huascarán",
        "bosque_lat": -9.4780,
        "bosque_lon": -77.4950
    }
}

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
        "version": "2.2",
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

    return jsonify({"status": "error", "mensaje": "Coordenadas no válidas"}), 400

@app.route('/api/riesgo', methods=['GET'])
def obtener_riesgo():
    region_nombre = request.args.get('region', 'Huancayo (Junín)')
    reg = REGIONES_CONFIG.get(region_nombre, REGIONES_CONFIG["Huancayo (Junín)"])

    lat = reg["bosque_lat"]
    lon = reg["bosque_lon"]

    url_meteo = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
    
    t, hr, w = 18.0, 48.0, 12.0
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url_meteo, headers=headers, timeout=6)
        if r.status_code == 200:
            clima = r.json().get('current', {})
            t = float(clima.get('temperature_2m', 18.0))
            hr = float(clima.get('relative_humidity_2m', 48.0))
            w = float(clima.get('wind_speed_10m', 12.0))
    except Exception:
        pass

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
        "temperatura_c": round(t, 1),
        "humedad_relativa_pct": round(hr, 1),
        "velocidad_viento_kmh": round(w, 1),
        "indice_riesgo_icia": icia,
        "nivel_alerta": alerta,
        "base_oficial": reg["base_nombre"],
        "base_coords": [reg["base_lat"], reg["base_lon"]],
        "bosque_coords": [reg["bosque_lat"], reg["bosque_lon"]]
    })

@app.route('/api/ruta_optima', methods=['GET'])
def calcular_ruta():
    region_nombre = request.args.get('region', 'Huancayo (Junín)')
    usar_gps = request.args.get('usar_gps', 'false').lower() == 'true'
    reg = REGIONES_CONFIG.get(region_nombre, REGIONES_CONFIG["Huancayo (Junín)"])

    if usar_gps and ULTIMO_GPS_USUARIO["lat"] is not None:
        origen_lat = ULTIMO_GPS_USUARIO["lat"]
        origen_lon = ULTIMO_GPS_USUARIO["lon"]
        origen_tipo = "GPS de Brigadista"
    else:
        origen_lat = reg["base_lat"]
        origen_lon = reg["base_lon"]
        origen_tipo = reg["base_nombre"]

    dest_lat = reg["bosque_lat"]
    dest_lon = reg["bosque_lon"]

    url_osrm = f"https://router.project-osrm.org/route/v1/driving/{origen_lon},{origen_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url_osrm, headers=headers, timeout=8)
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

@app.route('/movil')
def vista_movil():
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SHYp-IF Táctico</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 12px; display: flex; flex-direction: column; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 12px; }
        .header h1 { font-size: 20px; color: #ff5722; font-weight: 800; }
        .header p { font-size: 11px; color: #94a3b8; }
        .card { background-color: #1c2541; border-radius: 10px; padding: 10px; margin-bottom: 10px; border: 1px solid #3a506b; }
        select { width: 100%; padding: 10px; border-radius: 8px; background: #0b132b; color: white; border: 1px solid #48cae4; font-size: 14px; font-weight: bold; }
        .risk-box { text-align: center; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 42px; font-weight: 900; color: #00f5d4; }
        .risk-status { font-size: 13px; font-weight: bold; color: #00f5d4; margin-top: 2px; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .metric-item { background: #1c2541; padding: 8px 4px; border-radius: 8px; text-align: center; width: 31%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 9px; color: #94a3b8; display: block; margin-bottom: 2px; }
        .metric-item strong { font-size: 15px; color: #48cae4; }
        #map { width: 100%; height: 280px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #3a506b; z-index: 1; }
        .btn { width: 100%; padding: 14px; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .btn-gps { background-color: #10b981; color: white; }
        .btn-nav { background-color: #0284c7; color: white; }
        .gps-status { font-size: 11px; text-align: center; color: #a7f3d0; margin-top: -4px; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 SHYp-IF Táctico</h1>
        <p>Monitoreo Satelital y Ruteo Operativo</p>
    </div>

    <div class="card">
        <select id="regionSelect" onchange="cambiarRegion()">
            <option value="Huancayo (Junín)">Huancayo (Bosque Acopalca)</option>
            <option value="Cusco">Cusco (Alto Tambomachay)</option>
            <option value="Puno">Puno (Pajonales Yanamayo)</option>
            <option value="Abancay (Apurímac)">Abancay (Bosque Intimpa)</option>
            <option value="Huaraz (Áncash)">Huaraz (Quebrada Llaca)</option>
        </select>
    </div>

    <div class="risk-box" id="riskBox">
        <div style="font-size: 12px; color: #94a3b8; font-weight: 600;" id="sectorName">Sector Forestal</div>
        <div class="risk-val" id="riskVal">--%</div>
        <div class="risk-status" id="riskStatus">Consultando Satélite...</div>
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

    <!-- MAPA TÁCTICO MÓVIL SIN BLOQUEOS -->
    <div id="map"></div>

    <button class="btn btn-gps" onclick="obtenerGPS()">🎯 Fijar Mi Posición Satelital GPS</button>
    <div class="gps-status" id="gpsStatus">GPS: No fijado (Origen: Cuartel Oficial CGBVP)</div>

    <button class="btn btn-nav" onclick="trazarRutaVial()">🧭 Trazar Ruta Óptima en Mapa</button>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        // Mapa base ArcGIS Esri: 100% libre, sin API key, sin marcas de agua y de alto rendimiento
        let map = L.map('map', { zoomControl: true }).setView([-12.06915, -75.20985], 11);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri & Contributors',
            maxZoom: 18
        }).addTo(map);

        setTimeout(() => { map.invalidateSize(); }, 300);

        let markerOrigen = null;
        let markerDestino = null;
        let rutaLayer = null;
        let posActual = null;
        let baseCoords = [-12.06915, -75.20985];
        let bosqueCoords = [-11.9960, -75.1380];

        async function cambiarRegion() {
            const reg = document.getElementById('regionSelect').value;
            try {
                const res = await fetch('/api/riesgo?region=' + encodeURIComponent(reg));
                const data = await res.json();
                document.getElementById('sectorName').innerText = data.sector;
                document.getElementById('riskVal').innerText = data.indice_riesgo_icia + '%';
                document.getElementById('riskStatus').innerText = data.nivel_alerta;
                document.getElementById('tempVal').innerText = data.temperatura_c + ' °C';
                document.getElementById('humVal').innerText = data.humedad_relativa_pct + ' %';
                document.getElementById('vientoVal').innerText = data.velocidad_viento_kmh + ' km/h';

                const color = data.indice_riesgo_icia >= 70 ? '#ef4444' : (data.indice_riesgo_icia >= 40 ? '#f59e0b' : '#10b981');
                document.getElementById('riskVal').style.color = color;
                document.getElementById('riskStatus').style.color = color;
                document.getElementById('riskBox').style.borderColor = color;

                baseCoords = data.base_coords;
                bosqueCoords = data.bosque_coords;

                actualizarMarcadoresEnMapa();
            } catch(e) {}
        }

        function actualizarMarcadoresEnMapa() {
            if (markerOrigen) map.removeLayer(markerOrigen);
            if (markerDestino) map.removeLayer(markerDestino);
            if (rutaLayer) map.removeLayer(rutaLayer);

            const orig = posActual ? [posActual.lat, posActual.lon] : baseCoords;
            const origLabel = posActual ? "📍 Mi Posición GPS" : "🚒 Cuartel Oficial CGBVP";

            markerOrigen = L.marker(orig).addTo(map).bindPopup(origLabel);
            markerDestino = L.marker(bosqueCoords).addTo(map).bindPopup("🔥 Zona Forestal Objetivo");

            const bounds = L.latLngBounds([orig, bosqueCoords]);
            map.fitBounds(bounds, { padding: [25, 25] });
        }

        function procesarCoordenadas(pos) {
            posActual = { lat: pos.coords.latitude, lon: pos.coords.longitude };
            const prec = Math.round(pos.coords.accuracy);
            document.getElementById('gpsStatus').innerText = `GPS Activo: (±${prec}m de precisión)`;
            
            fetch('/api/guardar_gps', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lat: posActual.lat, lon: posActual.lon, accuracy: prec})
            });

            actualizarMarcadoresEnMapa();
        }

        function obtenerGPS() {
            if ("geolocation" in navigator) {
                document.getElementById('gpsStatus').innerText = "Conectando con satélites GPS...";
                navigator.geolocation.getCurrentPosition(
                    procesarCoordenadas,
                    (err) => {
                        // Intento secundario con menor exigencia satelital (triangulación por red/celda)
                        navigator.geolocation.getCurrentPosition(
                            procesarCoordenadas,
                            (errFinal) => {
                                alert("Para usar tu ubicación en vivo, ve a: Ajustes del Teléfono > Aplicaciones > SHYp-iF > Permisos > Ubicación > 'Permitir siempre o con la app en uso'.");
                                document.getElementById('gpsStatus').innerText = "GPS no disponible. Usando Cuartel Oficial.";
                            },
                            { enableHighAccuracy: false, timeout: 15000, maximumAge: 60000 }
                        );
                    },
                    { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
                );
            }
        }

        async function trazarRutaVial() {
            const reg = document.getElementById('regionSelect').value;
            const usarGps = posActual !== null;
            try {
                const res = await fetch(`/api/ruta_optima?region=${encodeURIComponent(reg)}&usar_gps=${usarGps}`);
                const data = await res.json();
                if (data.status === "success" && data.coordenadas) {
                    if (rutaLayer) map.removeLayer(rutaLayer);
                    const latlngs = data.coordenadas.map(c => [c[1], c[0]]);
                    rutaLayer = L.polyline(latlngs, { color: '#0284c7', weight: 6, opacity: 0.95 }).addTo(map);
                    map.fitBounds(rutaLayer.getBounds(), { padding: [25, 25] });
                }
            } catch(e) {
                alert('No se pudo calcular la ruta vial en este momento.');
            }
        }

        cambiarRegion();
    </script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)