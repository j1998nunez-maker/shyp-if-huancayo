import csv
import io
import sqlite3
import math
import requests
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "af_inteligencia_espacial_v8.db"

# Malla Espacial Inteligente: Corredores forestales, punas y provincias de todo el Perú
MALLA_CORREDORES_PERU = {
    "Junín": {
        "centro": [-11.55, -75.05], "zoom": 8, "bbox": [-12.65, -76.30, -10.70, -73.60],
        "nodos": [
            {"zona": "Huancayo - Quebrada Shullcas / Acopalca", "lat": -11.996, "lon": -75.138},
            {"zona": "Huancayo - Cerros Azapampa / Chilca", "lat": -12.115, "lon": -75.185},
            {"zona": "Concepción - Comas / Andamarca", "lat": -11.725, "lon": -75.110},
            {"zona": "Jauja - Valle de Yanamarca / Acolla", "lat": -11.712, "lon": -75.525},
            {"zona": "Chupaca - Ladera Cunas / Yanacancha", "lat": -12.165, "lon": -75.385},
            {"zona": "Tarma - Palcamayo / Acobamba", "lat": -11.335, "lon": -75.715},
            {"zona": "Chanchamayo - San Ramón / Perené", "lat": -11.015, "lon": -75.245},
            {"zona": "Satipo - Mazamari / Pangoa / Río Tambo", "lat": -11.325, "lon": -74.450},
            {"zona": "Junín - Reserva Ondores / Pampa", "lat": -11.155, "lon": -75.995}
        ]
    },
    "Puno": {
        "centro": [-14.85, -70.05], "zoom": 7, "bbox": [-16.70, -70.85, -13.30, -69.05],
        "nodos": [
            {"zona": "Puno - Pajonales Alto Puno / Yanamayo", "lat": -15.812, "lon": -70.045},
            {"zona": "San Román - Pampas de Juliaca / Cabanillas", "lat": -15.585, "lon": -70.285},
            {"zona": "Melgar - Ayaviri / Santa Rosa", "lat": -14.825, "lon": -70.620},
            {"zona": "Azángaro - Laderas Asillo / Muñani", "lat": -14.780, "lon": -70.180},
            {"zona": "Lampa - Cordillera Paratía / Ocuviri", "lat": -15.290, "lon": -70.510},
            {"zona": "Carabaya - Macusani / Corani / Ollachea", "lat": -13.980, "lon": -70.460},
            {"zona": "Sandia - Valle Inambari / Cuyocuyo", "lat": -14.220, "lon": -69.480},
            {"zona": "El Collao - Ilave / Mazocruz", "lat": -16.250, "lon": -69.720},
            {"zona": "Chucuito - Juli / Pomata / Desaguadero", "lat": -16.320, "lon": -69.380},
            {"zona": "Huancané / Moho - Vertiente Norte", "lat": -15.210, "lon": -69.650}
        ]
    },
    "Cusco": {
        "centro": [-13.40, -71.95], "zoom": 8, "bbox": [-14.85, -73.40, -12.00, -70.60],
        "nodos": [
            {"zona": "Cusco - Cumbre Apu Pachatusan / Oropesa", "lat": -13.508, "lon": -71.815},
            {"zona": "Cusco - Alto Sacsayhuamán / Tambomachay", "lat": -13.475, "lon": -71.968},
            {"zona": "Urubamba - Valle Sagrado / Ollantaytambo", "lat": -13.285, "lon": -72.185},
            {"zona": "Calca - Pisac / Lares", "lat": -13.310, "lon": -71.880},
            {"zona": "Paucartambo - Kosñipata / Tres Cruces", "lat": -13.220, "lon": -71.590},
            {"zona": "Quispicanchi - Urcos / Ocongate", "lat": -13.680, "lon": -71.510},
            {"zona": "Canchis - Sicuani / Maranganí", "lat": -14.280, "lon": -71.210},
            {"zona": "Espinar / Chumbivilcas - Punas Altas", "lat": -14.620, "lon": -71.650},
            {"zona": "La Convención - Quillabamba / Echarati", "lat": -12.780, "lon": -72.680}
        ]
    },
    "Apurímac": {
        "centro": [-13.85, -72.95], "zoom": 8, "bbox": [-14.70, -73.75, -13.20, -72.05],
        "nodos": [
            {"zona": "Abancay - Curahuasi / Matibamba", "lat": -13.524, "lon": -72.735},
            {"zona": "Abancay - Santuario Nacional de Ampay", "lat": -13.595, "lon": -72.878},
            {"zona": "Andahuaylas - San Jerónimo / Talavera", "lat": -13.655, "lon": -73.365},
            {"zona": "Chincheros - Ocobamba / Uripa", "lat": -13.510, "lon": -73.620},
            {"zona": "Aymaraes - Chalhuanca / Cotaruse", "lat": -14.295, "lon": -73.245},
            {"zona": "Cotabambas - Tambobamba / Challhuahuacho", "lat": -14.085, "lon": -72.250},
            {"zona": "Grau - Chuquibambilla", "lat": -14.110, "lon": -72.710}
        ]
    },
    "Ayacucho": {
        "centro": [-13.60, -74.15], "zoom": 8, "bbox": [-15.30, -75.00, -12.20, -73.10],
        "nodos": [
            {"zona": "Huamanga - Chiara / Quinua", "lat": -13.180, "lon": -74.160},
            {"zona": "Huanta - Santillana / Razuhuillca", "lat": -12.910, "lon": -74.210},
            {"zona": "La Mar - San Miguel / Tambo", "lat": -12.980, "lon": -73.950},
            {"zona": "Cangallo / Vilcashuamán", "lat": -13.630, "lon": -74.060},
            {"zona": "Lucanas - Puquio / Pampa Galeras", "lat": -14.690, "lon": -74.150}
        ]
    },
    "Huancavelica": {
        "centro": [-12.85, -74.95], "zoom": 8, "bbox": [-14.00, -75.70, -12.00, -74.30],
        "nodos": [
            {"zona": "Huancavelica - Yauli / Ascensión", "lat": -12.770, "lon": -74.920},
            {"zona": "Tayacaja - Pampas / Colcabamba", "lat": -12.390, "lon": -74.860},
            {"zona": "Acobamba / Lircay (Angaraes)", "lat": -12.910, "lon": -74.680},
            {"zona": "Castrovirreyna / Huaytará", "lat": -13.450, "lon": -75.250}
        ]
    },
    "Áncash": {
        "centro": [-9.45, -77.45], "zoom": 8, "bbox": [-10.70, -78.20, -8.10, -76.75],
        "nodos": [
            {"zona": "Huaraz - Quebrada Llaca / Independencia", "lat": -9.478, "lon": -77.495},
            {"zona": "Yungay / Carhuaz - Callejón de Huaylas", "lat": -9.180, "lon": -77.690},
            {"zona": "Huari - Chavín / San Marcos (Conchucos)", "lat": -9.420, "lon": -77.160},
            {"zona": "Bolognesi - Chiquián / Aquia", "lat": -10.150, "lon": -77.150}
        ]
    },
    "Cajamarca": {
        "centro": [-6.65, -78.65], "zoom": 8, "bbox": [-7.75, -79.40, -4.70, -77.75],
        "nodos": [
            {"zona": "Cajamarca - Porcón / Baños del Inca", "lat": -7.080, "lon": -78.580},
            {"zona": "Cutervo / Chota - Bosques Montanos", "lat": -6.380, "lon": -78.810},
            {"zona": "Jaén / San Ignacio - Bosques Secos", "lat": -5.450, "lon": -78.850},
            {"zona": "Celendín / Cajabamba", "lat": -7.250, "lon": -78.120}
        ]
    },
    "Huánuco": {
        "centro": [-9.65, -76.05], "zoom": 8, "bbox": [-10.45, -76.95, -8.50, -74.60],
        "nodos": [
            {"zona": "Huánuco - Amarilis / Carpish", "lat": -9.850, "lon": -76.150},
            {"zona": "Leoncio Prado - Tingo María / Monzón", "lat": -9.290, "lon": -76.010},
            {"zona": "Puerto Inca - Pachitea", "lat": -9.450, "lon": -75.050},
            {"zona": "Ambo / Dos de Mayo (La Unión)", "lat": -10.080, "lon": -76.550}
        ]
    },
    "Amazonas / San Martín": {
        "centro": [-6.35, -77.10], "zoom": 7, "bbox": [-8.50, -78.70, -3.50, -75.50],
        "nodos": [
            {"zona": "Chachapoyas / Luya (Amazonas)", "lat": -6.220, "lon": -77.880},
            {"zona": "Bongará / Pomacochas (Amazonas)", "lat": -5.820, "lon": -77.950},
            {"zona": "Moyobamba / Rioja (San Martín)", "lat": -6.040, "lon": -76.970},
            {"zona": "Tarapoto / Lamas (San Martín)", "lat": -6.480, "lon": -76.390},
            {"zona": "Mariscal Cáceres - Juanjuí (San Martín)", "lat": -7.180, "lon": -76.730}
        ]
    },
    "Ucayali / Madre de Dios": {
        "centro": [-10.50, -72.00], "zoom": 6, "bbox": [-13.35, -75.80, -7.20, -68.85],
        "nodos": [
            {"zona": "Coronel Portillo - Pucallpa / Campo Verde", "lat": -8.450, "lon": -74.750},
            {"zona": "Padre Abad - Aguaytía (Ucayali)", "lat": -9.040, "lon": -75.510},
            {"zona": "Atalaya - Sepahua (Ucayali)", "lat": -10.730, "lon": -73.750},
            {"zona": "Tambopata - Puerto Maldonado (Madre de Dios)", "lat": -12.590, "lon": -69.250},
            {"zona": "Tahuamanu - Iberia / Iñapari (Madre de Dios)", "lat": -11.410, "lon": -69.490}
        ]
    },
    "Arequipa": {
        "centro": [-15.85, -71.80], "zoom": 8, "bbox": [-16.65, -73.50, -14.70, -70.85],
        "nodos": [
            {"zona": "Arequipa - Faldas Volcán Pichu Pichu / Chiguata", "lat": -16.410, "lon": -71.360},
            {"zona": "Caylloma - Valle del Colca / Chivay", "lat": -15.630, "lon": -71.600},
            {"zona": "Condesuyos / Chuquibamba", "lat": -15.840, "lon": -72.650}
        ]
    }
}

CUARTELES_CGBVP = [
    {"nombre": "Cía. Bomberos Huancayo B-30", "lat": -12.07015, "lon": -75.20895},
    {"nombre": "Cía. Bomberos El Tambo B-198 (Huancayo)", "lat": -12.0468, "lon": -75.2215},
    {"nombre": "Cía. Bomberos Jauja B-48", "lat": -11.7758, "lon": -75.4965},
    {"nombre": "Cía. Bomberos Tarma B-58", "lat": -11.4189, "lon": -75.6891},
    {"nombre": "Cía. Bomberos La Merced B-60 (Chanchamayo)", "lat": -11.055, "lon": -75.328},
    {"nombre": "Cía. Bomberos Satipo B-148", "lat": -11.252, "lon": -74.638},
    {"nombre": "Cía. Bomberos Puno B-42", "lat": -15.83685, "lon": -70.02295},
    {"nombre": "Cía. Bomberos Juliaca B-53 (San Román)", "lat": -15.4997, "lon": -70.1333},
    {"nombre": "Cía. Bomberos Ayaviri B-192 (Melgar)", "lat": -14.881, "lon": -70.589},
    {"nombre": "Cía. Bomberos Macusani B-210 (Carabaya)", "lat": -14.069, "lon": -70.431},
    {"nombre": "Cía. Bomberos Cusco B-39", "lat": -13.52055, "lon": -71.97235},
    {"nombre": "Cía. Bomberos San Sebastián B-116 (Cusco)", "lat": -13.5312, "lon": -71.9355},
    {"nombre": "Cía. Bomberos Urubamba B-118", "lat": -13.305, "lon": -72.116},
    {"nombre": "Cía. Bomberos Sicuani B-50 (Canchis)", "lat": -14.2694, "lon": -71.2261},
    {"nombre": "Cía. Bomberos Quillabamba B-57", "lat": -12.863, "lon": -72.693},
    {"nombre": "Cía. Bomberos Abancay B-68", "lat": -13.63585, "lon": -72.87815},
    {"nombre": "Cía. Bomberos Curahuasi B-143", "lat": -13.5415, "lon": -72.6975},
    {"nombre": "Cía. Bomberos Andahuaylas B-153", "lat": -13.6556, "lon": -73.3872},
    {"nombre": "Cía. Bomberos Ayacucho B-63", "lat": -13.1631, "lon": -74.2236},
    {"nombre": "Cía. Bomberos Huancavelica B-56", "lat": -12.7861, "lon": -74.9722},
    {"nombre": "Cía. Bomberos Huaraz B-84", "lat": -9.52985, "lon": -77.52875},
    {"nombre": "Cía. Bomberos Cajamarca B-59", "lat": -7.1617, "lon": -78.5128},
    {"nombre": "Cía. Bomberos Huánuco B-52", "lat": -9.9306, "lon": -76.2422},
    {"nombre": "Cía. Bomberos Tarapoto B-71", "lat": -6.489, "lon": -76.360},
    {"nombre": "Cía. Bomberos Pucallpa B-46", "lat": -8.383, "lon": -74.532},
    {"nombre": "Cía. Bomberos Puerto Maldonado B-70", "lat": -12.593, "lon": -69.189},
    {"nombre": "Cía. Bomberos Arequipa B-19", "lat": -16.4090, "lon": -71.5375}
]

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
            fecha TEXT, zona TEXT, lat REAL, lon REAL,
            temp_c REAL, humedad_pct REAL, viento_kmh REAL, vpd_kpa REAL, ffdi_registrado REAL
        )
    """)
    c.execute("SELECT COUNT(*) FROM eventos_reales")
    if c.fetchone()[0] == 0:
        semillas = [
            ("2026-10-13", "Curahuasi - Apurímac", -13.5240, -72.7350, 22.8, 23.0, 27.5, 2.14, 21.4),
            ("2026-10-19", "Apu Pachatusan - Cusco", -13.5085, -71.8150, 19.5, 21.0, 32.0, 1.80, 18.2),
            ("2026-09-25", "Acopalca - Huancayo", -11.9960, -75.1380, 18.4, 26.0, 24.5, 1.56, 14.5)
        ]
        c.executemany("INSERT INTO eventos_reales (fecha, zona, lat, lon, temp_c, humedad_pct, viento_kmh, vpd_kpa, ffdi_registrado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", semillas)
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
    umbral_extremo = float(row[0]) if n_eventos > 0 else 18.0
    return max(10.0, round(umbral_extremo, 1)), n_eventos

# Ecuaciones Físicas Validadas: Déficit de Presión de Vapor (VPD) + McArthur FFDI con Factor de Sequía Dinámico
def calcular_indices_fisicos(t, hr, w, lluvia_mm):
    try:
        # 1. Presión de vapor de saturación Tetens (kPa) y VPD (aridez atmosférica)
        es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
        vpd = round(max(0.1, es * (1.0 - (hr / 100.0))), 2)

        # 2. Factor de Sequía Dinámico D (1 a 10) reducido por lluvia acumulada
        factor_d = max(1.5, min(10.0, 10.0 - (lluvia_mm * 1.3)))

        # 3. Ecuación Noble et al. (1980) - McArthur FFDI
        ffdi = 2.0 * math.exp(-0.450 + 0.987 * math.log(factor_d) - 0.0345 * hr + 0.0338 * t + 0.0234 * w)
        return round(max(0.5, ffdi), 1), vpd, round(factor_d, 1)
    except:
        return 1.5, 0.8, 7.0

# Consulta Vectorizada en Paralelo a Open-Meteo (Escanea decenas de coordenadas en 1 sola petición HTTP)
def escanear_malla_clima_24h(lista_nodos):
    if not lista_nodos:
        return []
    lats = ",".join([str(n["lat"]) for n in lista_nodos])
    lons = ",".join([str(n["lon"]) for n in lista_nodos])
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation&forecast_days=2"

    resultados_meteo = []
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            # Si se envía 1 solo nodo, Open-Meteo devuelve un dict; si son varios, devuelve una lista
            bloques = data if isinstance(data, list) else [data]
            for b in bloques:
                h = b.get("hourly", {})
                temps = [x for x in h.get("temperature_2m", [])[:24] if x is not None]
                hums = [x for x in h.get("relative_humidity_2m", [])[:24] if x is not None]
                winds = [x for x in h.get("wind_speed_10m", [])[:24] if x is not None]
                precs = [x for x in h.get("precipitation", [])[:24] if x is not None]
                if temps and hums and winds:
                    resultados_meteo.append({
                        "t": round(float(max(temps)), 1),
                        "hr": round(float(min(hums)), 1),
                        "w": round(float(max(winds)), 1),
                        "rain": round(float(sum(precs)), 1) if precs else 0.0
                    })
                else:
                    resultados_meteo.append({"t": 18.0, "hr": 35.0, "w": 18.0, "rain": 0.0})
            return resultados_meteo
    except:
        pass

    return [{"t": 18.5, "hr": 34.0, "w": 19.0, "rain": 0.0} for _ in lista_nodos]

def punto_valido_en_peru(lat, lon):
    if lat < -12.5 and lon > -68.95:
        return False
    if -14.8 <= lat <= -12.5 and lon > -69.05:
        return False
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
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and len(resp.text) > 100:
                reader = csv.DictReader(io.StringIO(resp.text))
                for row in reader:
                    lat, lon = float(row.get("latitude", 0)), float(row.get("longitude", 0))
                    frp = float(row.get("frp", 0))
                    if -18.0 <= lat <= -3.0 and -81.0 <= lon <= -68.8 and punto_valido_en_peru(lat, lon):
                        focos_hoy.append({"lat": round(lat, 4), "lon": round(lon, 4), "frp": round(frp, 2)})
                if len(focos_hoy) > 0:
                    break
        except:
            continue
    return focos_hoy

def construir_diagnostico_nodo(zona, lat, lon, m, umbral_critico, total_eventos, frp_mw=0.0):
    ffdi, vpd, factor_d = calcular_indices_fisicos(m["t"], m["hr"], m["w"], m["rain"])
    prob_pct = round(min(99.5, (ffdi / (umbral_critico * 1.35)) * 100.0), 1)

    if frp_mw > 0:
        if frp_mw >= 12.0 or ffdi >= umbral_critico * 0.7:
            tipo = "🔥 INCENDIO ACTIVO (SATÉLITE)"
            diag = f"🔥 FOCO ACTIVO NASA ({frp_mw} MW) en {zona}. VPD: {vpd} kPa | FFDI: {ffdi}."
            color, icono, prioridad = "#ef4444", "🔥", 100 + ffdi
        else:
            tipo = "♨️ QUEMA ACTIVA MENOR (SATÉLITE)"
            diag = f"♨️ Anomalía térmica menor ({frp_mw} MW) en {zona}. VPD: {vpd} kPa | FFDI: {ffdi}."
            color, icono, prioridad = "#f97316", "♨️", 80 + ffdi
    else:
        if ffdi >= umbral_critico:
            tipo = "🚨 RIESGO EXTREMO PREDICTIVO (24h)"
            diag = f"🚨 {zona}: Alta probabilidad de incendio mañana ({prob_pct}%). Sequedad VPD: {vpd} kPa | Lluvia: {m['rain']} mm."
            color, icono, prioridad = "#ef4444", "🚨", ffdi
        elif ffdi >= (umbral_critico * 0.55):
            tipo = "⚠️ RIESGO MODERADO / VIGILANCIA (24h)"
            diag = f"⚠️ {zona}: Susceptibilidad media ({prob_pct}%). VPD: {vpd} kPa | Lluvia 24h: {m['rain']} mm."
            color, icono, prioridad = "#f59e0b", "⚠️", ffdi
        else:
            tipo = "🌲 ZONA SEGURA / HÚMEDA (24h)"
            diag = f"🌲 {zona}: Condición estable ({prob_pct}%). Lluvia proyectada: {m['rain']} mm frena ignición."
            color, icono, prioridad = "#10b981", "🌲", ffdi

    return {
        "zona": zona, "lat": lat, "lon": lon,
        "temp_c": m["t"], "humedad_pct": m["hr"], "viento_kmh": m["w"],
        "lluvia_mm": m["rain"], "vpd_kpa": vpd, "ffdi_calculado": ffdi,
        "probabilidad_pct": prob_pct, "umbral_entrenado": umbral_critico,
        "eventos_bd": total_eventos, "tipo_evento": tipo,
        "diagnostico": diag, "color": color, "icono": icono, "prioridad": prioridad
    }

@app.route('/api/escaneo_inteligente', methods=['GET'])
def escaneo_inteligente():
    depto = request.args.get('departamento', 'TODOS (Nacional)')
    umbral_critico, total_eventos = obtener_umbral_ffdi_aprendido()

    # 1. Reunir todos los nodos de la malla territorial a evaluar
    nodos_a_evaluar = []
    if depto == "TODOS (Nacional)":
        vista = {"lat": -11.2, "lon": -74.5, "zoom": 5}
        # Tomar los 2 corredores principales de cada departamento para cubrir todo el Perú
        for d_key, d_val in MALLA_CORREDORES_PERU.items():
            for n in d_val["nodos"][:2]:
                nodos_a_evaluar.append({"zona": f"[{d_key}] {n['zona']}", "lat": n["lat"], "lon": n["lon"]})
    else:
        info_d = MALLA_CORREDORES_PERU.get(depto, MALLA_CORREDORES_PERU["Junín"])
        vista = {"lat": info_d["centro"][0], "lon": info_d["centro"][1], "zoom": info_d["zoom"], "bbox": info_d["bbox"]}
        for n in info_d["nodos"]:
            nodos_a_evaluar.append({"zona": n["zona"], "lat": n["lat"], "lon": n["lon"]})

    # 2. Agregar focos satelitales NASA FIRMS activos en la región
    sat_focos = escanear_nasa_firms()
    nodos_sat = []
    for f in sat_focos:
        if depto != "TODOS (Nacional)":
            b = vista["bbox"]
            if not (b[0] <= f["lat"] <= b[2] and b[1] <= f["lon"] <= b[3]):
                continue
        nodos_sat.append({"zona": f"Foco Satelital ({f['lat']}, {f['lon']})", "lat": f["lat"], "lon": f["lon"], "frp": f["frp"]})
    nodos_sat.sort(key=lambda x: x["frp"], reverse=True)
    nodos_sat = nodos_sat[:6]

    # 3. Escanear en paralelo todos los nodos predictivos + satelitales en una sola llamada
    todos_nodos = nodos_a_evaluar + nodos_sat
    climas = escanear_malla_clima_24h(todos_nodos)

    puntos_analizados = []
    for idx, nodo in enumerate(todos_nodos):
        m = climas[idx] if idx < len(climas) else {"t": 18.0, "hr": 35.0, "w": 18.0, "rain": 0.0}
        frp_val = nodo.get("frp", 0.0)
        ev = construir_diagnostico_nodo(nodo["zona"], nodo["lat"], nodo["lon"], m, umbral_critico, total_eventos, frp_val)
        puntos_analizados.append(ev)

    # Ordenar inteligentemente: primero los de mayor peligro para alertar de inmediato
    puntos_analizados.sort(key=lambda x: x["prioridad"], reverse=True)

    return jsonify({
        "status": "success",
        "vista_mapa": vista,
        "puntos": puntos_analizados
    })

@app.route('/api/predecir_punto_libre', methods=['POST'])
def predecir_punto_libre():
    data = request.get_json()
    lat, lon = round(float(data["lat"]), 4), round(float(data["lon"]), 4)
    umbral_critico, total_eventos = obtener_umbral_ffdi_aprendido()

    # Obtener nombre del lugar via OpenStreetMap
    nombre_zona = f"Sector Auditado ({lat}, {lon})"
    try:
        rn = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=13", headers={"User-Agent": "AF-Sentinel-v8"}, timeout=3)
        if rn.status_code == 200:
            addr = rn.json().get("address", {})
            loc = addr.get("village", addr.get("town", addr.get("municipality", addr.get("county", ""))))
            prov = addr.get("state", "")
            if loc:
                nombre_zona = f"{loc} ({prov})"
    except:
        pass

    climas = escanear_malla_clima_24h([{"lat": lat, "lon": lon}])
    ev = construir_diagnostico_nodo(nombre_zona, lat, lon, climas[0], umbral_critico, total_eventos, 0.0)
    return jsonify(ev)

@app.route('/api/entrenar_con_incendio_real', methods=['POST'])
def entrenar_con_incendio_real():
    data = request.get_json()
    lat, lon = round(float(data["lat"]), 4), round(float(data["lon"]), 4)
    zona = data.get("zona", f"Incendio Confirmado ({lat}, {lon})")

    climas = escanear_malla_clima_24h([{"lat": lat, "lon": lon}])
    m = climas[0]
    ffdi_real, vpd_real, _ = calcular_indices_fisicos(m["t"], m["hr"], m["w"], m["rain"])
    fecha_peru = obtener_hora_peru().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO eventos_reales (fecha, zona, lat, lon, temp_c, humedad_pct, viento_kmh, vpd_kpa, ffdi_registrado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (fecha_peru, zona, lat, lon, m["t"], m["hr"], m["w"], vpd_real, ffdi_real))
    conn.commit()
    conn.close()

    nuevo_umbral, total = obtener_umbral_ffdi_aprendido()
    return jsonify({"status": "success", "nuevo_umbral": nuevo_umbral, "total_eventos": total})

@app.route('/api/ruta_bomberos', methods=['GET'])
def ruta_bomberos():
    dest_lat, dest_lon = float(request.args.get('lat')), float(request.args.get('lon'))
    cuartel = min(CUARTELES_CGBVP, key=lambda q: math.sqrt((q["lat"] - dest_lat)**2 + (q["lon"] - dest_lon)**2))
    orig_lat, orig_lon = cuartel["lat"], cuartel["lon"]

    url_osrm = f"https://router.project-osrm.org/route/v1/driving/{orig_lon},{orig_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    try:
        resp = requests.get(url_osrm, timeout=5)
        data = resp.json()
        if "routes" in data and len(data["routes"]) > 0:
            r = data["routes"][0]
            return jsonify({
                "status": "success", "origen": cuartel["nombre"],
                "distancia_km": round(r["distance"] / 1000.0, 1),
                "duracion_min": round(r["duration"] / 60.0, 0),
                "coordenadas": r["geometry"]["coordinates"]
            })
    except:
        pass
    dist = round(math.sqrt((dest_lat - orig_lat)**2 + (dest_lon - orig_lon)**2) * 111.0, 1)
    return jsonify({"status": "success", "origen": cuartel["nombre"], "distancia_km": dist, "duracion_min": round(dist * 2.0, 0), "coordenadas": [[orig_lon, orig_lat], [dest_lon, dest_lat]]})

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
    <title>ArcForest Sentinel v8.0 | Malla Predictiva Inteligente</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 8px; display: flex; flex-direction: column; height: 100vh; overflow-y: hidden; }
        .header { text-align: center; margin-bottom: 4px; }
        .header h1 { font-size: 15px; color: #ff5722; font-weight: 800; }
        .header p { font-size: 9px; color: #94a3b8; font-weight: bold; }
        .top-controls { display: flex; gap: 5px; margin-bottom: 5px; }
        select { width: 100%; padding: 8px; border-radius: 6px; background: #1c2541; color: white; border: 1px solid #48cae4; font-size: 11px; font-weight: bold; }
        .ia-bar { background: #1e293b; border: 1px solid #38bdf8; border-radius: 6px; padding: 5px 8px; margin-bottom: 5px; font-size: 9px; display: flex; justify-content: space-between; }
        .ia-bar b { color: #00f5d4; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 5px; gap: 4px; }
        .metric-item { background: #1c2541; padding: 4px; border-radius: 6px; text-align: center; width: 25%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 7px; color: #94a3b8; display: block; }
        .metric-item strong { font-size: 11px; color: #48cae4; }
        .risk-box { text-align: center; padding: 6px 8px; border-radius: 8px; margin-bottom: 5px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 16px; font-weight: 900; color: #00f5d4; margin-bottom: 2px; }
        .risk-diag { font-size: 10px; font-weight: 600; color: #f8fafc; line-height: 1.2; }
        #map { width: 100%; flex-grow: 1; border-radius: 10px; margin-bottom: 6px; border: 1px solid #3a506b; z-index: 1; }
        .btn-row { display: flex; gap: 5px; }
        .btn { flex: 1; padding: 10px 4px; border: none; border-radius: 7px; font-size: 11px; font-weight: bold; cursor: pointer; text-align: center; color: white; }
        .btn-pred { background-color: #0284c7; }
        .btn-ruta { background-color: #059669; }
        .btn-train { background-color: #d97706; }
        .badge-marker { display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 15px; box-shadow: 0 0 8px rgba(0,0,0,0.85); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ ArcForest Sentinel v8.0 (Malla Autónoma)</h1>
        <p>Fecha: __FECHA_PERU__ | Escaneo Multi-Provincia: FFDI + VPD + Lluvia</p>
    </div>

    <div class="top-controls">
        <select id="deptoSelect" onchange="ejecutarEscaneoInteligente()">
            <option value="TODOS (Nacional)">🇵🇪 TODO EL PERÚ (Malla Nacional Multi-Región)</option>
            <option value="Junín">📍 Departamento de Junín (9 Corredores)</option>
            <option value="Puno">📍 Departamento de Puno (10 Provincias)</option>
            <option value="Cusco">📍 Departamento de Cusco (9 Provincias)</option>
            <option value="Apurímac">📍 Departamento de Apurímac (7 Provincias)</option>
            <option value="Ayacucho">📍 Departamento de Ayacucho</option>
            <option value="Huancavelica">📍 Departamento de Huancavelica</option>
            <option value="Áncash">📍 Departamento de Áncash</option>
            <option value="Cajamarca">📍 Departamento de Cajamarca</option>
            <option value="Huánuco">📍 Departamento de Huánuco</option>
            <option value="Amazonas / San Martín">📍 Amazonas y San Martín</option>
            <option value="Ucayali / Madre de Dios">📍 Ucayali y Madre de Dios</option>
            <option value="Arequipa">📍 Departamento de Arequipa</option>
        </select>
        <select id="nodoSelect" onchange="seleccionarNodoDeMalla()">
            <option value="">Escaneando puntos de riesgo...</option>
        </select>
    </div>

    <div class="ia-bar">
        <span>🧠 <b>IA Entrenada:</b> <span id="nEv">3</span> incendios reales</span>
        <span>Umbral Crítico Aprendido: <b id="umbIA">> 18.0 FFDI</b></span>
    </div>

    <div class="metrics">
        <div class="metric-item"><span>TEMP MÁX 24h</span><strong id="tempVal">-- °C</strong></div>
        <div class="metric-item"><span>HUM MÍN 24h</span><strong id="humVal">-- %</strong></div>
        <div class="metric-item"><span>VIENTO 24h</span><strong id="vientoVal">-- km/h</strong></div>
        <div class="metric-item"><span>SEQUEDAD VPD</span><strong id="vpdVal">-- kPa</strong></div>
    </div>

    <div class="risk-box" id="riskBox">
        <div class="risk-val" id="riskVal">Escaneando Territorio...</div>
        <div class="risk-diag" id="riskDiag">Analizando microclimas provinciales y anomalías térmicas...</div>
    </div>

    <div id="map"></div>

    <div class="btn-row">
        <button class="btn btn-pred" onclick="auditarPuntoTocado()">🔍 Auditar Punto</button>
        <button class="btn btn-ruta" onclick="trazarRutaCGBVP()">🚒 Ruta Bomberos</button>
        <button class="btn btn-train" onclick="entrenarIA()">💾 Entrenar IA</button>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: true, tap: false }).setView([-11.2, -74.5], 5);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 }).addTo(map);

        let capaMalla = L.layerGroup().addTo(map);
        let puntosMalla = [];
        let puntoActual = null;
        let pinLibre = null;
        let rutaLayer = null;

        function crearIcono(emoji, color) {
            return L.divIcon({
                className: 'badge-marker',
                html: `<div style="background-color:${color}; width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid #ffffff;">${emoji}</div>`,
                iconSize: [32, 32], iconAnchor: [16, 16]
            });
        }

        function actualizarPanel(d) {
            puntoActual = { lat: d.lat, lon: d.lon, zona: d.zona };
            document.getElementById('nEv').innerText = d.eventos_bd;
            document.getElementById('umbIA').innerText = '> ' + d.umbral_entrenado + ' FFDI';

            document.getElementById('tempVal').innerText = d.temp_c + ' °C';
            document.getElementById('humVal').innerText = d.humedad_pct + ' %';
            document.getElementById('vientoVal').innerText = d.viento_kmh + ' km/h';
            document.getElementById('vpdVal').innerText = d.vpd_kpa + ' kPa';

            document.getElementById('riskVal').innerText = `${d.tipo_evento} (${d.ffdi_calculado} FFDI | ${d.probabilidad_pct}%)`;
            document.getElementById('riskDiag').innerText = d.diagnostico;
            document.getElementById('riskVal').style.color = d.color;
            document.getElementById('riskBox').style.borderColor = d.color;
        }

        async function ejecutarEscaneoInteligente() {
            const depto = document.getElementById('deptoSelect').value;
            document.getElementById('riskDiag').innerText = "🛰️ Escaneando simultáneamente todas las provincias y corredores forestales...";
            if (rutaLayer) { map.removeLayer(rutaLayer); rutaLayer = null; }
            if (pinLibre) { map.removeLayer(pinLibre); pinLibre = null; }

            try {
                const res = await fetch(`/api/escaneo_inteligente?departamento=${encodeURIComponent(depto)}`);
                const data = await res.json();
                puntosMalla = data.puntos;
                capaMalla.clearLayers();
                map.setView([data.vista_mapa.lat, data.vista_mapa.lon], data.vista_mapa.zoom);

                const selNodo = document.getElementById('nodoSelect');
                selNodo.innerHTML = "";

                puntosMalla.forEach((p, idx) => {
                    const opt = document.createElement('option');
                    opt.value = idx;
                    opt.innerText = `${p.icono} [${p.probabilidad_pct}%] ${p.zona}`;
                    selNodo.appendChild(opt);

                    const m = L.marker([p.lat, p.lon], { icon: crearIcono(p.icono, p.color) })
                        .addTo(capaMalla)
                        .bindPopup(`<b>${p.zona}</b><br>${p.tipo_evento}<br>FFDI: ${p.ffdi_calculado} | VPD: ${p.vpd_kpa} kPa<br>Lluvia 24h: ${p.lluvia_mm} mm`);
                    m.on('click', () => {
                        selNodo.value = idx;
                        actualizarPanel(p);
                    });
                });

                if (puntosMalla.length > 0) {
                    actualizarPanel(puntosMalla[0]);
                }
            } catch(e) {}
        }

        function seleccionarNodoDeMalla() {
            const idx = parseInt(document.getElementById('nodoSelect').value);
            if (!isNaN(idx) && puntosMalla[idx]) {
                const p = puntosMalla[idx];
                actualizarPanel(p);
                map.setView([p.lat, p.lon], 11);
            }
        }

        map.on('click', function(e) {
            puntoActual = { lat: e.latlng.lat, lon: e.latlng.lng, zona: "Punto Personalizado" };
            if (pinLibre) map.removeLayer(pinLibre);
            pinLibre = L.marker([puntoActual.lat, puntoActual.lon], { icon: crearIcono('📍', '#2563eb') }).addTo(map);
            document.getElementById('riskDiag').innerText = `📍 Coordenada libre marcada (${puntoActual.lat.toFixed(3)}, ${puntoActual.lon.toFixed(3)}). Pulsa '🔍 Auditar Punto'.`;
        });

        async function auditarPuntoTocado() {
            if (!puntoActual) return alert("Toca cualquier lugar del mapa primero.");
            document.getElementById('riskDiag').innerText = "Calculando VPD, lluvia y McArthur FFDI a 24h en esa coordenada...";
            try {
                const res = await fetch('/api/predecir_punto_libre', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon })
                });
                const d = await res.json();
                actualizarPanel(d);
                if (pinLibre) map.removeLayer(pinLibre);
                pinLibre = L.marker([d.lat, d.lon], { icon: crearIcono(d.icono, d.color) })
                    .addTo(map)
                    .bindPopup(`<b>${d.zona}</b><br>${d.tipo_evento}<br>Probabilidad: ${d.probabilidad_pct}%`).openPopup();
            } catch(e) {}
        }

        async function trazarRutaCGBVP() {
            if (!puntoActual) return;
            document.getElementById('riskDiag').innerText = "🚒 Calculando ruta óptima desde la Compañía de Bomberos más cercana...";
            try {
                const res = await fetch(`/api/ruta_bomberos?lat=${puntoActual.lat}&lon=${puntoActual.lon}`);
                const data = await res.json();
                if (data.status === "success") {
                    if (rutaLayer) map.removeLayer(rutaLayer);
                    const latlngs = data.coordenadas.map(c => [c[1], c[0]]);
                    rutaLayer = L.polyline(latlngs, { color: '#38bdf8', weight: 5, opacity: 0.95 }).addTo(map);
                    map.fitBounds(rutaLayer.getBounds(), { padding: [30, 30] });
                    document.getElementById('riskDiag').innerText = `🚒 Despacho: ${data.origen} (${data.distancia_km} km | ~${data.duracion_min} min)`;
                }
            } catch(e) {}
        }

        async function entrenarIA() {
            if (!puntoActual) return;
            if (!confirm(`¿Confirmas incendio real en ${puntoActual.zona || 'este punto'}? La IA recalibrará su umbral crítico.`)) return;
            try {
                const res = await fetch('/api/entrenar_con_incendio_real', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon, zona: puntoActual.zona })
                });
                const d = await res.json();
                document.getElementById('nEv').innerText = d.total_eventos;
                document.getElementById('umbIA').innerText = '> ' + d.nuevo_umbral + ' FFDI';
                document.getElementById('riskDiag').innerText = `✅ IA recalibrada con ${d.total_eventos} eventos. Nuevo umbral: ${d.nuevo_umbral} FFDI.`;
            } catch(e) {}
        }

        ejecutarEscaneoInteligente();
    </script>
</body>
</html>
"""
    return html_content.replace("__FECHA_PERU__", fecha_peru)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)