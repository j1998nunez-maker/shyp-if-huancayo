import csv
import io
import sqlite3
import math
import requests
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "af_predictivo_cientifico.db"

DEPARTAMENTOS_PERU = {
    "TODOS (Nacional)": {"lat": -9.5, "lon": -75.0, "zoom": 5, "bbox": [-18.3, -81.3, 0.0, -68.6]},
    "Puno": {"lat": -15.5, "lon": -70.0, "zoom": 7, "bbox": [-17.3, -71.2, -13.0, -68.7]},
    "Cusco": {"lat": -13.5, "lon": -72.0, "zoom": 8, "bbox": [-15.0, -73.5, -11.5, -70.3]},
    "Apurímac": {"lat": -14.0, "lon": -73.0, "zoom": 8, "bbox": [-14.8, -73.8, -13.1, -72.0]},
    "Junín": {"lat": -11.5, "lon": -75.0, "zoom": 8, "bbox": [-12.7, -76.5, -10.6, -73.5]}
}

# FORZAR NO CACHÉ
@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

def obtener_hora_peru():
    return datetime.datetime.utcnow() - datetime.timedelta(hours=5)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS eventos_reales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, lat REAL, lon REAL,
            temp_c REAL, humedad_pct REAL, viento_kmh REAL, ffdi_registrado REAL
        )
    """)
    c.execute("SELECT COUNT(*) FROM eventos_reales")
    if c.fetchone()[0] == 0:
        semillas = [
            ("2026-10-13", -13.5240, -72.7350, 22.8, 23.0, 27.5, 21.4),
            ("2026-10-19", -13.5085, -71.8150, 19.5, 21.0, 32.0, 18.2),
            ("2026-09-25", -11.9960, -75.1380, 18.4, 26.0, 24.5, 14.5)
        ]
        c.executemany("INSERT INTO eventos_reales (fecha, lat, lon, temp_c, humedad_pct, viento_kmh, ffdi_registrado) VALUES (?, ?, ?, ?, ?, ?, ?)", semillas)
        conn.commit()
    conn.close()

init_db()

# MOTOR 1: SATÉLITE NASA (Detecta lo que ya se está quemando HOY)
def escanear_nasa_firms():
    focos_hoy = []
    urls = [
        "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_24h.csv",
        "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_24h.csv"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    lat, lon = float(row.get("latitude", 0)), float(row.get("longitude", 0))
                    if -18.3 <= lat <= 0.0 and -81.3 <= lon <= -68.6:
                        focos_hoy.append({
                            "lat": round(lat, 4), "lon": round(lon, 4),
                            "frp": float(row.get("frp", 0)), "fecha": row.get("acq_date", "")
                        })
        except:
            continue
    return focos_hoy

@app.route('/api/datos_nacionales', methods=['GET'])
def datos_nacionales():
    depto = request.args.get('departamento', 'TODOS (Nacional)')
    info_mapa = DEPARTAMENTOS_PERU.get(depto, DEPARTAMENTOS_PERU["TODOS (Nacional)"])
    
    eventos = []
    sat_focos = escanear_nasa_firms()
    
    for f in sat_focos:
        if depto != "TODOS (Nacional)":
            b = info_mapa["bbox"]
            if not (b[0] <= f["lat"] <= b[2] and b[1] <= f["lon"] <= b[3]):
                continue
        eventos.append({
            "lat": f["lat"], "lon": f["lon"], "temp_c": "--", "humedad_pct": "--", "viento_kmh": "--",
            "ffdi_calculado": 100, "umbral_entrenado": "--", "eventos_bd": "--",
            "tipo_evento": "INCENDIO ACTIVO (NASA FIRMS)", 
            "diagnostico": f"🔥 SATÉLITE NASA: Foco de calor extremo detectado HOY (Potencia: {f['frp']} MW).",
            "color": "#ef4444", "icono": "🔥"
        })

    return jsonify({"status": "success", "vista_mapa": info_mapa, "eventos": eventos})

# MOTOR 2: PREDICCIÓN A 24H Y APRENDIZAJE
def obtener_umbral_ffdi_aprendido():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT AVG(ffdi_registrado), COUNT(*) FROM eventos_reales")
    row = c.fetchone()
    conn.close()
    n_eventos = row[1] if row else 0
    umbral_extremo = float(row[0]) if n_eventos > 0 else 24.0
    return max(12.0, round(umbral_extremo, 1)), n_eventos

def calcular_ffdi_base(t, hr, w):
    try:
        return 2.0 * math.exp(-0.450 + 0.987 * math.log(10.0) - 0.0345 * hr + 0.0338 * t + 0.0234 * w)
    except:
        return 0.0

def pronostico_24h_peor_escenario(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&forecast_days=2"
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json().get("hourly", {})
            temps = data.get("temperature_2m", [])[:24]
            hums = data.get("relative_humidity_2m", [])[:24]
            winds = data.get("wind_speed_10m", [])[:24]
            if temps and hums and winds:
                t_max = max(temps)
                idx = temps.index(t_max)
                return float(t_max), float(hums[idx]), float(max(winds))
    except:
        pass
    return 18.0, 30.0, 15.0

@app.route('/api/predecir_y_evaluar', methods=['POST'])
def predecir_y_evaluar():
    data = request.get_json()
    lat, lon = float(data["lat"]), float(data["lon"])
    
    t, hr, w = pronostico_24h_peor_escenario(lat, lon)
    ffdi_futuro = calcular_ffdi_base(t, hr, w)
    umbral_critico, total_eventos = obtener_umbral_ffdi_aprendido()
    
    if ffdi_futuro >= umbral_critico:
        diag = f"🔥 ALERTA PREDICCIÓN: FFDI superará el umbral entrenado ({umbral_critico}). Riesgo extremo de propagación MAÑANA."
        color, icono, tipo = "#ef4444", "🔥", "Peligro Crítico (Predictivo)"
    elif ffdi_futuro >= (umbral_critico * 0.6):
        diag = "⚠️ PELIGRO MODERADO: Condiciones propicias para que una quema se descontrole MAÑANA."
        color, icono, tipo = "#f97316", "⚠️", "Vigilancia Preventiva"
    else:
        diag = "🌲 SEGURO: La humedad pronosticada impedirá la propagación forestal MAÑANA."
        color, icono, tipo = "#10b981", "🌲", "Condición Estable"

    return jsonify({
        "lat": lat, "lon": lon, "temp_c": t, "humedad_pct": hr, "viento_kmh": w,
        "ffdi_calculado": round(ffdi_futuro, 1), "umbral_entrenado": umbral_critico,
        "eventos_bd": total_eventos, "tipo_evento": tipo, "diagnostico": diag,
        "color": color, "icono": icono
    })

@app.route('/api/entrenar_con_incendio_real', methods=['POST'])
def entrenar_con_incendio_real():
    data = request.get_json()
    lat, lon = float(data["lat"]), float(data["lon"])
    
    try:
        r = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m", timeout=4)
        c = r.json().get("current", {})
        t, hr, w = float(c.get("temperature_2m", 18)), float(c.get("relative_humidity_2m", 30)), float(c.get("wind_speed_10m", 15))
    except:
        t, hr, w = 18.0, 30.0, 15.0

    ffdi_real = calcular_ffdi_base(t, hr, w)
    fecha_peru = obtener_hora_peru().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO eventos_reales (fecha, lat, lon, temp_c, humedad_pct, viento_kmh, ffdi_registrado) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (fecha_peru, lat, lon, t, hr, w, ffdi_real))
    conn.commit()
    conn.close()

    nuevo_umbral, total = obtener_umbral_ffdi_aprendido()
    return jsonify({"status": "success", "nuevo_umbral": nuevo_umbral, "total_eventos": total})

@app.route('/')
@app.route('/movil')
def vista_movil():
    fecha_peru = obtener_hora_peru().strftime("%Y-%m-%d")
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0b132b">
    <title>ArcForest Sentinel | Predicción Científica v6.0</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 10px; display: flex; flex-direction: column; height: 100vh; overflow-y: hidden; }
        .header { text-align: center; margin-bottom: 6px; }
        .header h1 { font-size: 16px; color: #ff5722; font-weight: 800; margin-bottom: 2px; }
        .header p { font-size: 10px; color: #94a3b8; font-weight: bold; }
        .ia-bar { background: #1e293b; border: 1px solid #38bdf8; border-radius: 6px; padding: 6px; margin-bottom: 6px; font-size: 10px; display: flex; justify-content: space-between; }
        .ia-bar b { color: #00f5d4; }
        select { width: 100%; padding: 10px; border-radius: 6px; background: #1c2541; color: white; border: 1px solid #48cae4; font-size: 12px; margin-bottom: 6px; font-weight: bold; }
        .risk-box { text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 6px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 28px; font-weight: 900; color: #00f5d4; line-height: 1; margin: 4px 0; }
        .risk-diag { font-size: 10px; font-weight: bold; color: #f8fafc; line-height: 1.2; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 6px; }
        .metric-item { background: #1c2541; padding: 5px; border-radius: 6px; text-align: center; width: 32%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 8px; color: #94a3b8; display: block; }
        .metric-item strong { font-size: 12px; color: #48cae4; }
        #map { width: 100%; flex-grow: 1; border-radius: 10px; margin-bottom: 8px; border: 1px solid #3a506b; z-index: 1; }
        .btn-group { display: flex; gap: 6px; flex-direction: column; }
        .btn { padding: 12px; border: none; border-radius: 8px; font-size: 12px; font-weight: bold; cursor: pointer; text-align: center; color: white; }
        .btn-pred { background-color: #0284c7; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .btn-train { background-color: #d97706; }
        .badge-marker { display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 16px; box-shadow: 0 0 8px rgba(0,0,0,0.8); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ ArcForest Sentinel | Predictivo v6.0</h1>
        <p>Fecha del Sistema (Perú): __FECHA_PERU__</p>
    </div>

    <select id="deptoSelect" onchange="cargarNacional()">
        <option value="TODOS (Nacional)">🇵🇪 TODO EL PERÚ (Satélite NASA en Vivo)</option>
        <option value="Puno">📍 Puno (Verificar Lago Titicaca)</option>
        <option value="Cusco">📍 Cusco</option>
        <option value="Apurímac">📍 Apurímac</option>
        <option value="Junín">📍 Junín</option>
    </select>

    <div class="ia-bar">
        <span>🧠 <b>Eventos Estudiados:</b> <span id="nEv">3</span></span>
        <span>Umbral de Peligro Andino: <b id="umbIA">> 18.0 FFDI</b></span>
    </div>

    <div class="metrics">
        <div class="metric-item"><span>TEMP MAX (MAÑANA)</span><strong id="tempVal">-- °C</strong></div>
        <div class="metric-item"><span>HUM MIN (MAÑANA)</span><strong id="humVal">-- %</strong></div>
        <div class="metric-item"><span>RÁFAGA (MAÑANA)</span><strong id="vientoVal">-- km/h</strong></div>
    </div>

    <div class="risk-box" id="riskBox">
        <div class="risk-val" id="riskVal">-- FFDI</div>
        <div class="risk-diag" id="riskDiag">Cargando escáner satelital NASA...</div>
    </div>

    <div id="map"></div>

    <div class="btn-group">
        <button class="btn btn-pred" onclick="predecirManana()">🔍 1. Predecir Riesgo de MAÑANA aquí</button>
        <button class="btn btn-train" onclick="entrenarIA()">💾 2. Guardar Incendio Real Aquí (Entrenar IA)</button>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: false, tap: false }).setView([-9.5, -75.0], 5);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 }).addTo(map);

        let capaFocos = L.layerGroup().addTo(map);
        let puntoActual = null;
        let pinEvaluacion = null;

        function crearIcono(emoji, color) {
            return L.divIcon({
                className: 'badge-marker', html: `<div style="background-color:${color}; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff;">${emoji}</div>`,
                iconSize: [34, 34], iconAnchor: [17, 17]
            });
        }

        function actualizarPanel(d) {
            if(d.eventos_bd !== "--") document.getElementById('nEv').innerText = d.eventos_bd;
            if(d.umbral_entrenado !== "--") document.getElementById('umbIA').innerText = '> ' + d.umbral_entrenado + ' FFDI';
            
            document.getElementById('tempVal').innerText = (d.temp_c !== "--") ? d.temp_c + ' °C' : '--';
            document.getElementById('humVal').innerText = (d.humedad_pct !== "--") ? d.humedad_pct + ' %' : '--';
            document.getElementById('vientoVal').innerText = (d.viento_kmh !== "--") ? d.viento_kmh + ' km/h' : '--';
            
            document.getElementById('riskVal').innerText = (d.ffdi_calculado === 100) ? 'FUEGO ACTIVO' : d.ffdi_calculado + ' FFDI';
            document.getElementById('riskDiag').innerText = d.diagnostico;
            document.getElementById('riskVal').style.color = d.color;
            document.getElementById('riskBox').style.borderColor = d.color;
        }

        async function cargarNacional() {
            const depto = document.getElementById('deptoSelect').value;
            document.getElementById('riskDiag').innerText = "🛰️ Conectando con satélites NASA para incendios activos...";
            try {
                const res = await fetch(`/api/datos_nacionales?departamento=${encodeURIComponent(depto)}`);
                const data = await res.json();
                capaFocos.clearLayers();
                if(pinEvaluacion) map.removeLayer(pinEvaluacion);
                map.setView([data.vista_mapa.lat, data.vista_mapa.lon], data.vista_mapa.zoom);

                data.eventos.forEach(ev => {
                    const m = L.marker([ev.lat, ev.lon], { icon: crearIcono(ev.icono, ev.color) }).addTo(capaFocos);
                    m.on('click', () => actualizarPanel(ev));
                });
                
                if (data.eventos.length > 0) {
                    actualizarPanel(data.eventos[0]);
                } else {
                    document.getElementById('riskDiag').innerText = "✅ Satélites NASA no detectan incendios activos masivos hoy. Toca el mapa para predecir el riesgo de mañana.";
                    document.getElementById('riskVal').innerText = "-- FFDI";
                    document.getElementById('riskVal').style.color = "#00f5d4";
                    document.getElementById('riskBox').style.borderColor = "#48cae4";
                }
            } catch(e) {}
        }

        map.on('click', function(e) {
            puntoActual = { lat: e.latlng.lat, lon: e.latlng.lng };
            if(pinEvaluacion) map.removeLayer(pinEvaluacion);
            pinEvaluacion = L.marker([puntoActual.lat, puntoActual.lon], { icon: crearIcono('📍', '#2563eb') }).addTo(map);
            document.getElementById('riskDiag').innerText = "Punto marcado. Presiona 'Predecir Riesgo' para analizar.";
        });

        async function predecirManana() {
            if(!puntoActual) return alert("Primero toca una zona en el mapa.");
            document.getElementById('riskDiag').innerText = "Descargando pronóstico meteorológico a 24h...";
            try {
                const res = await fetch('/api/predecir_y_evaluar', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon })
                });
                const d = await res.json();
                actualizarPanel(d);
                if(pinEvaluacion) map.removeLayer(pinEvaluacion);
                pinEvaluacion = L.marker([d.lat, d.lon], { icon: crearIcono(d.icono, d.color) }).addTo(map).bindPopup(d.tipo_evento).openPopup();
            } catch(e) {}
        }

        async function entrenarIA() {
            if(!puntoActual) return alert("Toca en el mapa el lugar exacto del incendio real.");
            if(!confirm("¿Confirmas que hay un incendio forestal activo en este punto ahora mismo?")) return;
            
            document.getElementById('riskDiag').innerText = "Registrando en Base de Datos y recalibrando IA...";
            try {
                const res = await fetch('/api/entrenar_con_incendio_real', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon })
                });
                const d = await res.json();
                document.getElementById('nEv').innerText = d.total_eventos;
                document.getElementById('umbIA').innerText = '> ' + d.nuevo_umbral + ' FFDI';
                document.getElementById('riskDiag').innerText = "✅ Evento guardado. La IA aprendió el patrón atmosférico de este incendio.";
                
                if(pinEvaluacion) map.removeLayer(pinEvaluacion);
                pinEvaluacion = L.marker([puntoActual.lat, puntoActual.lon], { icon: crearIcono('🔥', '#ef4444') }).addTo(map);
            } catch(e) {}
        }
        
        // Ejecutar carga inicial al abrir la app
        cargarNacional();
    </script>
</body>
</html>
"""
    return html_content.replace("__FECHA_PERU__", fecha_peru)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)