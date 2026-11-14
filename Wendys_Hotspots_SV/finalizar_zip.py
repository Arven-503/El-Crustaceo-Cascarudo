import os
import ast
import json
import zipfile
import numpy as np
import pandas as pd
import folium
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneOut
from pptx import Presentation

carpeta = "entregables_finales"
df = pd.read_csv(os.path.join(carpeta, "dataset_final_wendys_san_salvador.csv"))
n_muestras = len(df)
mejor_k = int(df["cluster"].nunique())
conteo_clusters = df["cluster"].value_counts().sort_index()
promedio_locales = float(conteo_clusters.mean())

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
        "exactitud": round(aciertos / n_muestras, 4)
    })

mejor_knn_cfg = max(
    resultados_loo,
    key=lambda r: (r["exactitud"], 1 if r["k"] == 3 else 0)
)
mejor_k_knn = mejor_knn_cfg["k"]

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

for cid in sorted(df["cluster"].unique()):
    sub = df[df["cluster"] == cid]
    c_lat = float(sub["latitud"].mean())
    c_lon = float(sub["longitud"].mean())
    color_zona = colores_cluster[int(cid) % len(colores_cluster)]
    n_loc = len(sub)
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

for orden, (idx, d_km) in enumerate(zip(idx_vecinos[0], dist_km), start=1):
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
<b>Fuente:</b> OpenStreetMap (OSM) - Overpass API | <b>Extraccion:</b> 13 de noviembre de 2026 | <b>Modelo:</b> K-Means (K={mejor_k}) + KNN Haversine (k={mejor_k_knn})<br>
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

ruta_mapa = os.path.join(carpeta, "mapa_final_hotspots_wendys.html")
mapa.save(ruta_mapa)

archivos_esperados = [
    "wendys_san_salvador_limpio.csv",
    "dataset_final_wendys_san_salvador.csv",
    "diccionario_datos.md",
    "proyecto_hotspots_wendys_sv.ipynb",
    "mapa_final_hotspots_wendys.html",
    "app.py",
    "requirements.txt",
    "README.md",
    "informe_tecnico.md",
    "presentacion_hotspots_wendys_sv.pptx",
    "guion_exposicion.md"
]

errores = []
for nombre in archivos_esperados:
    ruta = os.path.join(carpeta, nombre)
    if not os.path.isfile(ruta) or os.path.getsize(ruta) == 0:
        errores.append(f"Problema con archivo: {nombre}")

with open(ruta_mapa, "r", encoding="utf-8") as f:
    html_txt = f.read()
for marca in ["Esri World Street Map", "Leyenda del Mapa", "OpenStreetMap"]:
    if marca not in html_txt:
        errores.append(f"Falta en mapa HTML: {marca}")

with open(os.path.join(carpeta, "app.py"), "r", encoding="utf-8") as f:
    ast.parse(f.read())

with open(os.path.join(carpeta, "proyecto_hotspots_wendys_sv.ipynb"), "r", encoding="utf-8-sig") as f:
    nb = json.load(f)
celdas_codigo = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
if any(not c.get("outputs") for c in celdas_codigo):
    errores.append("Hay celdas sin salida en el notebook.")

prs_ver = Presentation(os.path.join(carpeta, "presentacion_hotspots_wendys_sv.pptx"))
if len(prs_ver.slides) < 8:
    errores.append("Presentacion incompleta.")

if errores:
    for err in errores:
        print(f"ERROR: {err}")
else:
    nombre_zip = "Entrega_Hotspots_Wendys_SanSalvador.zip"
    with zipfile.ZipFile(nombre_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre in archivos_esperados:
            ruta_completa = os.path.join(carpeta, nombre)
            zf.write(ruta_completa, arcname=os.path.join(carpeta, nombre))
    print("TODO PERFECTO. Todos los 11 archivos pasaron la auditoria.")
    print(f"Archivo ZIP listo para entregar: {os.path.abspath(nombre_zip)}")
