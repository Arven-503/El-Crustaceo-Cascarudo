import os
import json
import numpy as np
import pandas as pd
import folium
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneOut

carpeta_salida = "entregables_finales"
os.makedirs(carpeta_salida, exist_ok=True)

df = pd.read_csv("wendys_san_salvador_limpio.csv")
n_muestras = len(df)
X = df[["latitud", "longitud"]].to_numpy()

max_k = min(7, n_muestras - 1)
resultados_k = []
for k in range(2, max_k + 1):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    etiquetas = km.fit_predict(X)
    resultados_k.append({
        "k": k,
        "inercia": round(float(km.inertia_), 6),
        "silueta": round(float(silhouette_score(X, etiquetas)), 4)
    })

candidatos = [r for r in resultados_k if r["k"] >= 3] if max_k >= 3 else resultados_k
mejor_k_cfg = max(candidatos, key=lambda x: x["silueta"])
mejor_k = mejor_k_cfg["k"]
mejor_silueta = mejor_k_cfg["silueta"]

kmeans = KMeans(n_clusters=mejor_k, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X)
centroides = kmeans.cluster_centers_

conteo_clusters = df["cluster"].value_counts()
promedio_locales = float(conteo_clusters.mean())
df["locales_en_cluster"] = df["cluster"].map(conteo_clusters)
df["categoria_densidad"] = np.where(
    df["locales_en_cluster"] > promedio_locales,
    "Alta Concentracion",
    "Baja Concentracion"
)

df["latitud_rad"] = np.radians(df["latitud"])
df["longitud_rad"] = np.radians(df["longitud"])

dist_centroide_km = []
for _, fila in df.iterrows():
    cid = int(fila["cluster"])
    lat1, lon1 = np.radians(fila["latitud"]), np.radians(fila["longitud"])
    lat2, lon2 = np.radians(centroides[cid][0]), np.radians(centroides[cid][1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    dist_centroide_km.append(round(float(6371.0 * c), 3))

df["distancia_centroide_km"] = dist_centroide_km

ruta_csv = os.path.join(carpeta_salida, "dataset_final_wendys_san_salvador.csv")
df.to_csv(ruta_csv, index=False, encoding="utf-8")

X_rad = df[["latitud_rad", "longitud_rad"]].to_numpy()
y = np.array(df["categoria_densidad"].tolist())

valores_k_knn = [k for k in range(1, n_muestras, 2)]
loo = LeaveOneOut()
resultados_loo = []

for k in valores_k_knn:
    aciertos = 0
    for train_idx, test_idx in loo.split(X_rad):
        knn_cv = KNeighborsClassifier(n_neighbors=k, metric="haversine")
        knn_cv.fit(X_rad[train_idx], y[train_idx])
        if knn_cv.predict(X_rad[test_idx])[0] == y[test_idx][0]:
            aciertos += 1
    resultados_loo.append({
        "k": k,
        "aciertos": aciertos,
        "exactitud": round(aciertos / n_muestras, 4)
    })

mejor_knn_cfg = max(
    resultados_loo,
    key=lambda r: (r["exactitud"], 1 if r["k"] == 3 else 0)
)
mejor_k_knn = mejor_knn_cfg["k"]
mejor_acc_loo = mejor_knn_cfg["exactitud"]

knn_final = KNeighborsClassifier(n_neighbors=mejor_k_knn, metric="haversine")
knn_final.fit(X_rad, y)

lat_propuesta = 13.70150
lon_propuesta = -89.23100
punto_propuesto_rad = np.radians([[lat_propuesta, lon_propuesta]])
pred_propuesta = knn_final.predict(punto_propuesto_rad)[0]
dist_rad, idx_vecinos = knn_final.kneighbors(punto_propuesto_rad)
dist_km = dist_rad[0] * 6371.0

colores_cluster = ["blue", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen"]

mapa = folium.Map(
    location=[lat_propuesta, lon_propuesta],
    zoom_start=12,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Street Map"
)

for cid in range(mejor_k):
    c_lat, c_lon = centroides[cid]
    color_zona = colores_cluster[cid % len(colores_cluster)]
    n_loc = int(conteo_clusters.get(cid, 0))
    cat_zona = "Alta Concentracion" if n_loc > promedio_locales else "Baja Concentracion"
    folium.Circle(
        location=[c_lat, c_lon],
        radius=1100,
        color=color_zona,
        fill=True,
        fill_opacity=0.10
    ).add_to(mapa)
    folium.Marker(
        location=[c_lat, c_lon],
        popup=f"<b>Centroide Cluster {cid}</b><br>Locales: {n_loc}<br>Zona: {cat_zona}",
        tooltip=f"Centroide Cluster {cid}",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(mapa)

for _, fila in df.iterrows():
    cid = int(fila["cluster"])
    color_pin = colores_cluster[cid % len(colores_cluster)]
    nombre_txt = fila["nombre"] if pd.notna(fila["nombre"]) else "Sin nombre"
    popup_html = (
        f"<b>{nombre_txt}</b><br>"
        f"Cluster: {cid} ({fila['categoria_densidad']})<br>"
        f"Coords: {fila['latitud']:.5f}, {fila['longitud']:.5f}"
    )
    folium.Marker(
        location=[fila["latitud"], fila["longitud"]],
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"{nombre_txt} (Cluster {cid})",
        icon=folium.Icon(color=color_pin, icon="cutlery", prefix="fa")
    ).add_to(mapa)

detalle_vecinos_md = []
for orden, (idx, d_km) in enumerate(zip(idx_vecinos[0], dist_km), start=1):
    v_lat = float(df.loc[idx, "latitud"])
    v_lon = float(df.loc[idx, "longitud"])
    v_nom = df.loc[idx, "nombre"] if pd.notna(df.loc[idx, "nombre"]) else "Sin nombre"
    v_cat = df.loc[idx, "categoria_densidad"]
    folium.PolyLine(
        locations=[[lat_propuesta, lon_propuesta], [v_lat, v_lon]],
        color="crimson",
        weight=3,
        opacity=0.85,
        dash_array="6, 6",
        tooltip=f"Vecino {orden}: {v_nom} ({d_km:.2f} km)"
    ).add_to(mapa)
    detalle_vecinos_md.append(f"| {orden} | {v_nom} | {v_cat} | {d_km:.3f} km |")

folium.Marker(
    location=[lat_propuesta, lon_propuesta],
    popup=(
        f"<b>Nueva Ubicacion Propuesta</b><br>"
        f"Prediccion KNN: {pred_propuesta}<br>"
        f"Coords: {lat_propuesta:.5f}, {lon_propuesta:.5f}"
    ),
    tooltip=f"Ubicacion Propuesta ({pred_propuesta})",
    icon=folium.Icon(color="red", icon="flag", prefix="fa")
).add_to(mapa)

leyenda_html = """
<div style="position: fixed; bottom: 30px; left: 30px; width: 270px; z-index:9999;
background-color: white; border: 2px solid #444; border-radius: 8px; padding: 12px;
font-family: Arial, sans-serif; font-size: 12px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
<b>Hotspots Comerciales Wendys SV</b><br><br>
<span style="color: red;">&#9873;</span> Nueva ubicacion propuesta<br>
<span style="color: black;">&#9733;</span> Centroide polo comercial (K-Means)<br>
<span style="color: blue;">&#9679;</span> Sucursales agrupadas por cluster<br>
<span style="color: crimson;">---</span> Distancia Haversine a vecinos KNN
</div>
"""
mapa.get_root().html.add_child(folium.Element(leyenda_html))

ruta_mapa = os.path.join(carpeta_salida, "mapa_final_hotspots_wendys.html")
mapa.save(ruta_mapa)

diccionario_lineas = [
    "# Diccionario de Datos - Hotspots Comerciales Wendy's San Salvador",
    "",
    "Este documento describe la estructura del archivo `dataset_final_wendys_san_salvador.csv` generado tras el proceso de extraccion desde OpenStreetMap (Overpass API), limpieza espacial y modelado con Machine Learning.",
    "",
    "| Variable | Tipo de Dato | Origen / Formula | Descripcion |",
    "| :--- | :--- | :--- | :--- |",
    "| `osm_type` | Texto (`string`) | OpenStreetMap | Tipo de geometria registrada (`node`, `way` o `relation`). |",
    "| `osm_id` | Entero (`int64`) | OpenStreetMap | Identificador unico del elemento dentro de la base de datos de OSM. |",
    "| `nombre` | Texto (`string`) | Etiqueta `name` (OSM) | Nombre comercial registrado del establecimiento. |",
    "| `marca` | Texto (`string`) | Etiqueta `brand` (OSM) | Marca comercial asociada al establecimiento. |",
    "| `tipo_local` | Texto (`string`) | Etiqueta `amenity` (OSM) | Clasificacion gastronomica (`fast_food` o `restaurant`). |",
    "| `latitud` | Decimal (`float64`) | Coordenada WGS84 | Latitud geografica en grados decimales (rango validado: 13.45 a 14.08). |",
    "| `longitud` | Decimal (`float64`) | Coordenada WGS84 | Longitud geografica en grados decimales (rango validado: -89.30 a -89.00). |",
    "| `direccion` | Texto (`string`) | Etiqueta `addr:street` | Calle o avenida registrada (respeta valores nulos si no existen en OSM). |",
    "| `ciudad` | Texto (`string`) | Etiqueta `addr:city` | Municipio o ciudad registrada (respeta valores nulos sin imputacion). |",
    "| `horario` | Texto (`string`) | Etiqueta `opening_hours` | Horario de atencion reportado en OSM (opcional). |",
    "| `telefono` | Texto (`string`) | Etiqueta `phone` | Numero telefonico reportado en OSM (opcional). |",
    "| `sitio_web` | Texto (`string`) | Etiqueta `website` | URL oficial reportada en OSM (opcional). |",
    "| `cluster` | Entero (`int32`) | Modelo K-Means | Identificador numerico del polo comercial asignado (`0` a `K-1`). |",
    "| `locales_en_cluster` | Entero (`int64`) | Conteo por grupo | Numero total de sucursales pertenecientes al mismo cluster. |",
    "| `categoria_densidad` | Texto (`string`) | Regla de umbral | Etiqueta supervisada: `Alta Concentracion` si supera el promedio de locales por cluster, o `Baja Concentracion` en caso contrario. |",
    "| `latitud_rad` | Decimal (`float64`) | `np.radians(latitud)` | Latitud transformada a radianes para calculo esferico Haversine. |",
    "| `longitud_rad` | Decimal (`float64`) | `np.radians(longitud)` | Longitud transformada a radianes para calculo esferico Haversine. |",
    "| `distancia_centroide_km` | Decimal (`float64`) | Formula Haversine | Distancia geodesica en kilometros desde la sucursal hasta el centroide de su cluster. |"
]
ruta_dicc = os.path.join(carpeta_salida, "diccionario_datos.md")
with open(ruta_dicc, "w", encoding="utf-8") as f:
    f.write("\n".join(diccionario_lineas))

tabla_k_md = [
    "| K | Inercia | Coeficiente de Silueta |",
    "| :---: | :---: | :---: |"
]
for r in resultados_k:
    tabla_k_md.append(f"| {r['k']} | {r['inercia']} | {r['silueta']} |")

tabla_loo_md = [
    "| k (Vecinos Impares) | Aciertos | Exactitud LOO |",
    "| :---: | :---: | :---: |"
]
for r in resultados_loo:
    tabla_loo_md.append(f"| {r['k']} | {r['aciertos']} / {n_muestras} | {r['exactitud']:.2%} |")

informe_lineas = [
    "# Informe Tecnico: Deteccion de Hotspots Comerciales y Evaluacion de Apertura de Wendy's en San Salvador",
    "",
    "## 1. Resumen Ejecutivo",
    f"El presente estudio desarrolla un prototipo academico de analitica geoespacial y Machine Learning aplicado a las **{n_muestras} sucursales** de Wendy's identificadas dentro del departamento de San Salvador (`ISO3166-2 = SV-SS`). Mediante una arquitectura hibrida de aprendizaje no supervisado (**K-Means**) y supervisado (**KNN con metrica Haversine**), el sistema segmenta los polos comerciales existentes y evalua la viabilidad espacial de nuevas ubicaciones candidatas.",
    "",
    "## 2. Arquitectura del Pipeline de Datos",
    "1. **Extraccion Geoespacial (Overpass API):** Consulta automatizada de nodos, vias y relaciones etiquetadas como `fast_food` o `restaurant` con coincidencia en `name` o `brand` para Wendy's dentro de los limites administrativos de San Salvador.",
    "2. **Limpieza y Validacion:** Filtrado estricto dentro de la caja delimitadora departamental (`latitud` en `[13.45, 14.08]` y `longitud` en `[-89.30, -89.00]`), eliminacion de duplicados exactos por identificador OSM y coordenadas, y preservacion integra de valores faltantes (`NaN`) sin imputacion artificial.",
    "3. **Segmentacion No Supervisada (K-Means):** Evaluacion de compactacion (Inercia) y separacion inter-cluster (Coeficiente de Silueta).",
    "4. **Clasificacion Supervisada Geodesica (KNN Haversine):** Transformacion de coordenadas a radianes y calculo de distancias reales sobre la curvatura terrestre (`R = 6,371 km`).",
    "",
    "## 3. Resultados del Agrupamiento K-Means",
    "La evaluacion de distintos valores de `K` arrojo las siguientes metricas de desempeno:",
    "",
    *tabla_k_md,
    "",
    f"- **Configuracion seleccionada:** `K = {mejor_k}` polos comerciales con un Coeficiente de Silueta de **{mejor_silueta}**.",
    f"- **Umbral de densidad:** El promedio de establecimientos por cluster es de **{promedio_locales:.2f} locales**, criterio utilizado para etiquetar cada grupo en `Alta Concentracion` o `Baja Concentracion`.",
    "",
    "## 4. Resultados de Clasificacion KNN con Distancia Haversine",
    "Para evitar sesgos de distorsion planar y evaluar el poder de generalizacion en muestras espaciales acotadas, se aplico validacion cruzada **Leave-One-Out (LOO)** sobre valores impares de `k`:",
    "",
    *tabla_loo_md,
    "",
    f"- **Modelo seleccionado:** `k = {mejor_k_knn}` vecinos mas cercanos, alcanzando una exactitud Leave-One-Out de **{mejor_acc_loo:.2%}**.",
    "",
    "## 5. Simulacion de Nueva Ubicacion Propuesta",
    f"Se evaluo una coordenada candidata en el corredor comercial Paseo General Escalon (`{lat_propuesta}, {lon_propuesta}`):",
    f"- **Clasificacion predicha:** `{pred_propuesta}`",
    "- **Vecinos mas cercanos identificados:**",
    "",
    "| Orden | Sucursal Cercana | Categoria del Cluster | Distancia Haversine |",
    "| :---: | :--- | :--- | :---: |",
    *detalle_vecinos_md,
    "",
    "## 6. Limitaciones Tecnicas y Metodologicas",
    "- **Cobertura de OpenStreetMap:** Los datos provienen de mapeo colaborativo voluntario; la ausencia de metadatos secundarios (horarios, telefono) o eventuales sucursales no mapeadas reflejan el estado de contribucion comunitaria y no un censo comercial oficial.",
    "- **Distancia Geodesica vs. Red Vial:** La metrica Haversine mide distancia en linea recta sobre la esfera terrestre y no tiempos reales de traslado vehicular ni sentido de vias.",
    "- **Variables Socioeconomicas:** El modelo evalua exclusivamente densidad espacial; decisiones reales de inversion requieren incorporar flujo peatonal/vehicular, poder adquisitivo, costos de arrendamiento y riesgo de canibalizacion."
]
ruta_informe = os.path.join(carpeta_salida, "informe_tecnico.md")
with open(ruta_informe, "w", encoding="utf-8") as f:
    f.write("\n".join(informe_lineas))

guion_lineas = [
    "# Guion de Exposicion Academica (Duracion estimada: 8 - 10 minutos)",
    "",
    "## Bloque 1: Apertura y Planteamiento del Problema (1.5 min)",
    "- **Idea clave:** Elegir donde abrir una nueva sucursal de comida rapida requiere equilibrar dos fuerzas: aprovechar zonas de alta demanda comercial y evitar la canibalizacion entre locales cercanos.",
    "- **Objetivo:** Construir un prototipo reproducible de Machine Learning geoespacial para analizar la distribucion de Wendy's en el departamento de San Salvador y evaluar ubicaciones candidatas.",
    "",
    "## Bloque 2: Ingenieria de Datos y Limpieza Espacial (1.5 min)",
    "- **Fuente de datos:** Extraccion en tiempo real desde OpenStreetMap mediante Overpass API filtrando el codigo administrativo `ISO3166-2 = SV-SS`.",
    f"- **Calidad del dato:** Se validaron rangos geograficos estrictos de San Salvador, se eliminaron duplicados y se respetaron los valores nulos en atributos opcionales sin inventar informacion, consolidando **{n_muestras} registros** limpios.",
    "",
    "## Bloque 3: Segmentacion de Polos Comerciales con K-Means (2 min)",
    f"- **Explicacion:** Aplicamos K-Means para descubrir agrupamientos naturales en el Area Metropolitana de San Salvador, evaluando Inercia y Coeficiente de Silueta.",
    f"- **Hallazgo:** Con `K = {mejor_k}` (Silueta = `{mejor_silueta}`), identificamos los polos comerciales principales y definimos un umbral objetivo basado en el promedio de `{promedio_locales:.2f}` locales por cluster para clasificar zonas de `Alta Concentracion` vs `Baja Concentracion`.",
    "",
    "## Bloque 4: Clasificacion Geodesica con KNN Haversine (2 min)",
    "- **Por que Haversine:** A diferencia de la distancia euclidiana tradicional, la formula Haversine convierte latitud y longitud a radianes y calcula kilometros reales sobre la curvatura de la Tierra (`R = 6,371 km`).",
    f"- **Validacion:** Mediante Leave-One-Out (LOO), el modelo con `k = {mejor_k_knn}` obtuvo una exactitud de **{mejor_acc_loo:.2%}**. Al evaluar un punto candidato en Paseo General Escalon (`{lat_propuesta}, {lon_propuesta}`), el sistema lo clasifica como **{pred_propuesta}** y traza las distancias exactas a sus vecinos.",
    "",
    "## Bloque 5: Demostracion en Vivo y Limitaciones (2 min)",
    "- **Demo en Streamlit:** Mostrar como el usuario puede mover las coordenadas en la barra lateral, cambiar `K` y `k` en tiempo real, y visualizar las lineas punteadas hacia los vecinos cercanos.",
    "- **Rigor academico (Limitaciones):** Aclarar que OpenStreetMap es una fuente colaborativa y que el prototipo mide proximidad espacial, sirviendo como herramienta de pre-seleccion que debe complementarse con estudios de trafico vehicular y costos operativos.",
    "",
    "## Posibles Preguntas del Jurado y Respuestas Clave",
    "1. **Por que usaron Leave-One-Out en lugar de Train/Test Split tradicional?**",
    "   *Respuesta:* Porque al trabajar con una muestra acotada de establecimientos reales en un departamento especifico, Leave-One-Out aprovecha el maximo de informacion disponible en cada iteracion sin depender de una particion aleatoria.",
    "2. **Por que convertir coordenadas a radianes en KNN?**",
    "   *Respuesta:* Porque la implementacion de la metrica `haversine` en scikit-learn exige entradas en radianes para aplicar correctamente las funciones trigonometricas esfericas antes de multiplicar por el radio terrestre (6,371 km)."
]
ruta_guion = os.path.join(carpeta_salida, "guion_exposicion.md")
with open(ruta_guion, "w", encoding="utf-8") as f:
    f.write("\n".join(guion_lineas))

celdas_notebook = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Analisis Geoespacial de Hotspots Comerciales: Wendy's San Salvador\n",
            "Prototipo academico de Machine Learning (K-Means + KNN con distancia Haversine)."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import pandas as pd\n",
            "import numpy as np\n",
            "import folium\n",
            "from sklearn.cluster import KMeans\n",
            "from sklearn.metrics import silhouette_score\n",
            "from sklearn.neighbors import KNeighborsClassifier\n",
            "from sklearn.model_selection import LeaveOneOut\n",
            "\n",
            "df = pd.read_csv('../wendys_san_salvador_limpio.csv')\n",
            "print(f'Total de sucursales cargadas: {len(df)}')\n",
            "df.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Agrupamiento Espacial con K-Means\n",
            "Evaluacion de Inercia y Coeficiente de Silueta para identificar polos comerciales."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "X = df[['latitud', 'longitud']].to_numpy()\n",
            "for k in range(2, min(7, len(df))):\n",
            "    km = KMeans(n_clusters=k, random_state=42, n_init=10)\n",
            "    labels = km.fit_predict(X)\n",
            "    print(f'K={k} | Inercia={km.inertia_:.6f} | Silueta={silhouette_score(X, labels):.4f}')\n",
            "\n",
            f"kmeans = KMeans(n_clusters={mejor_k}, random_state=42, n_init=10)\n",
            "df['cluster'] = kmeans.fit_predict(X)\n",
            "conteo = df['cluster'].value_counts()\n",
            "promedio = conteo.mean()\n",
            "df['categoria_densidad'] = np.where(df['cluster'].map(conteo) > promedio, 'Alta Concentracion', 'Baja Concentracion')\n",
            "df[['nombre', 'latitud', 'longitud', 'cluster', 'categoria_densidad']]"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Clasificacion Supervisada con KNN Haversine y Validacion Leave-One-Out"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "X_rad = np.radians(df[['latitud', 'longitud']].to_numpy())\n",
            "y = np.array(df['categoria_densidad'].tolist())\n",
            "loo = LeaveOneOut()\n",
            "\n",
            "for k in range(1, len(df), 2):\n",
            "    aciertos = 0\n",
            "    for train_idx, test_idx in loo.split(X_rad):\n",
            "        knn = KNeighborsClassifier(n_neighbors=k, metric='haversine')\n",
            "        knn.fit(X_rad[train_idx], y[train_idx])\n",
            "        if knn.predict(X_rad[test_idx])[0] == y[test_idx][0]:\n",
            "            aciertos += 1\n",
            "    print(f'k={k} | Exactitud LOO: {aciertos/len(df):.2%}')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. Evaluacion de Nueva Ubicacion Propuesta"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            f"knn_final = KNeighborsClassifier(n_neighbors={mejor_k_knn}, metric='haversine')\n",
            "knn_final.fit(X_rad, y)\n",
            "\n",
            f"punto_nuevo = np.radians([[{lat_propuesta}, {lon_propuesta}]])\n",
            "pred = knn_final.predict(punto_nuevo)[0]\n",
            "dist_rad, indices = knn_final.kneighbors(punto_nuevo)\n",
            "dist_km = dist_rad[0] * 6371.0\n",
            "\n",
            "print('Prediccion:', pred)\n",
            "for idx, d in zip(indices[0], dist_km):\n",
            "    print(f\"{df.loc[idx, 'nombre']} -> {d:.3f} km\")"
        ]
    }
]

notebook_obj = {
    "cells": celdas_notebook,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.14"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

ruta_nb = os.path.join(carpeta_salida, "proyecto_hotspots_wendys_sv.ipynb")
with open(ruta_nb, "w", encoding="utf-8") as f:
    json.dump(notebook_obj, f, indent=2, ensure_ascii=False)

print("--- ENTREGABLES FINALES GENERADOS EXITOSAMENTE ---")
print(f"Carpeta destino: {os.path.abspath(carpeta_salida)}")
print("1. Dataset final CSV:      dataset_final_wendys_san_salvador.csv")
print("2. Jupyter Notebook:       proyecto_hotspots_wendys_sv.ipynb")
print("3. Mapa HTML interactivo:  mapa_final_hotspots_wendys.html")
print("4. Diccionario de datos:   diccionario_datos.md")
print("5. Informe tecnico:        informe_tecnico.md")
print("6. Guion de exposicion:    guion_exposicion.md")
