import numpy as np
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneOut

df = pd.read_csv("wendys_san_salvador_clusters.csv")

conteo_por_cluster = df["cluster"].value_counts()
promedio_locales = conteo_por_cluster.mean()

df["locales_en_cluster"] = df["cluster"].map(conteo_por_cluster)
df["categoria_densidad"] = np.where(
    df["locales_en_cluster"] > promedio_locales,
    "Alta Concentracion",
    "Baja Concentracion"
)

print("--- ETIQUETADO SUPERVISADO POR DENSIDAD DE CLUSTER ---")
print(f"Promedio de locales por cluster: {promedio_locales:.2f}")
resumen_clusters = (
    df.groupby(["cluster", "categoria_densidad"])
    .size()
    .reset_index(name="cantidad_locales")
)
print(resumen_clusters.to_string(index=False))

df.to_csv("wendys_san_salvador_knn.csv", index=False, encoding="utf-8")

X_rad = np.radians(df[["latitud", "longitud"]].to_numpy())
y = np.array(df["categoria_densidad"].tolist())

n_muestras = len(df)
valores_k = [k for k in range(1, n_muestras, 2)]

loo = LeaveOneOut()
resultados_loo = []

print("\n--- VALIDACION CRUZADA LEAVE-ONE-OUT (KNN HAVERSINE) ---")
for k in valores_k:
    aciertos = 0
    for train_idx, test_idx in loo.split(X_rad):
        knn = KNeighborsClassifier(n_neighbors=k, metric="haversine")
        knn.fit(X_rad[train_idx], y[train_idx])
        pred = knn.predict(X_rad[test_idx])
        if pred[0] == y[test_idx][0]:
            aciertos += 1
    exactitud = aciertos / n_muestras
    resultados_loo.append({
        "k_vecinos": k,
        "aciertos": aciertos,
        "total": n_muestras,
        "exactitud": round(exactitud, 4)
    })

df_loo = pd.DataFrame(resultados_loo)
print(df_loo.to_string(index=False))

mejor_fila = max(
    resultados_loo,
    key=lambda r: (r["exactitud"], 1 if r["k_vecinos"] == 3 else 0)
)
mejor_k = mejor_fila["k_vecinos"]
print(f"\nMejor k impar seleccionado: k = {mejor_k} (Exactitud LOO = {mejor_fila['exactitud']:.2%})")

knn_final = KNeighborsClassifier(n_neighbors=mejor_k, metric="haversine")
knn_final.fit(X_rad, y)

nueva_lat = 13.7015
nueva_lon = -89.2310
punto_nuevo_rad = np.radians([[nueva_lat, nueva_lon]])

prediccion = knn_final.predict(punto_nuevo_rad)[0]
distancias_rad, indices = knn_final.kneighbors(punto_nuevo_rad)
distancias_km = distancias_rad[0] * 6371.0

print("\n--- EVALUACION DE NUEVA UBICACION PROPUESTA ---")
print(f"Coordenada evaluada (Paseo General Escalon, San Salvador): ({nueva_lat}, {nueva_lon})")
print(f"Clasificacion predicha: {prediccion}")
print(f"\nDetalle de los {mejor_k} vecinos mas cercanos (Distancia Haversine):")

vecinos_info = []
for idx, dist_km in zip(indices[0], distancias_km):
    nombre_vecino = df.loc[idx, "nombre"] if pd.notna(df.loc[idx, "nombre"]) else "Sin nombre"
    vecinos_info.append({
        "sucursal": nombre_vecino,
        "cluster": int(df.loc[idx, "cluster"]),
        "categoria": df.loc[idx, "categoria_densidad"],
        "latitud": df.loc[idx, "latitud"],
        "longitud": df.loc[idx, "longitud"],
        "distancia_km": round(float(dist_km), 3)
    })

df_vecinos = pd.DataFrame(vecinos_info)
print(df_vecinos.to_string(index=False))
