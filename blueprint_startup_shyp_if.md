# 🔥 SHYp-IF: Sistema Híbrido Predictivo de Incendios Forestales
**De Piloto Geoespacial (Cero Costo) a Startup DeepTech en los Andes**

---

## 1. Propuesta de Valor y Enfoque de Startup (Para Concursos y Fondos)

* **El Problema:** En el Perú (y especialmente en la sierra central como Junín/Huancayo), más del 90% de los incendios forestales son de origen antropogénico (quemas agrícolas o *rozo*) potenciados por sequías y vientos andinos. Los sistemas actuales del Estado solo reportan incendios cuando ya quemaron decenas de hectáreas.
* **La Solución (SHYp-IF):** Una plataforma SaaS + IoT que **anticipa** qué laderas están listas para arder horas antes de que inicie el fuego, **detecta** anomalías térmicas cada 10 minutos vía satélite y **predice** hacia dónde correrá la llama mediante vectores de viento y topografía para guiar a las brigadas.
* **Ventaja Competitiva Injusta (Moat Tecnológico):**
  1. **Fase 1 (Software Puro):** Cruce del algoritmo FDC del satélite **GOES-19**, microclima de alta resolución, sequedad vegetal (**NDMI**) y el índice de rayos secos/vientos de tu sistema hermano (**SHYp-TA**).
  2. **Fase 2 (Hardware Propio Patentable):** Nodos forestales terrestres alimentados y sensados por **Generadores Triboeléctricos (TENG)** que operan con el viento andino sin depender de paneles solares (que se tapan con humo/ceniza) ni baterías que fallan por heladas.

---

## 2. Capas Visuales del Mapa en la App Móvil (Mapas de Calor + Anillos)

Manteniendo la identidad visual de tu app de tormentas eléctricas, el mapa interactivo tendrá **3 capas superpuestas**:

1. **Mapa de Calor Predictivo (Grid de Ignición Pre-Fuego):**
   * Polígonos semitransparentes (Verde $\rightarrow$ Amarillo $\rightarrow$ Rojo) sobre el Valle del Mantaro y zonas críticas (Acopalca, Huaytapallana, Sapallanga, Concepción, Jauja).
   * Muestra dónde está el pastizal (*ichu* / eucalipto) seco y con viento fuerte **antes de que exista fuego**.
2. **Anillos Concéntricos de Vigilancia (5 km, 15 km, 30 km):**
   * Centrados en las comunidades, bosques protegidos o infraestructuras críticas registradas.
3. **Marcadores Térmicos + Cono de Propagación (Post-Ignición):**
   * Puntos de calor en vivo (GOES-19 / NASA FIRMS) con un **cono direccional sombreado** que indica hacia qué ladera avanza el fuego según la dirección del viento y la pendiente del cerro.

---

## 3. Fórmulas del Motor Predictivo (Backend en Python)

### A. Índice Compuesto de Ignición Andina ($\text{ICIA}$)
Calculado cada hora (de $0\%$ a $100\%$) para pintar el Mapa de Calor Preventivo:

$$\text{ICIA} = 0.35(\text{NDMI}_{\text{sequedad}}) + 0.30(\text{Meteo}_{\text{viento+VPD}}) + 0.20(\text{Antropo}_{\text{rutas}}) + 0.15(\text{GLM}_{\text{rayos}})$$

* $\text{NDMI}_{\text{sequedad}}$: Índice de estrés hídrico de la vegetación (Sentinel-2 / GOES-19 Bandas 2, 3 y 6).
* $\text{Meteo}_{\text{viento+VPD}}$: Velocidad del viento, baja humedad relativa y Déficit de Presión de Vapor (API Open-Meteo).
* $\text{Antropo}_{\text{rutas}}$: Proximidad a parcelas agrícolas y caminos rurales (OpenStreetMap).
* $\text{GLM}_{\text{rayos}}$: Actividad eléctrica sin precipitación significativa.

### B. Velocidad y Vector de Propagación ($R_{\text{fuego}}$)
Para dibujar el cono de avance cuando se detecta un foco térmico:

$$R_{\text{fuego}} = R_0 \cdot (1 + \Phi_{\text{viento}} + \Phi_{\text{pendiente}})$$

Donde $R_0$ es la velocidad base de combustión del *ichu*/matorral, $\Phi_{\text{viento}}$ el factor de empuje eólico y $\Phi_{\text{pendiente}}$ el factor topográfico (el fuego duplica su velocidad por cada $10^\circ$ de pendiente positiva).

---

## 4. Arquitectura Cloud "Cero Peso en Laptop" (24/7)

El proyecto es **100% independiente** de tu proyecto de tormentas eléctricas:

* **Entorno Local (VS Code):** Solo almacena el código fuente (menos de 5 MB) para hacer `git push` a un nuevo repositorio de GitHub (`shyp-if`).
* **Servidor Cloud (Render / Worker 24/7):** Descarga en memoria RAM (`io.BytesIO`) los recortes de GOES-19 (`ABI-L2-FDCC`) cada 10 minutos, extrae las coordenadas de Junín y descarta el archivo pesado inmediatamente.
* **Base de Datos Cloud con Auto-Purga (Supabase / PostgreSQL):**
  * Tabla `monitoreo_riesgo_horario`: Guarda el mapa de calor del día y se comprime a medianoche.
  * Tabla `alertas_focos_calor`: Guarda únicamente los eventos reales de fuego detectados.
  * Tabla `resumen_historico_diario`: Guarda 1 fila por día para métricas de validación científica y pitch de startup.

---

## 5. Hoja de Ruta de Implementación (Roadmap)

* **Etapa 1 (Piloto Geoespacial - Costo S/ 0):**
  * Creación del repositorio independiente en VS Code.
  * Script Python de ingesta GOES-19 (`FDCC`) + NASA FIRMS + Open-Meteo.
  * Despliegue en la nube y adaptación de la App Móvil con Mapas de Calor y Anillos.
* **Etapa 2 (Validación y Tracción para Concursos):**
  * *Backtesting* con incendios reales ocurridos en Huancayo/Junín para demostrar precisión predictiva.
  * Piloto en vivo monitoreando 3 zonas críticas del Valle del Mantaro.
* **Etapa 3 (Escalamiento Hardware + Fondos Startup Perú / ProInnóvate):**
  * Integración de nodos IoT LoRaWAN en quebradas ciegas al satélite, autoalimentados con tu prototipo **TENG** como cosechador de energía eólica y sensor anemométrico sin batería.