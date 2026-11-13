# Diccionario de Datos - Hotspots Comerciales Wendy's San Salvador

Este documento describe la estructura del archivo `dataset_final_wendys_san_salvador.csv` generado tras el proceso de extraccion desde OpenStreetMap (Overpass API), limpieza espacial y modelado con Machine Learning.

| Variable | Tipo de Dato | Origen / Formula | Descripcion |
| :--- | :--- | :--- | :--- |
| `osm_type` | Texto (`string`) | OpenStreetMap | Tipo de geometria registrada (`node`, `way` o `relation`). |
| `osm_id` | Entero (`int64`) | OpenStreetMap | Identificador unico del elemento dentro de la base de datos de OSM. |
| `nombre` | Texto (`string`) | Etiqueta `name` (OSM) | Nombre comercial registrado del establecimiento. |
| `marca` | Texto (`string`) | Etiqueta `brand` (OSM) | Marca comercial asociada al establecimiento. |
| `tipo_local` | Texto (`string`) | Etiqueta `amenity` (OSM) | Clasificacion gastronomica (`fast_food` o `restaurant`). |
| `latitud` | Decimal (`float64`) | Coordenada WGS84 | Latitud geografica en grados decimales (rango validado: 13.45 a 14.08). |
| `longitud` | Decimal (`float64`) | Coordenada WGS84 | Longitud geografica en grados decimales (rango validado: -89.30 a -89.00). |
| `direccion` | Texto (`string`) | Etiqueta `addr:street` | Calle o avenida registrada (respeta valores nulos si no existen en OSM). |
| `ciudad` | Texto (`string`) | Etiqueta `addr:city` | Municipio o ciudad registrada (respeta valores nulos sin imputacion). |
| `horario` | Texto (`string`) | Etiqueta `opening_hours` | Horario de atencion reportado en OSM (opcional). |
| `telefono` | Texto (`string`) | Etiqueta `phone` | Numero telefonico reportado en OSM (opcional). |
| `sitio_web` | Texto (`string`) | Etiqueta `website` | URL oficial reportada en OSM (opcional). |
| `cluster` | Entero (`int32`) | Modelo K-Means | Identificador numerico del polo comercial asignado (`0` a `K-1`). |
| `locales_en_cluster` | Entero (`int64`) | Conteo por grupo | Numero total de sucursales pertenecientes al mismo cluster. |
| `categoria_densidad` | Texto (`string`) | Regla de umbral | Etiqueta supervisada: `Alta Concentracion` si supera el promedio de locales por cluster, o `Baja Concentracion` en caso contrario. |
| `latitud_rad` | Decimal (`float64`) | `np.radians(latitud)` | Latitud transformada a radianes para calculo esferico Haversine. |
| `longitud_rad` | Decimal (`float64`) | `np.radians(longitud)` | Longitud transformada a radianes para calculo esferico Haversine. |
| `distancia_centroide_km` | Decimal (`float64`) | Formula Haversine | Distancia geodesica en kilometros desde la sucursal hasta el centroide de su cluster. |