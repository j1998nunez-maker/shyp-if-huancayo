import csv
import io
import sqlite3
import math
import requests
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "af_predictivo_cientifico.db"

# Delimitación precisa por departamentos (evita traslapes con Moquegua, costa o Bolivia)
DEPARTAMENTOS_PERU = {
    "TODOS (Nacional)": {"lat": -11.0, "lon": -75.0, "zoom": 5, "bbox": [-18.0, -81.0, -3.0, -68.8]},
    "Junín": {"lat": -11.95, "lon": -75.15, "zoom": 8, "bbox": [-12.65, -76.30, -10.70, -73.60]},
    "Puno": {"lat": -15.20, "lon": -70.05, "zoom": 8, "bbox": [-16.70, -70.85, -13.65, -69.15]},
    "Cusco": {"lat": -13.52, "lon": -71.97, "zoom": 8, "bbox": [-14.85, -73.40, -12.00, -70.60]},
    "Apurímac": {"lat": -13.85, "lon": -72.95, "zoom": 8, "bbox": [-14.70, -73.75, -13.20, -72.05]},
    "Ayacucho": {"lat": -13.16, "lon": -74.22, "zoom": 8, "bbox": [-15.30, -75.00, -12.20, -73.10]},
    "Huancavelica": {"lat": -12.78, "lon": -74.97, "zoom": 8, "bbox": [-14.00, -75.70, -12.00, -74.30]},
    "Áncash": {"lat": -9.53, "lon": -77.53, "zoom": 8, "bbox": [-10.70, -78.20, -8.10, -76.75]},
    "Huánuco": {"lat": -9.93, "lon": -76.24, "zoom": 8, "bbox": [-10.45, -76.95, -8.50, -74.60]},
    "Pasco": {"lat": -10.68, "lon": -76.25, "zoom": 8, "bbox": [-11.15, -76.65, -9.80, -74.60]},
    "Cajamarca": {"lat": -7.16, "lon": -78.51, "zoom": 8, "bbox": [-7.75, -79.40, -4.70, -77.75]},
    "Arequipa": {"lat": -15.80, "lon": -71.80, "zoom": 8, "bbox": [-16.65, -73.50, -14.70, -70.85]},
    "Amazonas": {"lat": -6.23, "lon": -77.87, "zoom": 8, "bbox": [-6.95, -78.70, -3.50, -77.15]},
    "San Martín": {"lat": -6.48, "lon": -76.36, "zoom": 8, "bbox": [-8.50, -77.40, -5.40, -75.50]},
    "Ucayali": {"lat": -8.38, "lon": -74.55, "zoom": 7, "bbox": [-11.20, -75.80, -7.20, -70.60]},
    "Madre de Dios": {"lat": -12.59, "lon": -69.19, "zoom": 7, "bbox": [-13.35, -71.50, -10.80, -68.85]}
}

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

def obtener_umbral_ffdi_aprendido():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT AVG(ffdi_registrado), COUNT(*) FROM eventos_reales")
    row = c.fetchone()
    conn.close()
    n_eventos = row[1] if row else 0
    umbral_extremo = float(row[0]) if n_eventos > 0 else 20.0
    return max(12.0, round(umbral_extremo, 1)), n_eventos

# Ecuación científica McArthur FFDI (Noble et al., 1980)
def calcular_ffdi_base(t, hr, w):
    try:
        ffdi = 2.0 * math.exp(-0.450 + 0.987 * math.log(10.0) - 0.0345 * hr + 0.0338 * t + 0.0234 * w)
        return round(max(0.5, ffdi), 1)
    except:
        return 1.0

# Pronóstico a 24h (extrae la hora más crítica de las próximas 24 horas)
def pronostico_24h_peor_escenario(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&forecast_days=2"
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json().get("hourly", {})
            temps = [x for x in data.get("temperature_2m", [])[:24] if x is not None]
            hums = [x for x in data.get("relative_humidity_2m", [])[:24] if x is not None]
            winds = [x for x in data.get("wind_speed_10m", [])[:24] if x is not None]
            if temps and hums and winds:
                t_max = max(temps)
                hr_min = min(hums)
                w_max = max(winds)
                return round(float(t_max), 1), round(float(hr_min), 1), round(float(w_max), 1)
    except:
        pass
    return 17.5, 34.0, 18.0

# Filtro geográfico para descartar puntos fuera del Perú (ej. Bolivia) y refinerías/fundiciones costeras (ej. Ilo)
def punto_valido_en_peru(lat, lon):
    # Descartar selva boliviana al este de Puno/Madre de Dios
    if lat < -12.5 and lon > -68.95:
        return False
    if -14.8 <= lat <= -12.5 and lon > -69.05:
        return False
    # Descartar fundición/complejo metalúrgico costero de Ilo (Moquegua)
    if -17.75 <= lat <= -17.35 and -71.50 <= lon <= -71.15:
        return False
    return True

def escanear_nasa_firms():
    focos_hoy = []
    urls = [
        "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_24h.csv",
        "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_South_America_24h.csv"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200 and len(resp.text) > 100:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    lat = float(row.get("latitude", 0))
                    lon = float(row.get("longitude", 0))
                    frp = float(row.get("frp", 0))
                    if -18.0 <= lat <= -3.0 and -81.0 <= lon <= -68.8:
                        if punto_valido_en_peru(lat, lon):
                            focos_hoy.append({
                                "lat": round(lat, 4),
                                "lon": round(lon, 4),
                                "frp": round(frp, 2),
                                "fecha": row.get("acq_date", "")
                            })
                if len(focos_hoy) > 0:
                    break
        except:
            continue
    return focos_hoy

# Clasificación Científica combinando FRP Satelital (MW) + Índice Meteorológico McArthur FFDI
def evaluar_foco_cientifico(lat, lon, frp_mw, umbral_critico, total_eventos):
    t, hr, w = pronostico_24h_peor_escenario(lat, lon)
    ffdi = calcular_ffdi_base(t, hr, w)

    if frp_mw > 0:
        # Es una anomalía térmica detectada por satélite
        if frp_mw >= 15.0 or (frp_mw >= 5.0 and ffdi >= umbral_critico * 0.75):
            tipo = "🔥 INCENDIO FORESTAL ACTIVO"
            diag = f"🔥 INCENDIO CONFIRMADO: Potencia térmica de {frp_mw} MW + Clima de propagación ({ffdi} FFDI)."
            color = "#ef4444"
            icono = "🔥"
        else:
            tipo = "♨️ QUEMA AGRÍCOLA / FOCALIZADA"
            diag = f"♨️ QUEMA MENOR ({frp_mw} MW): Baja energía radiativa (quema agrícola/pastizal) con FFDI de {ffdi}."
            color = "#f97316"
            icono = "♨️"
    else:
        # Es una evaluación predictiva a 24 horas en un punto sin fuego actual
        if ffdi >= umbral_critico:
            tipo = "🚨 RIESGO EXTREMO (24h)"
            diag = f"🔥 ANTICIPACIÓN 24H: FFDI ({ffdi}) superará el umbral crítico ({umbral_critico}). Peligro extremo si hay quema."
            color = "#ef4444"
            icono = "🔥"
        elif ffdi >= (umbral_critico * 0.6):
            tipo = "⚠️ RIESGO MODERADO (24h)"
            diag = f"⚠️ ANTICIPACIÓN 24H: FFDI proyectado de {ffdi}. Vigilancia ante posibles quemas agrícolas."
            color = "#f59e0b"
            icono = "⚠️"
        else:
            tipo = "🌲 CONDICIÓN SEGURA (24h)"
            diag = f"🌲 ANTICIPACIÓN 24H: FFDI bajo ({ffdi}). La humedad mínima ({hr}%) frenará el fuego."
            color = "#10b981"
            icono = "🌲"

    return {
        "lat": lat, "lon": lon,
        "temp_c": t, "humedad_pct": hr, "viento_kmh": w,
        "ffdi_calculado": ffdi, "frp_mw": frp_mw,
        "umbral_entrenado": umbral_critico, "eventos_bd": total_eventos,
        "tipo_evento": tipo, "diagnostico": diag,
        "color": color, "icono": icono
    }

@app.route('/api/datos_nacionales', methods=['GET'])
def datos_nacionales():
    depto = request.args.get('departamento', 'TODOS (Nacional)')
    info_mapa = DEPARTAMENTOS_PERU.get(depto, DEPARTAMENTOS_PERU["TODOS (Nacional)"])
    umbral_critico, total_eventos = obtener_umbral_ffdi_aprendido()

    sat_focos = escanear_nasa_firms()
    filtrados = []

    for f in sat_focos:
        if depto != "TODOS (Nacional)":
            b = info_mapa["bbox"]
            if not (b[0] <= f["lat"] <= b[2] and b[1] <= f["lon"] <= b[3]):
                continue
        filtrados.append(f)

    # Ordenar por mayor potencia térmica (FRP) y limitar a los 12 principales para respuesta rápida
    filtrados.sort(key=lambda x: x["frp"], reverse=True)
    muestra = filtrados[:12]

    eventos = []
    for f in muestra:
        ev = evaluar_foco_cientifico(f["lat"], f["lon"], f["frp"], umbral_critico, total_eventos)
        eventos.append(ev)

    # Si en el departamento seleccionado no hay focos NASA hoy, evaluar pronóstico 24h del centro forestal del departamento
    prediccion_base = None
    if len(eventos) == 0:
        prediccion_base = evaluar_foco_cientifico(info_mapa["lat"], info_mapa["lon"], 0.0, umbral_critico, total_eventos)

    return jsonify({
        "status": "success",
        "vista_mapa": info_mapa,
        "eventos": eventos,
        "prediccion_base": prediccion_base
    })

@app.route('/api/predecir_y_evaluar', methods=['POST'])
def predecir_y_evaluar():
    data = request.get_json()
    lat, lon = float(data["lat"]), float(data["lon"])
    umbral_critico, total_eventos = obtener_umbral_ffdi_aprendido()
    resultado = evaluar_foco_cientifico(lat, lon, 0.0, umbral_critico, total_eventos)
    return jsonify(resultado)

@app.route('/api/entrenar_con_incendio_real', methods=['POST'])
def entrenar_con_incendio_real():
    data = request.get_json()
    lat, lon = float(data["lat"]), float(data["lon"])

    t, hr, w = pronostico_24h_peor_escenario(lat, lon)
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
    <title>ArcForest Sentinel | Predictivo v7.0</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 10px; display: flex; flex-direction: column; height: 100vh; overflow-y: hidden; }
        .header { text-align: center; margin-bottom: 5px; }
        .header h1 { font-size: 16px; color: #ff5722; font-weight: 800; margin-bottom: 2px; }
        .header p { font-size: 10px; color: #94a3b8; font-weight: bold; }
        select { width: 100%; padding: 9px; border-radius: 6px; background: #1c2541; color: white; border: 1px solid #48cae4; font-size: 12px; margin-bottom: 6px; font-weight: bold; }
        .ia-bar { background: #1e293b; border: 1px solid #38bdf8; border-radius: 6px; padding: 6px; margin-bottom: 6px; font-size: 10px; display: flex; justify-content: space-between; }
        .ia-bar b { color: #00f5d4; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 6px; }
        .metric-item { background: #1c2541; padding: 5px; border-radius: 6px; text-align: center; width: 32%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 8px; color: #94a3b8; display: block; }
        .metric-item strong { font-size: 12px; color: #48cae4; }
        .risk-box { text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 6px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 24px; font-weight: 900; color: #00f5d4; line-height: 1.1; margin: 2px 0; }
        .risk-diag { font-size: 10px; font-weight: bold; color: #f8fafc; line-height: 1.25; }
        #map { width: 100%; flex-grow: 1; border-radius: 10px; margin-bottom: 8px; border: 1px solid #3a506b; z-index: 1; }
        .btn-group { display: flex; gap: 6px; flex-direction: column; }
        .btn { padding: 11px; border: none; border-radius: 8px; font-size: 12px; font-weight: bold; cursor: pointer; text-align: center; color: white; }
        .btn-pred { background-color: #0284c7; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .btn-train { background-color: #d97706; }
        .badge-marker { display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 16px; box-shadow: 0 0 8px rgba(0,0,0,0.8); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ ArcForest Sentinel | Predictivo v7.0</h1>
        <p>Fecha (Perú): __FECHA_PERU__ | Modelo: McArthur FFDI + NASA FRP</p>
    </div>

    <select id="deptoSelect" onchange="cargarNacional()">
        <option value="TODOS (Nacional)">🇵🇪 TODO EL PERÚ (Barrido Satelital Nacional)</option>
        <option value="Junín">📍 Junín (Huancayo / Selva Central)</option>
        <option value="Puno">📍 Puno (Cuenca Titicaca / Altiplano)</option>
        <option value="Cusco">📍 Cusco</option>
        <option value="Apurímac">📍 Apurímac (Abancay / Andahuaylas)</option>
        <option value="Ayacucho">📍 Ayacucho</option>
        <option value="Huancavelica">📍 Huancavelica</option>
        <option value="Áncash">📍 Áncash (Callejón de Huaylas / Conchucos)</option>
        <option value="Huánuco">📍 Huánuco</option>
        <option value="Pasco">📍 Pasco</option>
        <option value="Cajamarca">📍 Cajamarca</option>
        <option value="Arequipa">📍 Arequipa</option>
        <option value="Amazonas">📍 Amazonas</option>
        <option value="San Martín">📍 San Martín</option>
        <option value="Ucayali">📍 Ucayali</option>
        <option value="Madre de Dios">📍 Madre de Dios</option>
    </select>

    <div class="ia-bar">
        <span>🧠 <b>Eventos Entrenados:</b> <span id="nEv">3</span></span>
        <span>Umbral Crítico Andino: <b id="umbIA">> 18.0 FFDI</b></span>
    </div>

    <div class="metrics">
        <div class="metric-item"><span>TEMP MÁX (24h)</span><strong id="tempVal">-- °C</strong></div>
        <div class="metric-item"><span>HUM MÍN (24h)</span><strong id="humVal">-- %</strong></div>
        <div class="metric-item"><span>VIENTO MÁX (24h)</span><strong id="vientoVal">-- km/h</strong></div>
    </div>

    <div class="risk-box" id="riskBox">
        <div class="risk-val" id="riskVal">Analizando...</div>
        <div class="risk-diag" id="riskDiag">Consultando satélite NASA y atmósfera...</div>
    </div>

    <div id="map"></div>

    <div class="btn-group">
        <button class="btn btn-pred" onclick="predecirManana()">🔍 1. Predecir Riesgo 24h en Punto Seleccionado</button>
        <button class="btn btn-train" onclick="entrenarIA()">💾 2. Confirmar Incendio Real Aquí (Entrenar IA)</button>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: true, tap: false }).setView([-11.0, -75.0], 5);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 }).addTo(map);

        let capaFocos = L.layerGroup().addTo(map);
        let puntoActual = null;
        let pinEvaluacion = null;

        function crearIcono(emoji, color) {
            return L.divIcon({
                className: 'badge-marker',
                html: `<div style="background-color:${color}; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff;">${emoji}</div>`,
                iconSize: [34, 34], iconAnchor: [17, 17]
            });
        }

        function actualizarPanel(d) {
            puntoActual = { lat: d.lat, lon: d.lon };
            document.getElementById('nEv').innerText = d.eventos_bd;
            document.getElementById('umbIA').innerText = '> ' + d.umbral_entrenado + ' FFDI';

            document.getElementById('tempVal').innerText = d.temp_c + ' °C';
            document.getElementById('humVal').innerText = d.humedad_pct + ' %';
            document.getElementById('vientoVal').innerText = d.viento_kmh + ' km/h';

            document.getElementById('riskVal').innerText = `${d.tipo_evento} (${d.ffdi_calculado} FFDI)`;
            document.getElementById('riskDiag').innerText = d.diagnostico;
            document.getElementById('riskVal').style.color = d.color;
            document.getElementById('riskBox').style.borderColor = d.color;
        }

        async function cargarNacional() {
            const depto = document.getElementById('deptoSelect').value;
            document.getElementById('riskDiag').innerText = "🛰️ Cruzando anomalías térmicas NASA con pronóstico meteorológico Open-Meteo...";
            try {
                const res = await fetch(`/api/datos_nacionales?departamento=${encodeURIComponent(depto)}`);
                const data = await res.json();
                capaFocos.clearLayers();
                if(pinEvaluacion) map.removeLayer(pinEvaluacion);
                map.setView([data.vista_mapa.lat, data.vista_mapa.lon], data.vista_mapa.zoom);

                if (data.eventos.length > 0) {
                    data.eventos.forEach(ev => {
                        const m = L.marker([ev.lat, ev.lon], { icon: crearIcono(ev.icono, ev.color) })
                            .addTo(capaFocos)
                            .bindPopup(`<b>${ev.tipo_evento}</b><br>Coord: ${ev.lat}, ${ev.lon}<br>Temp: ${ev.temp_c}°C | HR: ${ev.humedad_pct}% | Viento: ${ev.viento_kmh} km/h`);
                        m.on('click', () => actualizarPanel(ev));
                    });
                    actualizarPanel(data.eventos[0]);
                } else if (data.prediccion_base) {
                    const pb = data.prediccion_base;
                    actualizarPanel(pb);
                    pinEvaluacion = L.marker([pb.lat, pb.lon], { icon: crearIcono(pb.icono, pb.color) })
                        .addTo(capaFocos)
                        .bindPopup(`<b>Pronóstico 24h (${depto})</b><br>${pb.diagnostico}`).openPopup();
                }
            } catch(e) {}
        }

        map.on('click', function(e) {
            puntoActual = { lat: e.latlng.lat, lon: e.latlng.lng };
            if(pinEvaluacion) map.removeLayer(pinEvaluacion);
            pinEvaluacion = L.marker([puntoActual.lat, puntoActual.lon], { icon: crearIcono('📍', '#2563eb') }).addTo(map);
            document.getElementById('riskDiag').innerText = `📍 Coordenada (${puntoActual.lat.toFixed(3)}, ${puntoActual.lon.toFixed(3)}) marcada. Pulsa el botón azul (1) para predecir.`;
        });

        async function predecirManana() {
            if(!puntoActual) return alert("Primero toca un cerro en el mapa.");
            document.getElementById('riskDiag').innerText = "Calculando índice McArthur FFDI para las próximas 24 horas...";
            try {
                const res = await fetch('/api/predecir_y_evaluar', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon })
                });
                const d = await res.json();
                actualizarPanel(d);
                if(pinEvaluacion) map.removeLayer(pinEvaluacion);
                pinEvaluacion = L.marker([d.lat, d.lon], { icon: crearIcono(d.icono, d.color) })
                    .addTo(map)
                    .bindPopup(`<b>${d.tipo_evento}</b><br>FFDI: ${d.ffdi_calculado}`).openPopup();
            } catch(e) {}
        }

        async function entrenarIA() {
            if(!puntoActual) return alert("Toca primero en el mapa el lugar del incendio.");
            if(!confirm("¿Confirmas que hay un incendio forestal real en este punto? Se guardará su firma climática para entrenar el umbral FFDI.")) return;

            document.getElementById('riskDiag').innerText = "Guardando firma climática y recalibrando umbral FFDI...";
            try {
                const res = await fetch('/api/entrenar_con_incendio_real', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon })
                });
                const d = await res.json();
                document.getElementById('nEv').innerText = d.total_eventos;
                document.getElementById('umbIA').innerText = '> ' + d.nuevo_umbral + ' FFDI';
                document.getElementById('riskDiag').innerText = `✅ IA Recalibrada (${d.total_eventos} eventos). Nuevo umbral crítico andino: ${d.nuevo_umbral} FFDI.`;
            } catch(e) {}
        }

        cargarNacional();
    </script>
</body>
</html>
"""
    return html_content.replace("__FECHA_PERU__", fecha_peru)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)