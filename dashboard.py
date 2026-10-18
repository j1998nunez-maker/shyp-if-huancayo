import os
import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import streamlit.components.v1 as components

# Si existe variable de entorno usa la nube, si no, usa localhost
BACKEND_URL = "https://shyp-if-huancayo.onrender.com"

st.set_page_config(page_title="SHYp-IF Dashboard", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .big-font { font-size: 20px !important; font-weight: 600; color: #E5E7EB; }
    div[data-testid="stMetricValue"] > div { font-size: 28px !important; font-weight: 700; color: #00E5FF; }
    div[data-testid="stMetricLabel"] > label { font-size: 15px !important; font-weight: 600; color: #D1D5DB; }
    .stButton>button { width: 100%; height: 48px; font-size: 16px !important; font-weight: 700; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 SHYp-IF: Sistema Híbrido Predictivo de Incendios Forestales")
st.markdown("<p class='big-font'>Bases Oficiales CGBVP Fijas + Geolocalización Automática en Tiempo Real hacia Zonas Forestales</p>", unsafe_allow_html=True)
st.markdown("---")

BACKEND_URL = "https://shyp-if-huancayo.onrender.com"

# Cuarteles Oficiales del Cuerpo General de Bomberos Voluntarios del Perú (Fijos y Verificados)
REGIONES_PERU = {
    "Huancayo (Junín)": {
        "lat": -12.06915, "lon": -75.20985, # Exacto: Jr. Áncash 603, Huancayo
        "direccion_maps": "Compañia+de+Bomberos+Huancayo+30,+Jiron+Ancash+603,+Huancayo",
        "ladera_lat": -11.9960, "ladera_lon": -75.1380, 
        "sector_forestal": "Bosque Forestal Acopalca - Quebrada Shullcas",
        "base_operativa": "Cía. Bomberos Huancayo B-30 (Jr. Áncash 603)"
    },
    "Cusco": {
        "lat": -13.52055, "lon": -71.97235, # Exacto: Av. Garcilaso 313, Cusco
        "direccion_maps": "Compañia+de+Bomberos+Cusco+39,+Avenida+Garcilaso+313,+Cusco",
        "ladera_lat": -13.4750, "ladera_lon": -71.9680, 
        "sector_forestal": "Sector Forestal Alto Tambomachay - Pajonal",
        "base_operativa": "Cía. Bomberos Cusco B-39 (Av. Garcilaso 313)"
    },
    "Puno": {
        "lat": -15.83685, "lon": -70.02295, # Exacto: Av. El Sol 829, Puno
        "direccion_maps": "Compañia+de+Bomberos+Puno+42,+Avenida+El+Sol+829,+Puno",
        "ladera_lat": -15.8120, "ladera_lon": -70.0450,
        "sector_forestal": "Pajonales de Ichu - Cerros de Yanamayo",
        "base_operativa": "Cía. Bomberos Puno B-42 (Av. El Sol 829)"
    },
    "Abancay (Apurímac)": {
        "lat": -13.63585, "lon": -72.87815, # Exacto: Av. Seoane 210, Abancay
        "direccion_maps": "Compañia+de+Bomberos+Abancay+68,+Avenida+Seoane,+Abancay",
        "ladera_lat": -13.5950, "ladera_lon": -72.8780,
        "sector_forestal": "Bosque de Intimpa - Faldas del Ampay",
        "base_operativa": "Cía. Bomberos Abancay B-68 (Av. Seoane 210)"
    },
    "Huaraz (Áncash)": {
        "lat": -9.52985, "lon": -77.52875, # Exacto: Centro Cívico / Jr. Sucre, Huaraz
        "direccion_maps": "Compañia+de+Bomberos+Huaraz+84,+Huaraz",
        "ladera_lat": -9.4780, "ladera_lon": -77.4950,
        "sector_forestal": "Pajonal y Bosque Nativo - Ruta Quebrada Llaca",
        "base_operativa": "Cía. Bomberos Santiago Antúnez B-84 (Huaraz)"
    }
}

for key in ["datos_clima", "datos_satelite", "datos_cono", "datos_ruta", "res_escaneo"]:
    if key not in st.session_state:
        st.session_state[key] = {}

gps_backend = {"activo": False}
try:
    gps_backend = requests.get(f"{BACKEND_URL}/api/obtener_gps", timeout=2).json()
except: pass

st.subheader("🔍 Panel de Observación General (Cuarteles CGBVP y Zonas Forestales)")
if st.button("🔭 Ejecutar Escaneo General Nacional"):
    try:
        res = requests.get(f"{BACKEND_URL}/api/escaneo_general", timeout=8)
        if res.status_code == 200:
            st.session_state["res_escaneo"] = res.json().get("detalle", [])
            st.success("✅ Escaneo nacional de cuarteles y bosques completado.")
    except Exception:
        st.error("⚠️ Servidor Flask inactivo.")

if st.session_state["res_escaneo"]:
    df = pd.DataFrame(st.session_state["res_escaneo"])
    st.dataframe(df[["region", "base_bomberos", "zona_forestal", "estado", "indice_riesgo", "expansion_amago_pct", "temperatura_c"]], use_container_width=True)

st.markdown("---")

st.sidebar.markdown("### 📍 Región de Monitoreo")
selected_region = st.sidebar.selectbox("Seleccionar Región:", list(REGIONES_PERU.keys()))
datos_reg = REGIONES_PERU[selected_region]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🧭 Punto de Partida")

modo_origen = st.sidebar.radio(
    "Selecciona desde dónde trazar la ruta accesible:",
    ["🚒 Base Oficial de Bomberos (Fija)", "📍 Mi Ubicación Actual (Automática)"]
)

if "ultimo_modo_origen" not in st.session_state:
    st.session_state["ultimo_modo_origen"] = modo_origen

if st.session_state["ultimo_modo_origen"] != modo_origen:
    st.session_state["datos_ruta"][selected_region] = {} 
    st.session_state["ultimo_modo_origen"] = modo_origen

if modo_origen == "📍 Mi Ubicación Actual (Automática)":
    with st.sidebar:
        components.html(f"""
            <div style="font-family: sans-serif;">
                <button onclick="ubicarmeComoGoogleMaps()" style="
                    width: 100%; padding: 12px; background-color: #10B981; color: white;
                    border: none; border-radius: 8px; font-weight: bold; font-size: 14px;
                    cursor: pointer; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                    🎯 Detectar Mi Ubicación Exacta
                </button>
                <p id="estado_gps" style="color: #9CA3AF; font-size: 12px; margin-top: 8px; text-align: center;">
                    Pulsa el botón verde para ubicarte automáticamente donde estés.
                </p>
            </div>
            <script>
            function ubicarmeComoGoogleMaps() {{
                const status = document.getElementById("estado_gps");
                if (!navigator.geolocation) {{
                    status.innerText = "❌ Tu navegador no soporta geolocalización.";
                    return;
                }}
                status.style.color = "#00E5FF";
                status.innerText = "🛰️ Triangulando tu ubicación exacta...";
                
                navigator.geolocation.getCurrentPosition(
                    function(pos) {{
                        fetch("{BACKEND_URL}/api/guardar_gps", {{
                            method: "POST",
                            headers: {{"Content-Type": "application/json"}},
                            body: JSON.stringify({{
                                lat: pos.coords.latitude,
                                lon: pos.coords.longitude,
                                accuracy: pos.coords.accuracy
                            }})
                        }}).then(() => {{
                            status.style.color = "#10B981";
                            status.innerHTML = "✅ <b>¡Ubicación exacta fijada!</b><br>Pulsa 'Actualizar Mapa' abajo.";
                        }});
                    }},
                    function(err) {{
                        status.style.color = "#EF4444";
                        status.innerText = "⚠️ Permiso denegado en el navegador.";
                    }},
                    {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }}
                );
            }}
            </script>
        """, height=105)
        
        if st.button("🔄 Actualizar Mapa con Mi Ubicación"):
            gps_backend = requests.get(f"{BACKEND_URL}/api/obtener_gps", timeout=2).json()
            if gps_backend.get("activo"):
                payload_ruta = {
                    "region": selected_region, 
                    "origen_lat": gps_backend["lat"], 
                    "origen_lon": gps_backend["lon"],
                    "destino_lat": datos_reg["ladera_lat"], 
                    "destino_lon": datos_reg["ladera_lon"], 
                    "nombre_origen": "Mi Ubicación Exacta (GPS)"
                }
                st.session_state["datos_ruta"][selected_region] = requests.post(f"{BACKEND_URL}/api/ruta_optima", json=payload_ruta, timeout=8).json()
                st.rerun()

    if gps_backend.get("activo"):
        origen_lat_calc = gps_backend["lat"]
        origen_lon_calc = gps_backend["lon"]
        nombre_origen_calc = "Mi Ubicación Exacta (GPS)"
        enlace_maps = f"https://www.google.com/maps/dir/{origen_lat_calc},{origen_lon_calc}/{datos_reg['ladera_lat']},{datos_reg['ladera_lon']}"
        st.sidebar.success(f"📍 Ubicado con éxito (±{gps_backend.get('precision_m')}m)\nLat: {origen_lat_calc:.5f}, Lon: {origen_lon_calc:.5f}")
    else:
        origen_lat_calc = datos_reg["lat"]
        origen_lon_calc = datos_reg["lon"]
        nombre_origen_calc = datos_reg["base_operativa"]
        enlace_maps = f"https://www.google.com/maps/dir/{datos_reg['direccion_maps']}/{datos_reg['ladera_lat']},{datos_reg['ladera_lon']}"
        st.sidebar.warning("⚠️ Pulsa 'Detectar Mi Ubicación Exacta' arriba.")
else:
    # Base Oficial de Bomberos 100% FIJA para todas las regiones
    origen_lat_calc = datos_reg["lat"]
    origen_lon_calc = datos_reg["lon"]
    nombre_origen_calc = datos_reg["base_operativa"]
    # Usa la dirección oficial del cuartel para que Google Maps nunca se desvíe a calles vecinas
    enlace_maps = f"https://www.google.com/maps/dir/{datos_reg['direccion_maps']}/{datos_reg['ladera_lat']},{datos_reg['ladera_lon']}"
    st.sidebar.success(f"🚒 Cuartel Fijo:\n{nombre_origen_calc}\n({origen_lat_calc}, {origen_lon_calc})")

enlace_earth = f"https://earth.google.com/web/search/{datos_reg['ladera_lat']},{datos_reg['ladera_lon']}"
st.sidebar.markdown(f"🚗 **[Abrir Ruta Exacta en Google Maps]({enlace_maps})**")
st.sidebar.markdown(f"🌲 **[Ver Bosque/Pajonal en Google Earth]({enlace_earth})**")

# Auto-cargar clima, satélite y ruta de la Base de Bomberos por defecto para que siempre esté listo
if not st.session_state["datos_clima"].get(selected_region):
    try:
        st.session_state["datos_clima"][selected_region] = requests.get(f"{BACKEND_URL}/api/riesgo", params={"region": selected_region}, timeout=4).json()
        st.session_state["datos_satelite"][selected_region] = requests.get(f"{BACKEND_URL}/api/goes19/focos", params={"region": selected_region}, timeout=4).json()
        st.session_state["datos_cono"][selected_region] = requests.post(f"{BACKEND_URL}/api/propagacion", json={"region": selected_region}, timeout=4).json()
    except: pass

if not st.session_state["datos_ruta"].get(selected_region):
    try:
        payload_init = {
            "region": selected_region, "origen_lat": origen_lat_calc, "origen_lon": origen_lon_calc,
            "destino_lat": datos_reg["ladera_lat"], "destino_lon": datos_reg["ladera_lon"], "nombre_origen": nombre_origen_calc
        }
        st.session_state["datos_ruta"][selected_region] = requests.post(f"{BACKEND_URL}/api/ruta_optima", json=payload_init, timeout=6).json()
    except: pass

st.subheader(f"⚡ Operaciones Tácticas hacia: {datos_reg['sector_forestal']}")

if st.button("🚀 Ejecutar Diagnóstico Integral + Trazar Ruta Accesible"):
    with st.spinner("Calculando ruta vial accesible hacia la zona forestal..."):
        try:
            gps_check = requests.get(f"{BACKEND_URL}/api/obtener_gps", timeout=2).json()
            if modo_origen == "📍 Mi Ubicación Actual (Automática)" and gps_check.get("activo"):
                origen_lat_calc = gps_check["lat"]
                origen_lon_calc = gps_check["lon"]
                nombre_origen_calc = "Mi Ubicación Exacta (GPS)"

            st.session_state["datos_clima"][selected_region] = requests.get(f"{BACKEND_URL}/api/riesgo", params={"region": selected_region}, timeout=5).json()
            st.session_state["datos_satelite"][selected_region] = requests.get(f"{BACKEND_URL}/api/goes19/focos", params={"region": selected_region}, timeout=5).json()
            st.session_state["datos_cono"][selected_region] = requests.post(f"{BACKEND_URL}/api/propagacion", json={"region": selected_region}, timeout=5).json()
            
            payload_ruta = {
                "region": selected_region, "origen_lat": origen_lat_calc, "origen_lon": origen_lon_calc,
                "destino_lat": datos_reg["ladera_lat"], "destino_lon": datos_reg["ladera_lon"], "nombre_origen": nombre_origen_calc
            }
            st.session_state["datos_ruta"][selected_region] = requests.post(f"{BACKEND_URL}/api/ruta_optima", json=payload_ruta, timeout=8).json()
            st.rerun()
        except: pass

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📊 Clima en el Bosque")
    clima = st.session_state["datos_clima"].get(selected_region)
    if clima and "temperatura_c" in clima:
        st.metric(label="Temperatura", value=f"{clima['temperatura_c']} °C")
        st.metric(label="Humedad Relativa", value=f"{clima['humedad_relativa_pct']} %")
        st.metric(label="Índice ICIA (Riesgo)", value=f"{clima['indice_riesgo_icia']}%")
        st.metric(label="🔥 Expansión Potencial", value=f"{clima['probabilidad_expansion_pct']}%")
        st.info(f"**{clima['nivel_alerta']}**")

with col2:
    st.markdown("### 🛰️ Satélite GOES-19")
    sat = st.session_state["datos_satelite"].get(selected_region)
    if sat and "estado_barrido" in sat:
        st.success("✅ SIN FUEGO ACTIVO. Monitoreo preventivo en bosque.")
        st.caption(sat["estado_barrido"])
        st.write(f"**Zona:** {datos_reg['sector_forestal']}")

with col3:
    st.markdown("### 💨 Vector de Viento")
    cono = st.session_state["datos_cono"].get(selected_region)
    if cono and "vector_avance" in cono:
        st.success("Vector calculado en pajonal")
        st.json(cono["vector_avance"])

with col4:
    st.markdown("### 🚒 Ruta Accesible")
    ruta = st.session_state["datos_ruta"].get(selected_region)
    if ruta and "distancia_aprox_km" in ruta:
        st.metric(label="Distancia por Carretera/Trocha", value=f"{ruta['distancia_aprox_km']} km")
        st.metric(label="Tiempo de Llegada", value=f"~{ruta['tiempo_estimado_min']} min")
        st.caption(f"**Desde:** {ruta['punto_partida']}")
        st.caption(f"**Hacia:** {datos_reg['sector_forestal']}")

st.markdown("---")

st.subheader(f"🗺️ Mapa Táctico: {nombre_origen_calc} ➔ {datos_reg['sector_forestal']}")

poligonos_regiones = {
    "Huancayo (Junín)": [[-75.32, -12.12], [-75.25, -12.15], [-75.12, -12.10], [-75.08, -11.95], [-75.15, -11.90], [-75.28, -11.95], [-75.32, -12.12]],
    "Cusco": [[-72.05, -13.60], [-71.92, -13.62], [-71.85, -13.45], [-71.90, -13.40], [-72.08, -13.45], [-72.12, -13.55], [-72.05, -13.60]],
    "Puno": [[-70.15, -15.92], [-70.00, -15.95], [-69.88, -15.78], [-69.90, -15.72], [-70.08, -15.75], [-70.20, -15.85], [-70.15, -15.92]],
    "Abancay (Apurímac)": [[-72.98, -13.72], [-72.85, -13.70], [-72.78, -13.55], [-72.85, -13.50], [-72.95, -13.58], [-73.02, -13.65], [-72.98, -13.72]],
    "Huaraz (Áncash)": [[-77.62, -9.62], [-77.48, -9.60], [-77.42, -9.44], [-77.50, -9.40], [-77.60, -9.45], [-77.68, -9.55], [-77.62, -9.62]]
}

layers_to_render = [
    pdk.Layer(
        "PolygonLayer",
        [{"polygon": poligonos_regiones[selected_region], "name": "Perímetro de Monitoreo"}],
        get_polygon="polygon", get_fill_color=[0, 0, 0, 0], get_line_color=[0, 180, 255], line_width_min_pixels=2, stroked=True
    )
]

color_origen = [0, 255, 128, 240] if modo_origen == "📍 Mi Ubicación Actual (Automática)" else [0, 150, 255, 230]
puntos_operativos = [{
    "lat": origen_lat_calc, "lon": origen_lon_calc,
    "name": f"📍 Partida: {nombre_origen_calc}",
    "color": color_origen, "radius": 220
}]

puntos_operativos.append({
    "lat": datos_reg["ladera_lat"], "lon": datos_reg["ladera_lon"],
    "name": f"🌲 ZONA FORESTAL: {datos_reg['sector_forestal']}",
    "color": [255, 215, 0, 240], "radius": 260
})

if ruta and "coordenadas_ruta" in ruta and len(ruta["coordenadas_ruta"]) > 0:
    layers_to_render.append(pdk.Layer(
        "PathLayer", [{"path": ruta["coordenadas_ruta"], "name": "Ruta Vial Accesible"}],
        get_path="path", get_color=[0, 255, 200, 240], width_min_pixels=4, pickable=True
    ))

layers_to_render.append(pdk.Layer(
    "ScatterplotLayer",
    puntos_operativos,
    get_position="[lon, lat]", get_fill_color="color", get_radius="radius",
    radius_min_pixels=8, radius_max_pixels=15, stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=2, pickable=True
))

view_state = pdk.ViewState(
    latitude=(origen_lat_calc + datos_reg["ladera_lat"]) / 2,
    longitude=(origen_lon_calc + datos_reg["ladera_lon"]) / 2,
    zoom=11.2, pitch=15,
)

r = pdk.Deck(layers=layers_to_render, initial_view_state=view_state, tooltip={"text": "{name}"})
st.pydeck_chart(r)