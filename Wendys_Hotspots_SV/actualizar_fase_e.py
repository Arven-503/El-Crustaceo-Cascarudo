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

fecha_extraccion = "13 de noviembre de 2026"
fuente_datos = "OpenStreetMap (OSM) - Overpass API"
area_estudio = "Departamento de San Salvador, El Salvador (ISO3166-2 = SV-SS)"

consulta_overpass = """[out:json][timeout:60];
area["ISO3166-2"="SV-SS"]->.searchArea;
(
  nwr["amenity"~"^(fast_food|restaurant)$"]["name"~"Wendy",i](area.searchArea);
  nwr["amenity"~"^(fast_food|restaurant)$"]["brand"~"Wendy",i](area.searchArea);
);
out center;"""

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

casos_prueba = [
    {
        "caso": "Caso 1 (Propuesta Principal - Paseo General Escalon)",
        "lat": 13.70150,
        "lon": -89.23100
    },
    {
        "caso": "Caso 2 (Ejemplo Conocido - Eje Metrocentro / Los Heroes)",
        "lat": 13.70650,
        "lon": -89.21300
    },
    {
        "caso": "Caso 3 (Ejemplo Periferico - Zona Sur / San Marcos)",
        "lat": 13.65800,
        "lon": -89.18300
    }
]

resultados_casos = []
for cp in casos_prueba:
    p_rad = np.radians([[cp["lat"], cp["lon"]]])
    pred_c = knn_final.predict(p_rad)[0]
    d_rad, idx_v = knn_final.kneighbors(p_rad)
    d_km = d_rad[0] * 6371.0
    nombres_v = []
    for idx_item, dist_item in zip(idx_v[0], d_km):
        nom_v = df.loc[idx_item, "nombre"] if pd.notna(df.loc[idx_item, "nombre"]) else "Sin nombre"
        nombres_v.append(f"{nom_v} ({dist_item:.2f} km)")
    resultados_casos.append({
        "caso": cp["caso"],
        "lat": cp["lat"],
        "lon": cp["lon"],
        "prediccion": pred_c,
        "vecinos_detalle": "; ".join(nombres_v),
        "indices": idx_v[0],
        "distancias_km": d_km
    })

lat_propuesta = casos_prueba[0]["lat"]
lon_propuesta = casos_prueba[0]["lon"]
pred_propuesta = resultados_casos[0]["prediccion"]
idx_vecinos_principal = resultados_casos[0]["indices"]
dist_km_principal = resultados_casos[0]["distancias_km"]

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
        popup=f"<b>Centroide Cluster {cid}</b><br>Locales: {n_loc}<br>Categoria Zona: {cat_zona}",
        tooltip=f"Centroide Cluster {cid} ({cat_zona})",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(mapa)

for _, fila in df.iterrows():
    cid = int(fila["cluster"])
    color_pin = colores_cluster[cid % len(colores_cluster)]
    nombre_txt = fila["nombre"] if pd.notna(fila["nombre"]) else "Sin nombre"
    cat_osm = fila["tipo_local"] if pd.notna(fila["tipo_local"]) else "N/D"
    popup_html = (
        f"<b>{nombre_txt}</b><br>"
        f"Categoria OSM: {cat_osm}<br>"
        f"Cluster K-Means: {cid} ({fila['categoria_densidad']})<br>"
        f"Coords: {fila['latitud']:.5f}, {fila['longitud']:.5f}"
    )
    folium.Marker(
        location=[fila["latitud"], fila["longitud"]],
        popup=folium.Popup(popup_html, max_width=260),
        tooltip=f"{nombre_txt} [{cat_osm}] - Cluster {cid}",
        icon=folium.Icon(color=color_pin, icon="cutlery", prefix="fa")
    ).add_to(mapa)

for orden, (idx, d_km) in enumerate(zip(idx_vecinos_principal, dist_km_principal), start=1):
    v_lat = float(df.loc[idx, "latitud"])
    v_lon = float(df.loc[idx, "longitud"])
    v_nom = df.loc[idx, "nombre"] if pd.notna(df.loc[idx, "nombre"]) else "Sin nombre"
    folium.PolyLine(
        locations=[[lat_propuesta, lon_propuesta], [v_lat, v_lon]],
        color="crimson",
        weight=3,
        opacity=0.85,
        dash_array="6, 6",
        tooltip=f"Vecino {orden}: {v_nom} ({d_km:.2f} km)"
    ).add_to(mapa)

folium.Marker(
    location=[lat_propuesta, lon_propuesta],
    popup=(
        f"<b>Nueva Ubicacion Propuesta</b><br>"
        f"Clasificacion KNN (k={mejor_k_knn}): {pred_propuesta}<br>"
        f"Coords: {lat_propuesta:.5f}, {lon_propuesta:.5f}"
    ),
    tooltip=f"Ubicacion Propuesta ({pred_propuesta})",
    icon=folium.Icon(color="red", icon="flag", prefix="fa")
).add_to(mapa)

panel_superior_html = f"""
<div style="position: fixed; top: 15px; left: 55px; right: 55px; z-index:9999;
background-color: rgba(255, 255, 255, 0.95); border: 2px solid #1d4ed8; border-radius: 8px;
padding: 12px 16px; font-family: Arial, sans-serif; font-size: 12px;
box-shadow: 0 2px 8px rgba(0,0,0,0.25);">
<b style="font-size: 14px; color: #10233f;">Hotspots Comerciales de El Salvador: Wendy's (San Salvador)</b><br>
<b>Fuente:</b> {fuente_datos} | <b>Extraccion:</b> {fecha_extraccion} | <b>Modelo:</b> K-Means (K={mejor_k}) + KNN Haversine (k={mejor_k_knn})<br>
<b>Interpretacion:</b> Los clusters agrupan la oferta mapeada en OSM (no flujo real de personas). El punto propuesto ({lat_propuesta:.4f}, {lon_propuesta:.4f}) se clasifica como <b>{pred_propuesta}</b> segun sus {mejor_k_knn} vecinos mas cercanos.
</div>
"""

leyenda_html = f"""
<div style="position: fixed; bottom: 25px; left: 25px; width: 295px; z-index:9999;
background-color: rgba(255, 255, 255, 0.95); border: 2px solid #444; border-radius: 8px; padding: 12px;
font-family: Arial, sans-serif; font-size: 12px; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
<b>Leyenda del Mapa</b><br><br>
<span style="color: red;">&#9873;</span> Nueva ubicacion propuesta ({pred_propuesta})<br>
<span style="color: black;">&#9733;</span> Centroide polo comercial (K-Means)<br>
<span style="color: blue;">&#9679;</span> Sucursales actuales por cluster (ver popup)<br>
<span style="color: crimson;">---</span> Distancia Haversine a {mejor_k_knn} vecinos KNN<br>
<hr style="margin: 6px 0;">
<small>Umbral densidad: &gt; {promedio_locales:.2f} locales/cluster = Alta Concentracion</small>
</div>
"""

mapa.get_root().html.add_child(folium.Element(panel_superior_html))
mapa.get_root().html.add_child(folium.Element(leyenda_html))

ruta_mapa = os.path.join(carpeta_salida, "mapa_final_hotspots_wendys.html")
mapa.save(ruta_mapa)

diccionario_lineas = [
    "# Diccionario de Datos y Metadatos de Extraccion",
    "",
    "## 1. Metadatos de la Fuente de Datos",
    f"- **Fuente principal:** {fuente_datos}",
    f"- **Fecha de extraccion:** {fecha_extraccion}",
    f"- **Area geografica estudiada:** {area_estudio}",
    "- **Criterio de filtrado:** Establecimientos etiquetados como `amenity=fast_food` o `amenity=restaurant` con coincidencia insensible a mayusculas para `Wendy` en `name` o `brand`.",
    "- **Politica de calidad:** Validacion estricta de coordenadas dentro de San Salvador (`latitud` `[13.45, 14.08]`, `longitud` `[-89.30, -89.00]`), eliminacion de duplicados exactos y preservacion de valores faltantes (`NaN`) sin imputacion artificial.",
    "",
    "## 2. Consulta Literal Utilizada (Overpass QL)",
    "```overpassql",
    consulta_overpass,
    "```",
    "",
    "## 3. Estructura de Campos (`dataset_final_wendys_san_salvador.csv`)",
    "| Variable | Tipo de Dato | Origen / Formula | Descripcion |",
    "| :--- | :--- | :--- | :--- |",
    "| `osm_type` | Texto (`string`) | OpenStreetMap | Tipo de geometria registrada (`node`, `way` o `relation`). |",
    "| `osm_id` | Entero (`int64`) | OpenStreetMap | Identificador unico del elemento en la base de datos de OSM. |",
    "| `nombre` | Texto (`string`) | Etiqueta `name` (OSM) | Nombre comercial registrado del establecimiento. |",
    "| `marca` | Texto (`string`) | Etiqueta `brand` (OSM) | Marca comercial asociada al establecimiento. |",
    "| `tipo_local` | Texto (`string`) | Etiqueta `amenity` (OSM) | Categoria del negocio (`fast_food` o `restaurant`). |",
    "| `latitud` | Decimal (`float64`) | Coordenada WGS84 | Latitud geografica en grados decimales. |",
    "| `longitud` | Decimal (`float64`) | Coordenada WGS84 | Longitud geografica en grados decimales. |",
    "| `direccion` | Texto (`string`) | Etiqueta `addr:street` | Calle o avenida registrada (nulo si no existe en OSM). |",
    "| `ciudad` | Texto (`string`) | Etiqueta `addr:city` | Municipio o ciudad registrada (nulo si no existe en OSM). |",
    "| `horario` | Texto (`string`) | Etiqueta `opening_hours` | Horario de atencion reportado en OSM (opcional). |",
    "| `telefono` | Texto (`string`) | Etiqueta `phone` | Telefono reportado en OSM (opcional). |",
    "| `sitio_web` | Texto (`string`) | Etiqueta `website` | Sitio web reportado en OSM (opcional). |",
    "| `cluster` | Entero (`int32`) | Modelo K-Means | Grupo espacial asignado (`0` a `K-1`). |",
    "| `locales_en_cluster` | Entero (`int64`) | Conteo por grupo | Total de sucursales pertenecientes al mismo cluster. |",
    "| `categoria_densidad` | Texto (`string`) | Regla de umbral | Etiqueta supervisada: `Alta Concentracion` si supera el promedio de locales por cluster, o `Baja Concentracion` en caso contrario. |",
    "| `latitud_rad` | Decimal (`float64`) | `np.radians(latitud)` | Latitud en radianes para calculo geodesico Haversine. |",
    "| `longitud_rad` | Decimal (`float64`) | `np.radians(longitud)` | Longitud en radianes para calculo geodesico Haversine. |",
    "| `distancia_centroide_km` | Decimal (`float64`) | Formula Haversine | Distancia en kilometros desde la sucursal hasta el centroide de su cluster. |"
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

detalle_clusters_md = [
    "| Cluster | Centroide (Lat, Lon) | Cantidad de Locales | Clasificacion de Densidad | Sucursales Agrupadas |",
    "| :---: | :---: | :---: | :---: | :--- |"
]
for cid in range(mejor_k):
    sub_df = df[df["cluster"] == cid]
    n_loc = len(sub_df)
    cat_z = "Alta Concentracion" if n_loc > promedio_locales else "Baja Concentracion"
    nombres_lista = [
        f"{row['nombre']} ({row['latitud']:.4f}, {row['longitud']:.4f})"
        if pd.notna(row["nombre"]) else f"Sin nombre ({row['latitud']:.4f}, {row['longitud']:.4f})"
        for _, row in sub_df.iterrows()
    ]
    detalle_clusters_md.append(
        f"| {cid} | ({centroides[cid][0]:.5f}, {centroides[cid][1]:.5f}) | {n_loc} | {cat_z} | {', '.join(nombres_lista)} |"
    )

tabla_loo_md = [
    "| k (Vecinos Impares) | Aciertos | Exactitud LOO |",
    "| :---: | :---: | :---: |"
]
for r in resultados_loo:
    tabla_loo_md.append(f"| {r['k']} | {r['aciertos']} / {n_muestras} | {r['exactitud']:.2%} |")

tabla_casos_md = [
    "| Escenario Evaluado | Coordenadas | Clase Asignada (KNN) | Vecinos Mas Cercanos y Distancia Haversine |",
    "| :--- | :---: | :---: | :--- |"
]
for rc in resultados_casos:
    tabla_casos_md.append(
        f"| {rc['caso']} | ({rc['lat']:.5f}, {rc['lon']:.5f}) | **{rc['prediccion']}** | {rc['vecinos_detalle']} |"
    )

informe_lineas = [
    "# Informe Tecnico: Hotspots Comerciales de El Salvador (Wendy's - San Salvador)",
    "",
    "## 1. Contexto y Objetivo del Prototipo",
    f"Este prototipo academico analiza la distribucion geografica de las **{n_muestras} sucursales** de Wendy's registradas en el departamento de San Salvador para explorar polos de concentracion comercial y evaluar ubicaciones potenciales mediante **K-Means** y **K-Nearest Neighbors (KNN)** con distancia geodesica **Haversine**.",
    "",
    "## 2. Recoleccion, Limpieza y Trazabilidad de Datos (Fase A)",
    f"- **Fuente:** {fuente_datos}",
    f"- **Fecha de extraccion:** {fecha_extraccion}",
    f"- **Area de estudio:** {area_estudio}",
    f"- **Registros limpios consolidados:** {n_muestras} establecimientos validos dentro de la caja delimitadora departamental (`latitud` `[13.45, 14.08]`, `longitud` `[-89.30, -89.00]`).",
    "- **Limpieza aplicada:** Se eliminaron duplicados exactos por identificador OSM y coordenadas, y se mantuvieron intactos los valores nulos (`NaN`) en campos opcionales (direccion, horario, telefono) sin inventar informacion.",
    "",
    "**Consulta literal ejecutada en Overpass API:**",
    "```overpassql",
    consulta_overpass,
    "```",
    "",
    "## 3. Agrupamiento Espacial con K-Means (Fase B)",
    "Se evaluaron distintos valores de `K` midiendo la compactacion interna (**Inercia**) y la separacion entre polos comerciales (**Coeficiente de Silueta**):",
    "",
    *tabla_k_md,
    "",
    f"- **Justificacion de K:** Se selecciono `K = {mejor_k}` por maximizar el Coeficiente de Silueta (**{mejor_silueta}**) dentro de una segmentacion operativa de polos urbanos del Area Metropolitana de San Salvador.",
    f"- **Criterio de densidad:** El promedio por grupo es de **{promedio_locales:.2f} locales/cluster**. Los grupos por encima de este umbral reciben la etiqueta supervisada `Alta Concentracion` y los demas `Baja Concentracion`.",
    "",
    "**Interpretacion geografica de cada cluster:**",
    "",
    *detalle_clusters_md,
    "",
    "- **Limitaciones de K-Means:** K-Means agrupa unicamente coordenadas de establecimientos mapeados; un cluster con mas puntos indica mayor concentracion de oferta registrada en OSM, no mayor afluencia de personas ni mayor volumen de ventas.",
    "",
    "## 4. Clasificacion con KNN y Distancia Haversine (Fase C)",
    "Dado que KNN es un algoritmo supervisado, se utilizaron las etiquetas de densidad derivadas de K-Means. Las coordenadas se convirtieron a **radianes** para calcular distancias reales sobre la curvatura terrestre mediante la formula **Haversine** (`R = 6,371 km`).",
    "",
    "**Validacion cruzada Leave-One-Out (LOO) para seleccion de `k` impar:**",
    "",
    *tabla_loo_md,
    "",
    f"- **Justificacion de k:** Se eligio `k = {mejor_k_knn}` vecinos impares (evitando empates de votacion binaria), alcanzando una exactitud Leave-One-Out de **{mejor_acc_loo:.2%}**.",
    "",
    "**Evaluacion con ubicacion propuesta y ejemplos conocidos contrastantes:**",
    "",
    *tabla_casos_md,
    "",
    "## 5. Limitaciones Tecnicas y Conclusiones (Fase D)",
    "- **Cobertura colaborativa de OSM:** OpenStreetMap es construido por voluntarios; la falta de metadatos secundarios o eventuales sucursales no mapeadas reflejan el estado del mapeo comunitario y no un censo comercial oficial.",
    "- **Distancia geodesica vs. red vial:** La metrica Haversine calcula distancia en linea recta sobre la esfera terrestre, sin considerar sentido de calles, congestion vehicular ni barreras fisicas.",
    "- **Hipotesis comercial:** Una ubicacion clasificada como `Alta Concentracion` (mayor dinamismo comercial validado pero mayor riesgo de canibalizacion) o `Baja Concentracion` (oportunidad de expansion con menor competencia interna) constituye unicamente una hipotesis exploratoria que requiere estudios de poblacion, trafico, costos de alquiler y trabajo de campo."
]
ruta_informe = os.path.join(carpeta_salida, "informe_tecnico.md")
with open(ruta_informe, "w", encoding="utf-8") as f:
    f.write("\n".join(informe_lineas))

celdas_notebook = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Hotspots Comerciales de El Salvador: Wendy's (San Salvador)\n",
            f"- **Fuente:** {fuente_datos}\n",
            f"- **Fecha de extraccion:** {fecha_extraccion}\n",
            f"- **Area:** {area_estudio}"
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
            "from sklearn.cluster import KMeans\n",
            "from sklearn.metrics import silhouette_score\n",
            "from sklearn.neighbors import KNeighborsClassifier\n",
            "from sklearn.model_selection import LeaveOneOut\n",
            "\n",
            "df = pd.read_csv('../wendys_san_salvador_limpio.csv')\n",
            "print(f'Total de sucursales limpias: {len(df)}')\n",
            "df[['osm_id', 'nombre', 'tipo_local', 'latitud', 'longitud']]"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Fase B: Agrupamiento Espacial con K-Means"
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
            "df[['nombre', 'tipo_local', 'latitud', 'longitud', 'cluster', 'categoria_densidad']].sort_values('cluster')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Fase C: Clasificacion Supervisada con KNN (Metrica Haversine) y Ejemplos Contrastantes"
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
            "    print(f'k={k} | Exactitud LOO: {aciertos/len(df):.2%}')\n",
            "\n",
            f"knn_final = KNeighborsClassifier(n_neighbors={mejor_k_knn}, metric='haversine')\n",
            "knn_final.fit(X_rad, y)\n",
            "\n",
            "ejemplos = [\n",
            "    ('Propuesta Paseo General Escalon', 13.70150, -89.23100),\n",
            "    ('Conocido Eje Metrocentro / Los Heroes', 13.70650, -89.21300),\n",
            "    ('Periferico Zona Sur / San Marcos', 13.65800, -89.18300)\n",
            "]\n",
            "\n",
            "for titulo, lat_e, lon_e in ejemplos:\n",
            "    p_rad = np.radians([[lat_e, lon_e]])\n",
            "    pred_e = knn_final.predict(p_rad)[0]\n",
            "    d_rad, idx_e = knn_final.kneighbors(p_rad)\n",
            "    d_km = d_rad[0] * 6371.0\n",
            "    print(f'\\n{titulo} ({lat_e}, {lon_e}) -> {pred_e}')\n",
            "    for i_v, dist_v in zip(idx_e[0], d_km):\n",
            "        print(f\"  - {df.loc[i_v, 'nombre']} ({dist_v:.3f} km)\")"
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

print("--- ACTUALIZACION DE ENTREGABLES COMPLETADA ---")
print("1. diccionario_datos.md actualizado con fecha, fuente y consulta Overpass.")
print("2. informe_tecnico.md actualizado con interpretacion de clusters y 3 casos KNN.")
print("3. mapa_final_hotspots_wendys.html actualizado con titulo, fuente, leyenda y categoria OSM.")
print("4. proyecto_hotspots_wendys_sv.ipynb actualizado.")
