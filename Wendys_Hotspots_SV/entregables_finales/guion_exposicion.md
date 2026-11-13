# Guion de Exposicion Academica (Duracion estimada: 8 - 10 minutos)

## Bloque 1: Apertura y Planteamiento del Problema (1.5 min)
- **Idea clave:** Elegir donde abrir una nueva sucursal de comida rapida requiere equilibrar dos fuerzas: aprovechar zonas de alta demanda comercial y evitar la canibalizacion entre locales cercanos.
- **Objetivo:** Construir un prototipo reproducible de Machine Learning geoespacial para analizar la distribucion de Wendy's en el departamento de San Salvador y evaluar ubicaciones candidatas.

## Bloque 2: Ingenieria de Datos y Limpieza Espacial (1.5 min)
- **Fuente de datos:** Extraccion en tiempo real desde OpenStreetMap mediante Overpass API filtrando el codigo administrativo `ISO3166-2 = SV-SS`.
- **Calidad del dato:** Se validaron rangos geograficos estrictos de San Salvador, se eliminaron duplicados y se respetaron los valores nulos en atributos opcionales sin inventar informacion, consolidando **11 registros** limpios.

## Bloque 3: Segmentacion de Polos Comerciales con K-Means (2 min)
- **Explicacion:** Aplicamos K-Means para descubrir agrupamientos naturales en el Area Metropolitana de San Salvador, evaluando Inercia y Coeficiente de Silueta.
- **Hallazgo:** Con `K = 3` (Silueta = `0.5114`), identificamos los polos comerciales principales y definimos un umbral objetivo basado en el promedio de `3.67` locales por cluster para clasificar zonas de `Alta Concentracion` vs `Baja Concentracion`.

## Bloque 4: Clasificacion Geodesica con KNN Haversine (2 min)
- **Por que Haversine:** A diferencia de la distancia euclidiana tradicional, la formula Haversine convierte latitud y longitud a radianes y calcula kilometros reales sobre la curvatura de la Tierra (`R = 6,371 km`).
- **Validacion:** Mediante Leave-One-Out (LOO), el modelo con `k = 3` obtuvo una exactitud de **90.91%**. Al evaluar un punto candidato en Paseo General Escalon (`13.7015, -89.231`), el sistema lo clasifica como **Alta Concentracion** y traza las distancias exactas a sus vecinos.

## Bloque 5: Demostracion en Vivo y Limitaciones (2 min)
- **Demo en Streamlit:** Mostrar como el usuario puede mover las coordenadas en la barra lateral, cambiar `K` y `k` en tiempo real, y visualizar las lineas punteadas hacia los vecinos cercanos.
- **Rigor academico (Limitaciones):** Aclarar que OpenStreetMap es una fuente colaborativa y que el prototipo mide proximidad espacial, sirviendo como herramienta de pre-seleccion que debe complementarse con estudios de trafico vehicular y costos operativos.

## Posibles Preguntas del Jurado y Respuestas Clave
1. **Por que usaron Leave-One-Out en lugar de Train/Test Split tradicional?**
   *Respuesta:* Porque al trabajar con una muestra acotada de establecimientos reales en un departamento especifico, Leave-One-Out aprovecha el maximo de informacion disponible en cada iteracion sin depender de una particion aleatoria.
2. **Por que convertir coordenadas a radianes en KNN?**
   *Respuesta:* Porque la implementacion de la metrica `haversine` en scikit-learn exige entradas en radianes para aplicar correctamente las funciones trigonometricas esfericas antes de multiplicar por el radio terrestre (6,371 km).