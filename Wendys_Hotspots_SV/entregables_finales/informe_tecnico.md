# Informe Tecnico: Deteccion de Hotspots Comerciales y Evaluacion de Apertura de Wendy's en San Salvador

## 1. Resumen Ejecutivo
El presente estudio desarrolla un prototipo academico de analitica geoespacial y Machine Learning aplicado a las **11 sucursales** de Wendy's identificadas dentro del departamento de San Salvador (`ISO3166-2 = SV-SS`). Mediante una arquitectura hibrida de aprendizaje no supervisado (**K-Means**) y supervisado (**KNN con metrica Haversine**), el sistema segmenta los polos comerciales existentes y evalua la viabilidad espacial de nuevas ubicaciones candidatas.

## 2. Arquitectura del Pipeline de Datos
1. **Extraccion Geoespacial (Overpass API):** Consulta automatizada de nodos, vias y relaciones etiquetadas como `fast_food` o `restaurant` con coincidencia en `name` o `brand` para Wendy's dentro de los limites administrativos de San Salvador.
2. **Limpieza y Validacion:** Filtrado estricto dentro de la caja delimitadora departamental (`latitud` en `[13.45, 14.08]` y `longitud` en `[-89.30, -89.00]`), eliminacion de duplicados exactos por identificador OSM y coordenadas, y preservacion integra de valores faltantes (`NaN`) sin imputacion artificial.
3. **Segmentacion No Supervisada (K-Means):** Evaluacion de compactacion (Inercia) y separacion inter-cluster (Coeficiente de Silueta).
4. **Clasificacion Supervisada Geodesica (KNN Haversine):** Transformacion de coordenadas a radianes y calculo de distancias reales sobre la curvatura terrestre (`R = 6,371 km`).

## 3. Resultados del Agrupamiento K-Means
La evaluacion de distintos valores de `K` arrojo las siguientes metricas de desempeno:

| K | Inercia | Coeficiente de Silueta |
| :---: | :---: | :---: |
| 2 | 0.004706 | 0.5614 |
| 3 | 0.002748 | 0.5114 |
| 4 | 0.001287 | 0.4906 |
| 5 | 0.000883 | 0.3381 |
| 6 | 0.000565 | 0.2944 |
| 7 | 0.000333 | 0.324 |

- **Configuracion seleccionada:** `K = 3` polos comerciales con un Coeficiente de Silueta de **0.5114**.
- **Umbral de densidad:** El promedio de establecimientos por cluster es de **3.67 locales**, criterio utilizado para etiquetar cada grupo en `Alta Concentracion` o `Baja Concentracion`.

## 4. Resultados de Clasificacion KNN con Distancia Haversine
Para evitar sesgos de distorsion planar y evaluar el poder de generalizacion en muestras espaciales acotadas, se aplico validacion cruzada **Leave-One-Out (LOO)** sobre valores impares de `k`:

| k (Vecinos Impares) | Aciertos | Exactitud LOO |
| :---: | :---: | :---: |
| 1 | 10 / 11 | 90.91% |
| 3 | 10 / 11 | 90.91% |
| 5 | 10 / 11 | 90.91% |
| 7 | 10 / 11 | 90.91% |
| 9 | 10 / 11 | 90.91% |

- **Modelo seleccionado:** `k = 3` vecinos mas cercanos, alcanzando una exactitud Leave-One-Out de **90.91%**.

## 5. Simulacion de Nueva Ubicacion Propuesta
Se evaluo una coordenada candidata en el corredor comercial Paseo General Escalon (`13.7015, -89.231`):
- **Clasificacion predicha:** `Alta Concentracion`
- **Vecinos mas cercanos identificados:**

| Orden | Sucursal Cercana | Categoria del Cluster | Distancia Haversine |
| :---: | :--- | :--- | :---: |
| 1 | Wendy's | Alta Concentracion | 0.044 km |
| 2 | Wendy's | Alta Concentracion | 1.038 km |
| 3 | Wendy's | Alta Concentracion | 1.713 km |

## 6. Limitaciones Tecnicas y Metodologicas
- **Cobertura de OpenStreetMap:** Los datos provienen de mapeo colaborativo voluntario; la ausencia de metadatos secundarios (horarios, telefono) o eventuales sucursales no mapeadas reflejan el estado de contribucion comunitaria y no un censo comercial oficial.
- **Distancia Geodesica vs. Red Vial:** La metrica Haversine mide distancia en linea recta sobre la esfera terrestre y no tiempos reales de traslado vehicular ni sentido de vias.
- **Variables Socioeconomicas:** El modelo evalua exclusivamente densidad espacial; decisiones reales de inversion requieren incorporar flujo peatonal/vehicular, poder adquisitivo, costos de arrendamiento y riesgo de canibalizacion.