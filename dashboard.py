import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="SHYp-IF Dashboard",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 SHYp-IF: Sistema Híbrido Predictivo de Incendios Forestales")
st.markdown("**Valle del Mantaro - Huancayo | Monitoreo en Tiempo Real**")
st.markdown("---")

# URL de nuestro backend en Flask local
BACKEND_URL = "http://127.0.0.1:5000"

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Variables Meteorológicas & Riesgo (ICIA)")
    if st.button("Consultar Estado del Clima y Riesgo"):
        try:
            res = requests.get(f"{BACKEND_URL}/api/riesgo", timeout=5)
            if res.status_code == 200:
                data = res.json()
                st.success("Datos obtenidos correctamente desde el backend")
                st.metric(label="Temperatura Actual", value=f"{data.get('temperatura_c')} °C")
                st.metric(label="Humedad Relativa", value=f"{data.get('humedad_relativa_pct')} %")
                st.metric(label="Velocidad del Viento", value=f"{data.get('velocidad_viento_kmh')} km/h")
                st.metric(label="Índice de Riesgo (ICIA)", value=f"{data.get('indice_riesgo_icia')}%")
                st.info(f"Nivel de Alerta: **{data.get('nivel_alerta')}**")
            else:
                st.error("Error al conectar con la API de riesgo.")
        except Exception as e:
            st.error(f"No se pudo conectar al servidor Flask local: {e}")

with col2:
    st.subheader("🛰️ Monitoreo Satelital GOES-19")
    if st.button("Verificar Focos de Calor"):
        try:
            res = requests.get(f"{BACKEND_URL}/api/goes19/focos", timeout=5)
            if res.status_code == 200:
                data = res.json()
                st.warning(f"Estado: {data.get('estado_barrido')}")
                st.write(f"**Instrumento:** {data.get('instrumento')}")
                st.write(f"**Producto:** {data.get('producto')}")
                st.json(data.get('coordenadas_focos'))
            else:
                st.error("Error al consultar el satélite.")
        except Exception as e:
            st.error(f"Error de conexión: {e}")

st.markdown("---")
st.subheader("💨 Simulación de Cono de Propagación por Viento")
if st.button("Calcular Vector de Avance del Fuego"):
    try:
        res = requests.post(f"{BACKEND_URL}/api/propagacion", json={"lat": -12.0464, "lon": -75.2049}, timeout=5)
        if res.status_code == 200:
            prop = res.json()
            st.success("Cálculo vectorial completado:")
            st.json(prop)
        else:
            st.error("Error al calcular la propagación.")
    except Exception as e:
        st.error(f"Error de conexión: {e}")