import math
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Configuración táctica de Cuarteles CGBVP Fijos y Zonas Forestales
REGIONES_CONFIG = {
    "Huancayo (Junín)": {
        "base_nombre": "Cía. Bomberos Huancayo B-30 (Jr. Loreto 457)",
        "base_lat": -12.07015,
        "base_lon": -75.20895,
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
        "version": "3.5",
        "endpoints": ["/api/riesgo", "/api/guardar_gps", "/api/ruta_optima", "/movil", "/manifest.json"]
    })

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "SHYp-IF Táctico",
        "short_name": "SHYp-IF",
        "start_url": "/movil",
        "display": "standalone",
        "background_color": "#0b132b",
        "theme_color": "#0b132b",
        "orientation": "portrait",
        "icons": [
            {
                "src": "https://cdn-icons-png.flaticon.com/512/785/785116.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route('/api/guardar_gps', methods=['POST'])
def guardar_gps():
    global ULTIMO_GPS_USUARIO
    data = request.get_json(silent=True) or {}
    lat = data.get('lat')
    lon = data.get('lon')
    acc = data.get('accuracy', 10.0)

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

    url_meteo = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    
    t, hr, w = None, None, None
    try:
        req = requests.get(
            url_meteo,
            headers={"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36"},
            timeout=5
        )
        if req.status_code == 200:
            res_json = req.json()
            curr = res_json.get("current", {})
            t = curr.get("temperature_2m")
            hr = curr.get("relative_humidity_2m")
            w = curr.get("wind_speed_10m")
    except Exception:
        pass

    if t is None or hr is None or w is None:
        offsets = {
            "Huancayo (Junín)": (14.2, 55.0, 16.5),
            "Cusco": (16.8, 42.0, 14.0),
            "Puno": (11.5, 30.0, 22.0),
            "Abancay (Apurímac)": (21.4, 38.0, 11.0),
            "Huaraz (Áncash)": (15.1, 49.0, 15.0)
        }
        t, hr, w = offsets.get(region_nombre, (18.0, 45.0, 15.0))

    t = float(t)
    hr = float(hr)
    w = float(w)

    peso_temp = (t / 35.0) * 35.0
    peso_hum = ((100.0 - hr) / 100.0) * 40.0
    peso_viento = (w / 50.0) * 25.0
    icia = round(max(5.0, min(99.0, peso_temp + peso_hum + peso_viento)), 1)

    if icia >= 70.0:
        alerta = "ALTO RIESGO / EXTREMO"
        semaforo = "rojo"
        icono = "🔥"
    elif icia >= 40.0:
        alerta = "RIESGO MODERADO"
        semaforo = "ambar"
        icono = "⚠️"
    else:
        alerta = "CONDICIÓN SEGURA"
        semaforo = "verde"
        icono = "🌲"

    return jsonify({
        "region": region_nombre,
        "sector": reg["bosque_nombre"],
        "temperatura_c": round(t, 1),
        "humedad_relativa_pct": round(hr, 1),
        "velocidad_viento_kmh": round(w, 1),
        "indice_riesgo_icia": icia,
        "nivel_alerta": alerta,
        "semaforo": semaforo,
        "icono_rango": icono,
        "base_oficial": reg["base_nombre"],
        "base_coords": [reg["base_lat"], reg["base_lon"]],
        "bosque_coords": [reg["bosque_lat"], reg["bosque_lon"]]
    })

@app.route('/api/ruta_optima', methods=['GET'])
def calcular_ruta():
    region_nombre = request.args.get('region', 'Huancayo (Junín)')
    lat_q = request.args.get('lat')
    lon_q = request.args.get('lon')
    reg = REGIONES_CONFIG.get(region_nombre, REGIONES_CONFIG["Huancayo (Junín)"])

    dest_lat = reg["bosque_lat"]
    dest_lon = reg["bosque_lon"]

    # Verificar si las coordenadas GPS enviadas están dentro del radio operativo de la región (< 80 km)
    usar_gps_local = False
    if lat_q and lon_q:
        lat_u = float(lat_q)
        lon_u = float(lon_q)
        dist_al_bosque_km = math.sqrt((dest_lat - lat_u)**2 + (dest_lon - lon_u)**2) * 111.0
        if dist_al_bosque_km <= 80.0:
            usar_gps_local = True
            origen_lat = lat_u
            origen_lon = lon_u
            origen_tipo = "Mi Ubicación GPS Exacta"

    if not usar_gps_local:
        origen_lat = reg["base_lat"]
        origen_lon = reg["base_lon"]
        origen_tipo = reg["base_nombre"]

    url_osrm = f"https://router.project-osrm.org/route/v1/driving/{origen_lon},{origen_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    try:
        resp = requests.get(url_osrm, headers={"User-Agent": "SHYp-IF/3.5"}, timeout=6)
        data = resp.json()
        if "routes" in data and len(data["routes"]) > 0:
            ruta = data["routes"][0]
            dist_km = round(ruta["distance"] / 1000.0, 2)
            dur_min = round(ruta["duration"] / 60.0, 1)
            coords = ruta["geometry"]["coordinates"]
            return jsonify({
                "status": "success",
                "usando_gps": usar_gps_local,
                "origen": origen_tipo,
                "destino": reg["bosque_nombre"],
                "distancia_km": dist_km,
                "duracion_min": dur_min,
                "coordenadas": coords
            })
    except Exception:
        pass

    dist_aprox = round(math.sqrt((dest_lat - origen_lat)**2 + (dest_lon - origen_lon)**2) * 111.0, 2)
    return jsonify({
        "status": "success",
        "usando_gps": usar_gps_local,
        "origen": origen_tipo,
        "destino": reg["bosque_nombre"],
        "distancia_km": dist_aprox,
        "duracion_min": round(dist_aprox * 2.2, 1),
        "coordenadas": [[origen_lon, origen_lat], [dest_lon, dest_lat]]
    })

@app.route('/movil')
def vista_movil():
    return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0b132b">
    <link rel="manifest" href="/manifest.json">
    <title>SHYp-IF Táctico</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 12px; display: flex; flex-direction: column; min-height: 100vh; }
        .header { text-align: center; margin-bottom: 10px; }
        .header h1 { font-size: 20px; color: #ff5722; font-weight: 800; }
        .header p { font-size: 11px; color: #94a3b8; }
        .card { background-color: #1c2541; border-radius: 10px; padding: 10px; margin-bottom: 10px; border: 1px solid #3a506b; }
        select { width: 100%; padding: 10px; border-radius: 8px; background: #0b132b; color: white; border: 1px solid #48cae4; font-size: 14px; font-weight: bold; }
        .risk-box { text-align: center; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 40px; font-weight: 900; color: #00f5d4; }
        .risk-status { font-size: 13px; font-weight: bold; color: #00f5d4; margin-top: 2px; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .metric-item { background: #1c2541; padding: 8px 4px; border-radius: 8px; text-align: center; width: 31%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 9px; color: #94a3b8; display: block; margin-bottom: 2px; }
        .metric-item strong { font-size: 15px; color: #48cae4; }
        #map { width: 100%; height: 290px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #3a506b; z-index: 1; }
        .btn { width: 100%; padding: 13px; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; cursor: pointer; margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 6px; }
        .btn-gps { background-color: #10b981; color: white; }
        .btn-nav { background-color: #0284c7; color: white; }
        .gps-status { font-size: 11px; text-align: center; color: #a7f3d0; margin-top: -2px; margin-bottom: 8px; font-weight: 600; }
        .badge-marker { display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 16px; box-shadow: 0 0 8px rgba(0,0,0,0.6); }
        .gmaps-dot {
            width: 18px;
            height: 18px;
            background-color: #2563eb;
            border: 3px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 10px rgba(37, 99, 235, 0.95);
        }
        .route-info { font-size: 12px; text-align: center; color: #38bdf8; margin-bottom: 8px; font-weight: bold; min-height: 16px; }
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

    <div id="map"></div>
    <div class="route-info" id="routeInfo">Selecciona una acción abajo:</div>

    <button class="btn btn-gps" id="btnGps" onclick="ubicarMiGPSExacto()">🎯 1. Ubicar Mi Posición Exacta (GPS)</button>
    <div class="gps-status" id="gpsStatus">GPS en espera de activación</div>

    <button class="btn btn-nav" onclick="trazarRutaManual()">🧭 2. Trazar Ruta hacia Zona Forestal</button>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: true }).setView([-12.07015, -75.20895], 13);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri & Contributors',
            maxZoom: 19
        }).addTo(map);

        setTimeout(() => { map.invalidateSize(); }, 300);

        let markerBomberos = null;
        let markerUsuario = null;
        let circuloPrecision = null;
        let markerDestino = null;
        let rutaLayer = null;
        let posActual = null;

        let baseCoords = [-12.07015, -75.20895]; // CGBVP B-30 Jr. Loreto 457
        let bosqueCoords = [-11.9960, -75.1380];
        let infoSector = { sector: "Bosque", riesgo: 0, alerta: "Seguro", color: "#10b981", icono: "🌲" };

        function crearIconoHTML(emoji, colorFondo) {
            return L.divIcon({
                className: 'badge-marker',
                html: `<div style="background-color:${colorFondo}; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff; font-size:17px;">${emoji}</div>`,
                iconSize: [34, 34],
                iconAnchor: [17, 17]
            });
        }

        const iconoPuntoAzul = L.divIcon({
            className: '',
            html: '<div class="gmaps-dot"></div>',
            iconSize: [18, 18],
            iconAnchor: [9, 9]
        });

        function calcularDistanciaKm(lat1, lon1, lat2, lon2) {
            return Math.sqrt(Math.pow(lat2 - lat1, 2) + Math.pow(lon2 - lon1, 2)) * 111.0;
        }

        // Al cambiar de región: SOLO muestra el cuartel y el bosque de esa región (SIN trazar ruta todavía)
        async function cambiarRegion() {
            const reg = document.getElementById('regionSelect').value;
            // Limpiar cualquier ruta previa para que no queden líneas cruzadas
            if (rutaLayer) {
                map.removeLayer(rutaLayer);
                rutaLayer = null;
            }
            document.getElementById('routeInfo').innerText = "Presiona 'Trazar Ruta' para dibujar el recorrido.";

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
                infoSector = {
                    sector: data.sector,
                    riesgo: data.indice_riesgo_icia,
                    alerta: data.nivel_alerta,
                    color: color,
                    icono: data.icono_rango,
                    baseNombre: data.base_oficial
                };

                mostrarMarcadoresRegion();
            } catch(e) {}
        }

        function mostrarMarcadoresRegion() {
            if (markerBomberos) map.removeLayer(markerBomberos);
            if (markerDestino) map.removeLayer(markerDestino);

            // 1. Cuartel Fijo de la Región
            markerBomberos = L.marker(baseCoords, { icon: crearIconoHTML('🚒', '#0284c7') })
                .addTo(map)
                .bindPopup(`<b>${infoSector.baseNombre}</b><br>(Cuartel Oficial CGBVP)`);

            // 2. Bosque de la Región
            markerDestino = L.marker(bosqueCoords, { icon: crearIconoHTML(infoSector.icono, infoSector.color) })
                .addTo(map)
                .bindPopup(`<b>${infoSector.sector}</b><br>Riesgo: ${infoSector.riesgo}% (${infoSector.alerta})`);

            // Encuadrar la vista limpia en la región seleccionada
            const puntosVista = [baseCoords, bosqueCoords];
            if (posActual && calcularDistanciaKm(posActual.lat, posActual.lon, bosqueCoords[0], bosqueCoords[1]) <= 80) {
                puntosVista.push([posActual.lat, posActual.lon]);
            }
            map.fitBounds(L.latLngBounds(puntosVista), { padding: [35, 35] });
        }

        // Botón 1: Ubicar mi posición GPS exacta (SIN dibujar la ruta todavía)
        function ubicarMiGPSExacto() {
            if (!("geolocation" in navigator)) {
                document.getElementById('gpsStatus').innerText = "❌ Dispositivo sin soporte GPS.";
                return;
            }

            document.getElementById('gpsStatus').innerText = "🛰️ Obteniendo coordenadas exactas del satélite...";

            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    const acc = Math.round(pos.coords.accuracy);

                    posActual = { lat: lat, lon: lon, acc: acc };

                    if (markerUsuario) map.removeLayer(markerUsuario);
                    if (circuloPrecision) map.removeLayer(circuloPrecision);

                    circuloPrecision = L.circle([lat, lon], {
                        radius: acc,
                        color: '#2563eb',
                        fillColor: '#3b82f6',
                        fillOpacity: 0.2,
                        weight: 1
                    }).addTo(map);

                    markerUsuario = L.marker([lat, lon], { icon: iconoPuntoAzul })
                        .addTo(map)
                        .bindPopup(`<b>📍 Estoy Aquí (GPS Exacto)</b><br>Precisión: ±${acc}m`)
                        .openPopup();

                    // Hacer zoom directo a tu calle exacta para que verifiques tu ubicación
                    map.setView([lat, lon], 16);

                    document.getElementById('gpsStatus').innerText = `✅ GPS Exacto: ${lat.toFixed(5)}, ${lon.toFixed(5)} (±${acc}m)`;
                    document.getElementById('btnGps').style.backgroundColor = '#059669';
                    document.getElementById('btnGps').innerText = `📍 Mi Ubicación GPS Fijada (±${acc}m)`;
                    document.getElementById('routeInfo').innerText = "✅ Ubicación lista. Ahora toca '2. Trazar Ruta'.";

                    fetch('/api/guardar_gps', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({lat: lat, lon: lon, accuracy: acc})
                    });
                },
                (err) => {
                    document.getElementById('gpsStatus').innerText = "⚠️ Activa la Ubicación en tu celular o abre en Chrome para permiso satelital.";
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000,
                    maximumAge: 0
                }
            );
        }

        // Botón 2: SOLO cuando el usuario toca este botón se dibuja la ruta
        async function trazarRutaManual() {
            const reg = document.getElementById('regionSelect').value;
            document.getElementById('routeInfo').innerText = "⏳ Calculando carretera y trocha óptima...";

            let url = `/api/ruta_optima?region=${encodeURIComponent(reg)}`;
            if (posActual) {
                url += `&lat=${posActual.lat}&lon=${posActual.lon}`;
            }

            try {
                const res = await fetch(url);
                const data = await res.json();
                if (data.status === "success" && data.coordenadas) {
                    if (rutaLayer) map.removeLayer(rutaLayer);
                    const latlngs = data.coordenadas.map(c => [c[1], c[0]]);
                    const colorRuta = data.usando_gps ? '#10b981' : '#0284c7';
                    rutaLayer = L.polyline(latlngs, { color: colorRuta, weight: 6, opacity: 0.95 }).addTo(map);
                    map.fitBounds(rutaLayer.getBounds(), { padding: [35, 35] });

                    document.getElementById('routeInfo').innerText = `🛣️ Desde ${data.origen}: ${data.distancia_km} km (~${data.duracion_min} min)`;
                }
            } catch(e) {
                document.getElementById('routeInfo').innerText = "❌ Error al trazar la ruta.";
            }
        }

        // Al iniciar: Solo carga los marcadores de la región (NO traza ruta sola)
        cambiarRegion();
    </script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)