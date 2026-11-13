import requests
import pandas as pd
import folium

endpoints = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]

query = """
[out:json][timeout:60];
area["ISO3166-2"="SV-SS"]->.searchArea;
(
  nwr["amenity"~"^(fast_food|restaurant)$"]["name"~"Wendy",i](area.searchArea);
  nwr["amenity"~"^(fast_food|restaurant)$"]["brand"~"Wendy",i](area.searchArea);
);
out center;
"""

headers = {"User-Agent": "ProyectoAcademicoHotspotsSV/1.0"}
data = None

for url in endpoints:
    try:
        print(f"Consultando servidor Overpass: {url} ...")
        response = requests.post(url, data={"data": query}, headers=headers, timeout=90)
        response.raise_for_status()
        data = response.json()
        print("Respuesta recibida exitosamente.")
        break
    except Exception as e:
        print(f"Fallo en {url}: {e}")

if data is None:
    raise RuntimeError("No fue posible obtener respuesta de ningun servidor Overpass.")

elements = data.get("elements", [])
print(f"Registros crudos recibidos desde OSM: {len(elements)}")

rows = []
for el in elements:
    osm_type = el.get("type")
    osm_id = el.get("id")
    lat = el.get("lat") if "lat" in el else el.get("center", {}).get("lat")
    lon = el.get("lon") if "lon" in el else el.get("center", {}).get("lon")
    tags = el.get("tags", {})
    rows.append({
        "osm_type": osm_type,
        "osm_id": osm_id,
        "nombre": tags.get("name"),
        "marca": tags.get("brand"),
        "tipo_local": tags.get("amenity"),
        "latitud": lat,
        "longitud": lon,
        "direccion": tags.get("addr:street"),
        "ciudad": tags.get("addr:city"),
        "horario": tags.get("opening_hours"),
        "telefono": tags.get("phone"),
        "sitio_web": tags.get("website")
    })

df = pd.DataFrame(rows)

if df.empty:
    print("No se encontraron registros en la consulta.")
else:
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df = df.dropna(subset=["latitud", "longitud"])

    rango_lat = (df["latitud"] >= 13.45) & (df["latitud"] <= 14.08)
    rango_lon = (df["longitud"] >= -89.30) & (df["longitud"] <= -89.00)
    df = df[rango_lat & rango_lon].copy()

    df = df.drop_duplicates(subset=["osm_type", "osm_id"])
    df = df.drop_duplicates(subset=["nombre", "latitud", "longitud"])
    df = df.reset_index(drop=True)

    df.to_csv("wendys_san_salvador_limpio.csv", index=False, encoding="utf-8")

    print("\n--- RESUMEN EXPLORATORIO (EDA) ---")
    print(f"Total de sucursales limpias en San Salvador: {len(df)}")
    print("\nValores faltantes por columna (respetados sin imputacion):")
    print(df.isna().sum().to_string())
    print("\nEstadisticas descriptivas de coordenadas:")
    print(df[["latitud", "longitud"]].describe().to_string())
    print("\nListado de establecimientos extraidos:")
    print(df[["osm_id", "nombre", "tipo_local", "latitud", "longitud"]].to_string())

    centro_lat = df["latitud"].mean()
    centro_lon = df["longitud"].mean()
    mapa = folium.Map(
        location=[centro_lat, centro_lon],
        zoom_start=12,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Street Map"
    )

    for _, fila in df.iterrows():
        nombre_txt = fila["nombre"] if pd.notna(fila["nombre"]) else "Sin nombre"
        tipo_txt = fila["tipo_local"] if pd.notna(fila["tipo_local"]) else "N/D"
        dir_txt = fila["direccion"] if pd.notna(fila["direccion"]) else "No disponible"
        popup_html = (
            f"<b>{nombre_txt}</b><br>"
            f"Tipo: {tipo_txt}<br>"
            f"Direccion: {dir_txt}<br>"
            f"Coords: {fila['latitud']:.5f}, {fila['longitud']:.5f}"
        )
        folium.Marker(
            location=[fila["latitud"], fila["longitud"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=nombre_txt,
            icon=folium.Icon(color="red", icon="cutlery", prefix="fa")
        ).add_to(mapa)

    mapa.save("mapa_exploratorio.html")
    print("\nArchivos generados correctamente:")
    print("- wendys_san_salvador_limpio.csv")
    print("- mapa_exploratorio.html")
