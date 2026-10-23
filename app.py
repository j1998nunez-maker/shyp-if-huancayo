import csv
import io
import sqlite3
import math
import requests
import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_PATH = "af_inteligencia_v9.db"

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
    "Cajamarca": {
        "centro": [-6.65, -78.65], "zoom": 8, "bbox": [-7.75, -79.45, -4.70, -77.75],
        "nodos": [
            {"zona": "Cajamarca - Porcón / Baños del Inca", "lat": -7.080, "lon": -78.580},
            {"zona": "Cutervo / Chota - Bosques Montanos", "lat": -6.380, "lon": -78.810},
            {"zona": "Jaén / San Ignacio - Bosques Secos", "lat": -5.450, "lon": -78.850},
            {"zona": "Celendín / Cajabamba", "lat": -7.250, "lon": -78.120}
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
            {"zona": "Tarapoto / Lamas (San Martín)", "lat": -6.480, "lon": -76.390}
        ]
    },
    "Ucayali / Madre de Dios": {
        "centro": [-10.50, -72.00], "zoom": 6, "bbox": [-13.35, -75.80, -7.20, -68.85],
        "nodos": [
            {"zona": "Coronel Portillo - Pucallpa", "lat": -8.450, "lon": -74.750},
            {"zona": "Padre Abad - Aguaytía (Ucayali)", "lat": -9.040, "lon": -75.510},
            {"zona": "Tambopata - Puerto Maldonado", "lat": -12.590, "lon": -69.250},
            {"zona": "Tahuamanu - Iberia / Iñapari", "lat": -11.410, "lon": -69.490}
        ]
    },
    "Arequipa": {
        "centro": [-15.85, -71.80], "zoom": 8, "bbox": [-16.65, -73.50, -14.70, -70.85],
        "nodos": [
            {"zona": "Arequipa - Faldas Pichu Pichu / Chiguata", "lat": -16.410, "lon": -71.360},
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
    {"nombre": "Cía. Bomberos Satipo B-148", "lat": -11.252, "lon": -74.638},
    {"nombre": "Cía. Bomberos Puno B-42", "lat": -15.83685, "lon": -70.02295},
    {"nombre": "Cía. Bomberos Juliaca B-53", "lat": -15.4997, "lon": -70.1333},
    {"nombre": "Cía. Bomberos Ayaviri B-192", "lat": -14.881, "lon": -70.589},
    {"nombre": "Cía. Bomberos Macusani B-210", "lat": -14.069, "lon": -70.431},
    {"nombre": "Cía. Bomberos Cusco B-39", "lat": -13.52055, "lon": -71.97235},
    {"nombre": "Cía. Bomberos Sicuani B-50", "lat": -14.2694, "lon": -71.2261},
    {"nombre": "Cía. Bomberos Abancay B-68", "lat": -13.63585, "lon": -72.87815},
    {"nombre": "Cía. Bomberos Curahuasi B-143", "lat": -13.5415, "lon": -72.6975},
    {"nombre": "Cía. Bomberos Andahuaylas B-153", "lat": -13.6556, "lon": -73.3872},
    {"nombre": "Cía. Bomberos Ayacucho B-63", "lat": -13.1631, "lon": -74.2236},
    {"nombre": "Cía. Bomberos Huancavelica B-56", "lat": -12.7861, "lon": -74.9722},
    {"nombre": "Cía. Bomberos Huaraz B-84", "lat": -9.52985, "lon": -77.52875},
    {"nombre": "Cía. Bomberos Cajamarca B-59", "lat": -7.1617, "lon": -78.5128},
    {"nombre": "Cía. Bomberos Jaén B-69 (Cajamarca)", "lat": -5.707, "lon": -78.807},
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
        CREATE TABLE IF NOT EXISTS eventos_entrenamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT, zona TEXT, categoria_origen TEXT,
            lat REAL, lon REAL,
            temp_c REAL, humedad_pct REAL, viento_kmh REAL, vpd_kpa REAL, ffdi_registrado REAL
        )
    """)
    c.execute("SELECT COUNT(*) FROM eventos_entrenamiento")
    if c.fetchone()[0] == 0:
        semillas = [
            ("2026-10-13", "Curahuasi - Apurímac", "INCENDIO_FORESTAL", -13.5240, -72.7350, 22.8, 23.0, 27.5, 2.14, 21.4),
            ("2026-10-19", "Apu Pachatusan - Cusco", "INCENDIO_FORESTAL", -13.5085, -71.8150, 19.5, 21.0, 32.0, 1.80, 18.2),
            ("2026-09-25", "Acopalca - Huancayo", "INCENDIO_FORESTAL", -11.9960, -75.1380, 18.4, 26.0, 24.5, 1.56, 14.5),
            ("2026-10-22", "Jaén/Cutervo - Cajamarca", "ANTROPOGENICO", -6.0431, -79.3426, 18.8, 59.0, 16.1, 0.89, 2.1),
            ("2026-10-05", "Azapampa - Huancayo", "ANTROPOGENICO", -12.1150, -75.1850, 19.0, 48.0, 14.0, 1.14, 4.8)
        ]
        c.executemany("""
            INSERT INTO eventos_entrenamiento 
            (fecha, zona, categoria_origen, lat, lon, temp_c, humedad_pct, viento_kmh, vpd_kpa, ffdi_registrado) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, semillas)
        conn.commit()
    conn.close()

init_db()

# Obtener parámetros aprendidos diferenciando Incendios Forestales vs Quemas Antropogénicas
def obtener_cerebro_ia():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT AVG(ffdi_registrado), COUNT(*) FROM eventos_entrenamiento WHERE categoria_origen = 'INCENDIO_FORESTAL'")
    row_if = c.fetchone()
    c.execute("SELECT AVG(ffdi_registrado), COUNT(*) FROM eventos_entrenamiento WHERE categoria_origen = 'ANTROPOGENICO'")
    row_ant = c.fetchone()
    c.execute("SELECT COUNT(*) FROM eventos_entrenamiento")
    total = c.fetchone()[0]
    conn.close()

    umbral_forestal = round(float(row_if[0]), 1) if (row_if and row_if[1] > 0) else 16.5
    media_antropica = round(float(row_ant[0]), 1) if (row_ant and row_ant[1] > 0) else 4.5

    return {
        "total_eventos": total,
        "n_forestales": row_if[1] if row_if else 0,
        "n_antropogenicos": row_ant[1] if row_ant else 0,
        "umbral_ffdi_forestal": max(10.0, umbral_forestal),
        "umbral_ffdi_antropico": max(2.0, media_antropica)
    }

def calcular_indices_fisicos(t, hr, w, lluvia_mm):
    try:
        es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
        vpd = round(max(0.1, es * (1.0 - (hr / 100.0))), 2)
        factor_d = max(1.5, min(10.0, 10.0 - (lluvia_mm * 1.3)))
        ffdi = 2.0 * math.exp(-0.450 + 0.987 * math.log(factor_d) - 0.0345 * hr + 0.0338 * t + 0.0234 * w)
        return round(max(0.5, ffdi), 1), vpd
    except:
        return 1.5, 0.8

def escanear_malla_clima(lista_nodos, fecha_hist=None):
    if not lista_nodos:
        return []
    hoy_str = obtener_hora_peru().strftime("%Y-%m-%d")
    lats = ",".join([str(n["lat"]) for n in lista_nodos])
    lons = ",".join([str(n["lon"]) for n in lista_nodos])

    # Si el usuario entrena con una fecha pasada, usar Archive API
    if fecha_hist and fecha_hist != hoy_str:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lats}&longitude={lons}&start_date={fecha_hist}&end_date={fecha_hist}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
    else:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation&forecast_days=2"

    resultados = []
    try:
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            bloques = data if isinstance(data, list) else [data]
            for b in bloques:
                h = b.get("hourly", {})
                temps = [x for x in h.get("temperature_2m", [])[:24] if x is not None]
                hums = [x for x in h.get("relative_humidity_2m", [])[:24] if x is not None]
                winds = [x for x in h.get("wind_speed_10m", [])[:24] if x is not None]
                precs = [x for x in h.get("precipitation", [])[:24] if x is not None]
                if temps and hums and winds:
                    resultados.append({
                        "t": round(float(max(temps)), 1),
                        "hr": round(float(min(hums)), 1),
                        "w": round(float(max(winds)), 1),
                        "rain": round(float(sum(precs)), 1) if precs else 0.0
                    })
                else:
                    resultados.append({"t": 18.5, "hr": 36.0, "w": 18.0, "rain": 0.0})
            return resultados
    except:
        pass
    return [{"t": 18.5, "hr": 36.0, "w": 18.0, "rain": 0.0} for _ in lista_nodos]

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

# MOTOR DIFERENCIADOR: Separa Incendio Forestal vs Origen Antropogénico vs Riesgo Natural Climático vs Seguro
def clasificar_nodo_inteligente(zona, lat, lon, m, cerebro, frp_mw=0.0, es_urbano=False):
    ffdi, vpd = calcular_indices_fisicos(m["t"], m["hr"], m["w"], m["rain"])
    umbral_if = cerebro["umbral_ffdi_forestal"]
    prob_pct = round(min(99.5, (ffdi / (umbral_if * 1.3)) * 100.0), 1)

    if es_urbano:
        categoria = "URBANO"
        origen_texto = "🏙️ ORIGEN URBANO / INDUSTRIAL"
        diag = f"🏙️ {zona}: Zona urbana/infraestructura. Sin combustible forestal (FFDI: {ffdi})."
        color, icono, prioridad = "#8b5cf6", "🏙️", 10.0
    elif frp_mw > 0:
        # Hay fuego detectado por satélite: ¿Es Incendio Forestal Descontrolado o Quema Antropogénica Agrícola?
        if frp_mw >= 15.0 or (ffdi >= umbral_if * 0.75 and m["hr"] <= 38.0):
            categoria = "INCENDIO_FORESTAL"
            origen_texto = "🔥 INCENDIO FORESTAL (PROPAGACIÓN CRÍTICA)"
            diag = f"🔥 {zona}: Potencia alta ({frp_mw} MW) + Atmósfera seca (HR {m['hr']}%, FFDI {ffdi}). Fuego fuera de control."
            color, icono, prioridad = "#ef4444", "🔥", 100.0 + ffdi
        else:
            categoria = "ANTROPOGENICO"
            origen_texto = "🚜 ORIGEN ANTROPOGÉNICO (QUEMA AGRÍCOLA / HUMANA)"
            diag = f"🚜 {zona}: Quema humana/agrícola detectada ({frp_mw} MW). La humedad ({m['hr']}%) frena su propagación forestal (FFDI {ffdi})."
            color, icono, prioridad = "#f97316", "🚜", 75.0 + ffdi
    else:
        # No hay fuego activo hoy: Evaluar Riesgo Natural / Susceptibilidad Climática a 24h
        if ffdi >= umbral_if or (vpd >= 1.55 and m["hr"] <= 30.0):
            categoria = "RIESGO_NATURAL"
            origen_texto = "⚡ RIESGO NATURAL / CLIMÁTICO EXTREMO (24h)"
            diag = f"⚡ {zona}: Estrés hídrico severo en vegetación (VPD {vpd} kPa, HR {m['hr']}%). Peligro crítico mañana ({prob_pct}%)."
            color, icono, prioridad = "#dc2626", "⚡", 60.0 + ffdi
        elif ffdi >= (umbral_if * 0.55):
            categoria = "RIESGO_NATURAL"
            origen_texto = "⚠️ SUSCEPTIBILIDAD NATURAL / CLIMÁTICA (24h)"
            diag = f"⚠️ {zona}: Condición seca moderada (FFDI {ffdi}, VPD {vpd} kPa). Vulnerable ante quemas humanas mañana ({prob_pct}%)."
            color, icono, prioridad = "#eab308", "⚠️", 40.0 + ffdi
        else:
            categoria = "SEGURO"
            origen_texto = "🌲 ECOSISTEMA NATURAL SEGURO / HÚMEDO (24h)"
            diag = f"🌲 {zona}: Humedad alta ({m['hr']}%) y lluvia ({m['rain']} mm) protegen la vegetación ({prob_pct}%)."
            color, icono, prioridad = "#10b981", "🌲", ffdi

    return {
        "zona": zona, "lat": lat, "lon": lon,
        "categoria": categoria, "origen_texto": origen_texto,
        "temp_c": m["t"], "humedad_pct": m["hr"], "viento_kmh": m["w"],
        "lluvia_mm": m["rain"], "vpd_kpa": vpd, "ffdi_calculado": ffdi,
        "probabilidad_pct": prob_pct, "diagnostico": diag,
        "color": color, "icono": icono, "prioridad": prioridad,
        "cerebro": cerebro
    }

@app.route('/api/escaneo_inteligente', methods=['GET'])
def escaneo_inteligente():
    depto = request.args.get('departamento', 'TODOS (Nacional)')
    cerebro = obtener_cerebro_ia()

    nodos_a_evaluar = []
    if depto == "TODOS (Nacional)":
        vista = {"lat": -11.2, "lon": -74.5, "zoom": 5}
        for d_key, d_val in MALLA_CORREDORES_PERU.items():
            for n in d_val["nodos"][:2]:
                nodos_a_evaluar.append({"zona": f"[{d_key}] {n['zona']}", "lat": n["lat"], "lon": n["lon"]})
    else:
        info_d = MALLA_CORREDORES_PERU.get(depto, MALLA_CORREDORES_PERU["Junín"])
        vista = {"lat": info_d["centro"][0], "lon": info_d["centro"][1], "zoom": info_d["zoom"], "bbox": info_d["bbox"]}
        for n in info_d["nodos"]:
            nodos_a_evaluar.append({"zona": n["zona"], "lat": n["lat"], "lon": n["lon"]})

    sat_focos = escanear_nasa_firms()
    nodos_sat = []
    for f in sat_focos:
        if depto != "TODOS (Nacional)":
            b = vista["bbox"]
            if not (b[0] <= f["lat"] <= b[2] and b[1] <= f["lon"] <= b[3]):
                continue
        nodos_sat.append({"zona": f"Foco Satelital ({f['lat']}, {f['lon']})", "lat": f["lat"], "lon": f["lon"], "frp": f["frp"]})
    nodos_sat.sort(key=lambda x: x["frp"], reverse=True)
    nodos_sat = nodos_sat[:8]

    todos_nodos = nodos_a_evaluar + nodos_sat
    climas = escanear_malla_clima(todos_nodos)

    puntos_analizados = []
    for idx, nodo in enumerate(todos_nodos):
        m = climas[idx] if idx < len(climas) else {"t": 18.0, "hr": 40.0, "w": 15.0, "rain": 0.0}
        frp_val = nodo.get("frp", 0.0)
        ev = clasificar_nodo_inteligente(nodo["zona"], nodo["lat"], nodo["lon"], m, cerebro, frp_val, False)
        puntos_analizados.append(ev)

    puntos_analizados.sort(key=lambda x: x["prioridad"], reverse=True)

    return jsonify({
        "status": "success",
        "vista_mapa": vista,
        "cerebro": cerebro,
        "puntos": puntos_analizados
    })

@app.route('/api/predecir_punto_libre', methods=['POST'])
def predecir_punto_libre():
    data = request.get_json()
    lat, lon = round(float(data["lat"]), 4), round(float(data["lon"]), 4)
    fecha = data.get("fecha")
    cerebro = obtener_cerebro_ia()

    nombre_zona = f"Coordenada ({lat}, {lon})"
    es_urbano = False
    try:
        rn = requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=15", headers={"User-Agent": "AF-Sentinel-v9"}, timeout=3)
        if rn.status_code == 200:
            dn = rn.json()
            addr = dn.get("address", {})
            cat = dn.get("category", "")
            if ("road" in addr or "suburb" in addr or "neighbourhood" in addr) and cat not in ["natural", "landuse"]:
                es_urbano = True
            loc = addr.get("village", addr.get("town", addr.get("city", addr.get("county", ""))))
            if loc:
                nombre_zona = f"{loc} ({lat}, {lon})"
    except:
        pass

    climas = escanear_malla_clima([{"lat": lat, "lon": lon}], fecha_hist=fecha)
    ev = clasificar_nodo_inteligente(nombre_zona, lat, lon, climas[0], cerebro, 0.0, es_urbano)
    return jsonify(ev)

@app.route('/api/entrenar_supervisado', methods=['POST'])
def entrenar_supervisado():
    data = request.get_json()
    lat, lon = round(float(data["lat"]), 4), round(float(data["lon"]), 4)
    zona = data.get("zona", f"Punto ({lat}, {lon})")
    categoria = data.get("categoria", "INCENDIO_FORESTAL")
    fecha = data.get("fecha") or obtener_hora_peru().strftime("%Y-%m-%d")

    climas = escanear_malla_clima([{"lat": lat, "lon": lon}], fecha_hist=fecha)
    m = climas[0]
    ffdi_real, vpd_real = calcular_indices_fisicos(m["t"], m["hr"], m["w"], m["rain"])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO eventos_entrenamiento 
        (fecha, zona, categoria_origen, lat, lon, temp_c, humedad_pct, viento_kmh, vpd_kpa, ffdi_registrado) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, zona, categoria, lat, lon, m["t"], m["hr"], m["w"], vpd_real, ffdi_real))
    conn.commit()
    conn.close()

    nuevo_cerebro = obtener_cerebro_ia()
    return jsonify({
        "status": "success",
        "cerebro": nuevo_cerebro,
        "ffdi_guardado": ffdi_real,
        "categoria_guardada": categoria
    })

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
    <title>ArcForest Sentinel v9.0 | Clasificador Natural vs. Antropogénico</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #ffffff; padding: 8px; display: flex; flex-direction: column; height: 100vh; overflow-y: hidden; }
        .header { text-align: center; margin-bottom: 4px; }
        .header h1 { font-size: 15px; color: #ff5722; font-weight: 800; }
        .header p { font-size: 9px; color: #94a3b8; font-weight: bold; }
        .top-controls { display: flex; gap: 4px; margin-bottom: 4px; }
        select, input[type="date"] { width: 100%; padding: 7px; border-radius: 6px; background: #1c2541; color: white; border: 1px solid #48cae4; font-size: 11px; font-weight: bold; }
        .ia-bar { background: #1e293b; border: 1px solid #38bdf8; border-radius: 6px; padding: 4px 8px; margin-bottom: 4px; font-size: 9px; display: flex; justify-content: space-between; align-items: center; }
        .ia-bar b { color: #00f5d4; }
        .metrics { display: flex; justify-content: space-between; margin-bottom: 4px; gap: 4px; }
        .metric-item { background: #1c2541; padding: 4px; border-radius: 6px; text-align: center; width: 25%; border: 1px solid #3a506b; }
        .metric-item span { font-size: 7px; color: #94a3b8; display: block; }
        .metric-item strong { font-size: 11px; color: #48cae4; }
        .risk-box { text-align: center; padding: 6px 8px; border-radius: 8px; margin-bottom: 4px; border: 2px solid #48cae4; background: #1c2541; }
        .risk-val { font-size: 14px; font-weight: 900; color: #00f5d4; margin-bottom: 2px; }
        .risk-diag { font-size: 10px; font-weight: 600; color: #f8fafc; line-height: 1.2; }
        #map { width: 100%; flex-grow: 1; border-radius: 10px; margin-bottom: 5px; border: 1px solid #3a506b; z-index: 1; }
        .train-drawer { display: none; background: #1e293b; border: 1px solid #f59e0b; border-radius: 8px; padding: 7px; margin-bottom: 5px; }
        .train-drawer.active { display: block; }
        .train-drawer label { font-size: 9px; color: #fcd34d; font-weight: bold; display: block; margin-bottom: 4px; }
        .btn-row { display: flex; gap: 5px; }
        .btn { flex: 1; padding: 9px 4px; border: none; border-radius: 7px; font-size: 11px; font-weight: bold; cursor: pointer; text-align: center; color: white; }
        .btn-pred { background-color: #0284c7; }
        .btn-ruta { background-color: #059669; }
        .btn-train { background-color: #d97706; }
        .badge-marker { display: flex; align-items: center; justify-content: center; border-radius: 50%; font-size: 15px; box-shadow: 0 0 8px rgba(0,0,0,0.85); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🛰️ ArcForest Sentinel v9.0 (Clasificador + IA Supervisada)</h1>
        <p>Fecha: __FECHA_PERU__ | Diferenciador: Incendio Forestal vs. Antropogénico vs. Riesgo Natural</p>
    </div>

    <!-- 3 CONTROLES SUPERIORES: DEPARTAMENTO + FILTRO DE ORIGEN + SELECTOR DE PUNTO -->
    <div class="top-controls">
        <select id="deptoSelect" onchange="ejecutarEscaneoInteligente()">
            <option value="TODOS (Nacional)">🇵🇪 Todo el Perú</option>
            <option value="Junín">📍 Junín</option>
            <option value="Puno">📍 Puno</option>
            <option value="Cusco">📍 Cusco</option>
            <option value="Apurímac">📍 Apurímac</option>
            <option value="Cajamarca">📍 Cajamarca</option>
            <option value="Ayacucho">📍 Ayacucho</option>
            <option value="Huancavelica">📍 Huancavelica</option>
            <option value="Áncash">📍 Áncash</option>
            <option value="Huánuco">📍 Huánuco</option>
            <option value="Amazonas / San Martín">📍 Amazonas / San Martín</option>
            <option value="Ucayali / Madre de Dios">📍 Ucayali / Madre de Dios</option>
            <option value="Arequipa">📍 Arequipa</option>
        </select>

        <select id="filtroOrigen" onchange="aplicarFiltroEnMapa()" style="border-color: #f59e0b;">
            <option value="TODOS">🔍 Mostrar Todos (Sin filtro)</option>
            <option value="INCENDIO_FORESTAL">🔥 Solo Incendio Forestal</option>
            <option value="ANTROPOGENICO">🚜 Solo Antropogénico (Quemas)</option>
            <option value="RIESGO_NATURAL">⚡ Solo Riesgo Natural / Climático</option>
            <option value="SEGURO">🌲 Solo Zonas Seguras / Húmedas</option>
        </select>

        <select id="nodoSelect" onchange="seleccionarNodoDeMalla()">
            <option value="">Puntos...</option>
        </select>
    </div>

    <div class="ia-bar">
        <span>🧠 <b>BD IA:</b> <b id="nForestal">3</b> Forestales | <b id="nAntropico">2</b> Antropogénicos</span>
        <span>Umbral Propagación: <b id="umbIA">> 18.0 FFDI</b></span>
    </div>

    <div class="metrics">
        <div class="metric-item"><span>TEMP MÁX 24h</span><strong id="tempVal">-- °C</strong></div>
        <div class="metric-item"><span>HUM MÍN 24h</span><strong id="humVal">-- %</strong></div>
        <div class="metric-item"><span>VIENTO 24h</span><strong id="vientoVal">-- km/h</strong></div>
        <div class="metric-item"><span>SEQUEDAD VPD</span><strong id="vpdVal">-- kPa</strong></div>
    </div>

    <div class="risk-box" id="riskBox">
        <div class="risk-val" id="riskVal">Clasificando Territorio...</div>
        <div class="risk-diag" id="riskDiag">Diferenciando quemas antropogénicas, incendios y riesgo climático...</div>
    </div>

    <div id="map"></div>

    <!-- PANEL DESPLEGABLE DE ENTRENAMIENTO SUPERVISADO -->
    <div class="train-drawer" id="trainDrawer">
        <label>🧠 Entrenamiento Supervisado (Elige fecha y clasifica el evento seleccionado para enseñar a la IA):</label>
        <div class="top-controls">
            <input type="date" id="fechaEntrenar" value="__FECHA_PERU__">
            <select id="catEntrenar">
                <option value="INCENDIO_FORESTAL">🔥 Es Incendio Forestal (Descontrolado)</option>
                <option value="ANTROPOGENICO">🚜 Es Quema Antropogénica (Agrícola/Humana)</option>
                <option value="RIESGO_NATURAL">⚡ Es Ignición / Riesgo Natural</option>
            </select>
            <button class="btn btn-train" style="flex:0.8;" onclick="confirmarEntrenamiento()">✅ Guardar en BD</button>
        </div>
    </div>

    <div class="btn-row">
        <button class="btn btn-pred" onclick="auditarPuntoTocado()">🔍 1. Auditar Punto</button>
        <button class="btn btn-ruta" onclick="trazarRutaCGBVP()">🚒 2. Ruta Bomberos</button>
        <button class="btn btn-train" onclick="togglePanelEntrenar()">🧠 3. Entrenar / Validar IA</button>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        let map = L.map('map', { zoomControl: true, tap: false }).setView([-11.2, -74.5], 5);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19 }).addTo(map);

        let capaMalla = L.layerGroup().addTo(map);
        let todosLosPuntos = [];
        let puntosFiltrados = [];
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

        function actualizarBarraCerebro(c) {
            if (!c) return;
            document.getElementById('nForestal').innerText = c.n_forestales;
            document.getElementById('nAntropico').innerText = c.n_antropogenicos;
            document.getElementById('umbIA').innerText = '> ' + c.umbral_ffdi_forestal + ' FFDI';
        }

        function actualizarPanel(d) {
            puntoActual = { lat: d.lat, lon: d.lon, zona: d.zona };
            if (d.cerebro) actualizarBarraCerebro(d.cerebro);

            document.getElementById('tempVal').innerText = d.temp_c + ' °C';
            document.getElementById('humVal').innerText = d.humedad_pct + ' %';
            document.getElementById('vientoVal').innerText = d.viento_kmh + ' km/h';
            document.getElementById('vpdVal').innerText = d.vpd_kpa + ' kPa';

            document.getElementById('riskVal').innerText = `${d.origen_texto} (${d.ffdi_calculado} FFDI | ${d.probabilidad_pct}%)`;
            document.getElementById('riskDiag').innerText = d.diagnostico;
            document.getElementById('riskVal').style.color = d.color;
            document.getElementById('riskBox').style.borderColor = d.color;
        }

        async function ejecutarEscaneoInteligente() {
            const depto = document.getElementById('deptoSelect').value;
            document.getElementById('riskDiag').innerText = "🛰️ Escaneando territorio y separando origen Antropogénico vs. Natural vs. Forestal...";
            if (rutaLayer) { map.removeLayer(rutaLayer); rutaLayer = null; }
            if (pinLibre) { map.removeLayer(pinLibre); pinLibre = null; }

            try {
                const res = await fetch(`/api/escaneo_inteligente?departamento=${encodeURIComponent(depto)}`);
                const data = await res.json();
                todosLosPuntos = data.puntos;
                actualizarBarraCerebro(data.cerebro);
                map.setView([data.vista_mapa.lat, data.vista_mapa.lon], data.vista_mapa.zoom);
                aplicarFiltroEnMapa();
            } catch(e) {}
        }

        // Filtra en vivo los marcadores del mapa según la categoría elegida (Antropogénico, Forestal, Natural o Seguro)
        function aplicarFiltroEnMapa() {
            const filtro = document.getElementById('filtroOrigen').value;
            capaMalla.clearLayers();
            const selNodo = document.getElementById('nodoSelect');
            selNodo.innerHTML = "";

            puntosFiltrados = todosLosPuntos.filter(p => filtro === "TODOS" || p.categoria === filtro);

            puntosFiltrados.forEach((p, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                opt.innerText = `${p.icono} [${p.probabilidad_pct}%] ${p.zona}`;
                selNodo.appendChild(opt);

                const m = L.marker([p.lat, p.lon], { icon: crearIcono(p.icono, p.color) })
                    .addTo(capaMalla)
                    .bindPopup(`<b>${p.origen_texto}</b><br>${p.zona}<br>FFDI: ${p.ffdi_calculado} | HR: ${p.humedad_pct}% | VPD: ${p.vpd_kpa} kPa`);
                m.on('click', () => {
                    selNodo.value = idx;
                    actualizarPanel(p);
                });
            });

            if (puntosFiltrados.length > 0) {
                actualizarPanel(puntosFiltrados[0]);
            } else {
                document.getElementById('riskVal').innerText = "SIN EVENTOS EN ESTA CATEGORÍA";
                document.getElementById('riskDiag').innerText = `No hay puntos clasificados como [${filtro}] en este departamento hoy. Cambia el filtro a 'Mostrar Todos'.`;
            }
        }

        function seleccionarNodoDeMalla() {
            const idx = parseInt(document.getElementById('nodoSelect').value);
            if (!isNaN(idx) && puntosFiltrados[idx]) {
                const p = puntosFiltrados[idx];
                actualizarPanel(p);
                map.setView([p.lat, p.lon], 11);
            }
        }

        map.on('click', function(e) {
            puntoActual = { lat: e.latlng.lat, lon: e.latlng.lng, zona: "Punto Auditado" };
            if (pinLibre) map.removeLayer(pinLibre);
            pinLibre = L.marker([puntoActual.lat, puntoActual.lon], { icon: crearIcono('📍', '#2563eb') }).addTo(map);
            document.getElementById('riskDiag').innerText = `📍 Coordenada (${puntoActual.lat.toFixed(3)}, ${puntoActual.lon.toFixed(3)}) marcada. Pulsa '🔍 1. Auditar Punto' o '🧠 3. Entrenar IA'.`;
        });

        async function auditarPuntoTocado() {
            if (!puntoActual) return alert("Toca cualquier lugar del mapa primero.");
            const fecha = document.getElementById('fechaEntrenar').value;
            document.getElementById('riskDiag').innerText = "Analizando si el punto corresponde a zona urbana, quema antropogénica o riesgo natural...";
            try {
                const res = await fetch('/api/predecir_punto_libre', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ lat: puntoActual.lat, lon: puntoActual.lon, fecha: fecha })
                });
                const d = await res.json();
                actualizarPanel(d);
                if (pinLibre) map.removeLayer(pinLibre);
                pinLibre = L.marker([d.lat, d.lon], { icon: crearIcono(d.icono, d.color) })
                    .addTo(map)
                    .bindPopup(`<b>${d.origen_texto}</b><br>${d.zona}`).openPopup();
            } catch(e) {}
        }

        function togglePanelEntrenar() {
            const drawer = document.getElementById('trainDrawer');
            drawer.classList.toggle('active');
        }

        async function confirmarEntrenamiento() {
            if (!puntoActual) return alert("Primero selecciona un foco o toca un punto en el mapa.");
            const cat = document.getElementById('catEntrenar').value;
            const fecha = document.getElementById('fechaEntrenar').value;

            document.getElementById('riskDiag').innerText = "💾 Guardando evento etiquetado y recalibrando umbrales de la IA...";
            try {
                const res = await fetch('/api/entrenar_supervisado', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        lat: puntoActual.lat,
                        lon: puntoActual.lon,
                        zona: puntoActual.zona,
                        categoria: cat,
                        fecha: fecha
                    })
                });
                const d = await res.json();
                actualizarBarraCerebro(d.cerebro);
                document.getElementById('trainDrawer').classList.remove('active');
                document.getElementById('riskDiag').innerText = `✅ ¡IA Entrenada! Evento guardado como [${d.categoria_guardada}] con ${d.ffdi_guardado} FFDI. Nuevo umbral: > ${d.cerebro.umbral_ffdi_forestal} FFDI.`;
            } catch(e) {}
        }

        async function trazarRutaCGBVP() {
            if (!puntoActual) return;
            document.getElementById('riskDiag').innerText = "🚒 Calculando ruta desde la Compañía de Bomberos más cercana...";
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

        ejecutarEscaneoInteligente();
    </script>
</body>
</html>
"""
    return html_content.replace("__FECHA_PERU__", fecha_peru)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)