import math
import requests
from flask import Flask, jsonify, request, Response

app = Flask(__name__)

# Configuración táctica de Cuarteles CGBVP y Zonas Forestales
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
        "version": "3.0",
        "endpoints": ["/api/riesgo", "/api/guardar_gps", "/api/ruta_optima", "/movil", "/manifest.json"]
    })

# Manifiesto para que Android instale la App de forma nativa con GPS desbloqueado
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
    acc = data.get('accuracy', 15.0)

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

    if lat_q and lon_q:
        origen_lat = float(lat_q)
        origen_lon = float(lon_q)
        origen_tipo = "Mi Ubicación Actual"
    elif ULTIMO_GPS_USUARIO["lat"] is not None:
        origen_lat = ULTIMO_GPS_USUARIO["lat"]
        origen_lon = ULTIMO_GPS_USUARIO["lon"]
        origen_tipo = "Mi Ubicación Actual"
    else:
        origen_lat = reg["base_lat"]
        origen_lon = reg["base_lon"]
        origen_tipo = reg["base_nombre"]

    dest_lat = reg["bosque_lat"]
    dest_lon = reg["bosque_lon"]

    url_osrm = f"https://router.project-osrm.org/route/v1/driving/{origen_lon},{origen_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    try:
        resp = requests.get(url_osrm, headers={"User-Agent": "SHYp-IF/3.0"}, timeout=6)
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

    dist_aprox = round(math.sqrt((dest_lat - origen_lat)**2 + (dest_lon - origen_lon)**2) * 111.0, 2)
    return jsonify({
        "status": "success",
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
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
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
        .tip-tocar { font-size: 11px; text-align: center; color: #38bdf8; margin-bottom: 8px; font-weight: 600; }
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
    <div class="tip-tocar">👆 Toca cualquier calle en el mapa o arrastra el pin 📍 para ajustar tu posición exacta.</div>

    <button class="btn btn-gps" id="btnGps" onclick="detectarUbicacionHibrida()">🎯 Detectar Mi Ubicación Ahora</button>
    <div class="gps-status" id="gpsStatus">🛰️ Buscando señal de ubicación...</div>

    <button class="btn btn-nav" onclick="trazarRutaVial()">🧭 Trazar Ruta desde Mi Ubicación</button>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: true }).setView([-12.07015, -75.20895], 13);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri & Contributors',
            maxZoom: 18
        }).addTo(map);

        setTimeout(() => { map.invalidateSize(); }, 300);

        let markerBomberos = null;
        let markerUsuario = null;
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
                infoSector = {
                    sector: data.sector,
                    riesgo: data.indice_riesgo_icia,
                    alerta: data.nivel_alerta,
                    color: color,
                    icono: data.icono_rango,
                    baseNombre: data.base_oficial
                };

                actualizarMarcadoresEnMapa();
                trazarRutaVial();
            } catch(e) {}
        }

        function actualizarMarcadoresEnMapa() {
            if (markerBomberos) map.removeLayer(markerBomberos);
            if (markerUsuario) map.removeLayer(markerUsuario);
            if (markerDestino) map.removeLayer(markerDestino);

            // 1. Mostrar SIEMPRE el Cuartel Fijo de Bomberos como referencia oficial
            markerBomberos = L.marker(baseCoords, { icon: crearIconoHTML('🚒', '#0284c7') })
                .addTo(map)
                .bindPopup(`<b>${infoSector.baseNombre || 'Cuartel CGBVP'}</b><br>(Base Fija Oficial)`);

            // 2. Si hay ubicación del usuario, mostrar el pin verde arrastrable y usarlo como origen
            if (posActual) {
                markerUsuario = L.marker([posActual.lat, posActual.lon], {
                    icon: crearIconoHTML('📍', '#10b981'),
                    draggable: true
                }).addTo(map).bindPopup(`<b>📍 Mi Ubicación Actual</b><br>Origen de la ruta táctica`).openPopup();

                markerUsuario.on('dragend', function(ev) {
                    const nuevaPos = ev.target.getLatLng();
                    fijarCoordenadasUsuario(nuevaPos.lat, nuevaPos.lng, 5, "Posición ajustada en mapa");
                });
            }

            // 3. Mostrar el Destino Forestal según rango de riesgo
            markerDestino = L.marker(bosqueCoords, { icon: crearIconoHTML(infoSector.icono, infoSector.color) })
                .addTo(map)
                .bindPopup(`<b>${infoSector.sector}</b><br>Riesgo: ${infoSector.riesgo}% (${infoSector.alerta})`);

            const puntoPartida = posActual ? [posActual.lat, posActual.lon] : baseCoords;
            const bounds = L.latLngBounds([puntoPartida, bosqueCoords]);
            map.fitBounds(bounds, { padding: [35, 35] });
        }

        function fijarCoordenadasUsuario(lat, lon, acc, fuente) {
            posActual = { lat: lat, lon: lon, acc: acc };
            document.getElementById('gpsStatus').innerText = `✅ ${fuente}: ${lat.toFixed(4)}, ${lon.toFixed(4)} (±${acc}m)`;
            document.getElementById('btnGps').style.backgroundColor = '#059669';
            document.getElementById('btnGps').innerText = `📍 Mi Ubicación Activa (${fuente})`;

            fetch('/api/guardar_gps', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lat: lat, lon: lon, accuracy: acc})
            });

            actualizarMarcadoresEnMapa();
            trazarRutaVial();
        }

        // Sistema de Geolocalización de 3 Niveles (Satélite -> Celda/Wi-Fi -> Red IP)
        async function detectarUbicacionHibrida() {
            document.getElementById('gpsStatus').innerText = "🛰️ Obteniendo coordenadas del dispositivo...";

            if ("geolocation" in navigator) {
                navigator.geolocation.getCurrentPosition(
                    (pos) => {
                        fijarCoordenadasUsuario(pos.coords.latitude, pos.coords.longitude, Math.round(pos.coords.accuracy || 15), "GPS Satelital");
                    },
                    (err1) => {
                        // Intento 2: Baja potencia / Red Wi-Fi
                        navigator.geolocation.getCurrentPosition(
                            (pos2) => {
                                fijarCoordenadasUsuario(pos2.coords.latitude, pos2.coords.longitude, Math.round(pos2.coords.accuracy || 40), "Antena / Wi-Fi");
                            },
                            async (err2) => {
                                // Intento 3: Si el APK bloquea permisos de Android, triangular por Red IP automáticamente sin lanzar alertas molestas
                                await fallbackUbicacionPorRed();
                            },
                            { enableHighAccuracy: false, timeout: 6000, maximumAge: 300000 }
                        );
                    },
                    { enableHighAccuracy: true, timeout: 7000, maximumAge: 0 }
                );
            } else {
                await fallbackUbicacionPorRed();
            }
        }

        async function fallbackUbicacionPorRed() {
            try {
                const r = await fetch('https://ipapi.co/json/');
                const d = await r.json();
                if (d.latitude && d.longitude) {
                    fijarCoordenadasUsuario(parseFloat(d.latitude), parseFloat(d.longitude), 120, "Triangulación de Red");
                    return;
                }
            } catch(e) {}

            try {
                const r2 = await fetch('https://get.geojs.io/v1/ip/geo.json');
                const d2 = await r2.json();
                if (d2.latitude && d2.longitude) {
                    fijarCoordenadasUsuario(parseFloat(d2.latitude), parseFloat(d2.longitude), 150, "Triangulación de Red");
                    return;
                }
            } catch(e) {}

            // Si todo falla, posicionar un pin inicial editable en Huancayo centro para que el usuario lo mueva con un toque
            fijarCoordenadasUsuario(-12.0655, -75.2045, 25, "Pin Táctico Móvil");
        }

        // Al tocar cualquier calle del mapa, mueve tu ubicación allí inmediatamente y recalcula la ruta
        map.on('click', function(e) {
            fijarCoordenadasUsuario(e.latlng.lat, e.latlng.lng, 5, "Ubicación Exacta en Mapa");
        });

        async function trazarRutaVial() {
            const reg = document.getElementById('regionSelect').value;
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
                    // Línea verde brillante cuando sale desde tu ubicación GPS, azul cuando sale desde el cuartel
                    const colorRuta = posActual ? '#10b981' : '#0284c7';
                    rutaLayer = L.polyline(latlngs, { color: colorRuta, weight: 6, opacity: 0.95 }).addTo(map);
                    map.fitBounds(rutaLayer.getBounds(), { padding: [35, 35] });
                }
            } catch(e) {}
        }

        // Iniciar al abrir la aplicación
        cambiarRegion();
        detectarUbicacionHibrida();
    </script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)