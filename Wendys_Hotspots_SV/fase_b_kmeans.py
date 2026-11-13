import pandas as pd
import numpy as np
import folium
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

df = pd.read_csv("wendys_san_salvador_limpio.csv")
X = df[["latitud", "longitud"]].to_numpy()

n_muestras = len(df)
if n_muestras < 3:
    raise ValueError("Se necesitan al menos 3 sucursales para evaluar K-Means.")

max_k = min(7, n_muestras - 1)
resultados_k = []

print("--- EVALUACION DE VALORES DE K (K-MEANS) ---")
for k in range(2, max_k + 1):
    modelo = KMeans(n_clusters=k, random_state=42, n_init=10)
    etiquetas = modelo.fit_predict(X)
    inercia = modelo.inertia_
    silueta = silhouette_score(X, etiquetas)
    resultados_k.append({
        "k": k,
        "inercia": round(float(inercia), 6),
        "silueta": round(float(silueta), 4)
    })

df_eval = pd.DataFrame(resultados_k)
print(df_eval.to_string(index=False))

candidatos = [r for r in resultados_k if r["k"] >= 3] if max_k >= 3 else resultados_k
mejor_config = max(candidatos, key=lambda x: x["silueta"])
mejor_k = mejor_config["k"]

print(f"\nK seleccionado para polos comerciales del AMSS: K = {mejor_k} (Silueta = {mejor_config['silueta']})")

kmeans_final = KMeans(n_clusters=mejor_k, random_state=42, n_init=10)
df["cluster"] = kmeans_final.fit_predict(X)

conteo_clusters = df["cluster"].value_counts().sort_index()
centroides = kmeans_final.cluster_centers_

filas_centroides = []
for cid in range(mejor_k):
    filas_centroides.append({
        "cluster": cid,
        "latitud_centroide": centroides[cid][0],
        "longitud_centroide": centroides[cid][1],
        "cantidad_locales": int(conteo_clusters.get(cid, 0))
    })

df_centroides = pd.DataFrame(filas_centroides)

print("\n--- RESUMEN DE CLUSTERS Y CENTROIDES ---")
print(df_centroides.to_string(index=False))

df.to_csv("wendys_san_salvador_clusters.csv", index=False, encoding="utf-8")
df_centroides.to_csv("centroides_kmeans.csv", index=False, encoding="utf-8")

colores_cluster = ["blue", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen"]

centro_lat = df["latitud"].mean()
centro_lon = df["longitud"].mean()
mapa = folium.Map(
    location=[centro_lat, centro_lon],
    zoom_start=12,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Esri World Street Map"
)

for _, fila in df.iterrows():
    cid = int(fila["cluster"])
    color_pin = colores_cluster[cid % len(colores_cluster)]
    nombre_txt = fila["nombre"] if pd.notna(fila["nombre"]) else "Sin nombre"
    popup_html = (
        f"<b>{nombre_txt}</b><br>"
        f"Cluster asignado: {cid}<br>"
        f"Coords: {fila['latitud']:.5f}, {fila['longitud']:.5f}"
    )
    folium.Marker(
        location=[fila["latitud"], fila["longitud"]],
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"{nombre_txt} (Cluster {cid})",
        icon=folium.Icon(color=color_pin, icon="cutlery", prefix="fa")
    ).add_to(mapa)

for _, cfila in df_centroides.iterrows():
    cid = int(cfila["cluster"])
    color_zona = colores_cluster[cid % len(colores_cluster)]
    popup_centroide = (
        f"<b>Centroide Polo Comercial - Cluster {cid}</b><br>"
        f"Locales en el grupo: {int(cfila['cantidad_locales'])}<br>"
        f"Coords: {cfila['latitud_centroide']:.5f}, {cfila['longitud_centroide']:.5f}"
    )
    folium.Circle(
        location=[cfila["latitud_centroide"], cfila["longitud_centroide"]],
        radius=1200,
        color=color_zona,
        fill=True,
        fill_opacity=0.12
    ).add_to(mapa)
    folium.Marker(
        location=[cfila["latitud_centroide"], cfila["longitud_centroide"]],
        popup=folium.Popup(popup_centroide, max_width=260),
        tooltip=f"Centroide Cluster {cid}",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(mapa)

mapa.save("mapa_clusters_kmeans.html")
print("\nArchivos generados correctamente:")
print("- wendys_san_salvador_clusters.csv")
print("- centroides_kmeans.csv")
print("- mapa_clusters_kmeans.html")
