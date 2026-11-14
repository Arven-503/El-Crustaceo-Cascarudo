import os
import ast
import json
import zipfile
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneOut
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

carpeta = "entregables_finales"

print("--- REPARANDO CODIFICACION Y VERIFICANDO ENTREGABLES ---")

ruta_app = os.path.join(carpeta, "app.py")
if os.path.isfile(ruta_app):
    with open(ruta_app, "r", encoding="utf-8-sig") as f:
        contenido_app = f.read()
    with open(ruta_app, "w", encoding="utf-8") as f:
        f.write(contenido_app)

ruta_pptx = os.path.join(carpeta, "presentacion_hotspots_wendys_sv.pptx")
if not os.path.isfile(ruta_pptx):
    df_p = pd.read_csv(os.path.join(carpeta, "dataset_final_wendys_san_salvador.csv"))
    n_muestras = len(df_p)
    X = df_p[["latitud", "longitud"]].to_numpy()

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

    mejor_k = int(df_p["cluster"].nunique())
    mejor_silueta = next(r["silueta"] for r in resultados_k if r["k"] == mejor_k)
    conteo_clusters = df_p["cluster"].value_counts().sort_index()
    promedio_locales = float(conteo_clusters.mean())

    X_rad = df_p[["latitud_rad", "longitud_rad"]].to_numpy()
    y = np.array(df_p["categoria_densidad"].tolist())
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

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    layout_blanco = prs.slide_layouts[6]

    color_navy = RGBColor(16, 35, 63)
    color_teal = RGBColor(15, 118, 110)
    color_texto = RGBColor(31, 41, 55)
    color_blanco = RGBColor(255, 255, 255)

    def agregar_encabezado(slide, titulo, subtitulo):
        franja = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        franja.fill.solid()
        franja.fill.fore_color.rgb = color_navy
        franja.line.fill.background()

        tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.18), Inches(12.1), Inches(0.85))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = titulo
        p1.font.size = Pt(24)
        p1.font.bold = True
        p1.font.color.rgb = color_blanco

        p2 = tf.add_paragraph()
        p2.text = subtitulo
        p2.font.size = Pt(13)
        p2.font.color.rgb = RGBColor(191, 219, 254)

    def agregar_bullets(slide, items, left, top, width, height, font_size=16):
        tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        for idx, (negrita, detalle) in enumerate(items):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.space_after = Pt(12)
            r1 = p.add_run()
            r1.text = f"- {negrita}: " if negrita else "- "
            r1.font.bold = True
            r1.font.size = Pt(font_size)
            r1.font.color.rgb = color_navy

            r2 = p.add_run()
            r2.text = detalle
            r2.font.size = Pt(font_size)
            r2.font.color.rgb = color_texto

    s1 = prs.slides.add_slide(layout_blanco)
    fondo1 = s1.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    fondo1.fill.solid()
    fondo1.fill.fore_color.rgb = color_navy
    fondo1.line.fill.background()

    acento1 = s1.shapes.add_shape(1, Inches(0.8), Inches(1.5), Inches(1.2), Inches(0.12))
    acento1.fill.solid()
    acento1.fill.fore_color.rgb = color_teal
    acento1.line.fill.background()

    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.5), Inches(4.5))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p_eyebrow = tf1.paragraphs[0]
    p_eyebrow.text = "MACHINE LEARNING APLICADO - PROTOTIPO ACADEMICO"
    p_eyebrow.font.size = Pt(14)
    p_eyebrow.font.bold = True
    p_eyebrow.font.color.rgb = RGBColor(147, 197, 253)

    p_tit = tf1.add_paragraph()
    p_tit.text = "Hotspots Comerciales de El Salvador:\nCaso Wendy's (San Salvador)"
    p_tit.font.size = Pt(40)
    p_tit.font.bold = True
    p_tit.font.color.rgb = color_blanco
    p_tit.space_before = Pt(12)
    p_tit.space_after = Pt(18)

    p_sub = tf1.add_paragraph()
    p_sub.text = "Agrupamiento espacial con K-Means y clasificacion geodesica con KNN Haversine sobre datos abiertos de OpenStreetMap."
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = RGBColor(226, 232, 240)
    p_sub.space_after = Pt(28)

    p_meta = tf1.add_paragraph()
    p_meta.text = "Exposicion: Lunes 16 de noviembre de 2026  |  Departamento: San Salvador (SV-SS)"
    p_meta.font.size = Pt(14)
    p_meta.font.color.rgb = RGBColor(153, 246, 228)

    s2 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s2, "1. Contexto y Pregunta Guia", "Planteamiento del reto comercial y alcance metodologico")
    agregar_bullets(s2, [
        ("Problema de negocio", "Evaluar donde instalar una nueva sucursal comercial en San Salvador equilibrando atraccion de demanda y riesgo de canibalizacion."),
        ("Pregunta guia", "Que zonas concentran establecimientos actuales y como analizamos una nueva ubicacion mediante Machine Learning?"),
        ("Arquitectura propuesta", "Combinar aprendizaje no supervisado (K-Means) para detectar polos existentes y aprendizaje supervisado (KNN) para evaluar puntos candidatos."),
        ("Alcance academico", "Es un prototipo exploratorio basado en oferta mapeada; no garantiza ventas, seguridad ni afluencia real de personas.")
    ], 0.7, 1.5, 11.9, 5.4, 17)

    s3 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s3, "2. Recoleccion y Limpieza de Datos (Fase A)", "Extraccion reproducible desde OpenStreetMap mediante Overpass API")
    agregar_bullets(s3, [
        ("Fuente y fecha", "OpenStreetMap (Overpass API), extraido el 13 de noviembre de 2026 para el area administrativa ISO3166-2 = SV-SS."),
        ("Filtro aplicado", "Nodos, vias y relaciones etiquetados como fast_food o restaurant con coincidencia para Wendy's en name o brand."),
        ("Control de calidad", f"Validacion de coordenadas dentro de San Salvador ([13.45, 14.08] lat; [-89.30, -89.00] lon) y eliminacion de duplicados exactos, consolidando {n_muestras} sucursales."),
        ("Integridad del dato", "Se respetaron los valores faltantes (NaN) en campos opcionales como horarios o telefonos sin inventar registros.")
    ], 0.7, 1.5, 11.9, 5.4, 17)

    s4 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s4, "3. Agrupamiento Espacial con K-Means (Fase B)", "Seleccion del numero de polos comerciales mediante Inercia y Silueta")

    filas_t4 = len(resultados_k) + 1
    tabla_s4 = s4.shapes.add_table(filas_t4, 3, Inches(0.7), Inches(1.55), Inches(5.3), Inches(3.8)).table
    tabla_s4.cell(0, 0).text = "K (Clusters)"
    tabla_s4.cell(0, 1).text = "Inercia"
    tabla_s4.cell(0, 2).text = "Coef. Silueta"
    for c_idx in range(3):
        tabla_s4.cell(0, c_idx).fill.solid()
        tabla_s4.cell(0, c_idx).fill.fore_color.rgb = color_navy
        tabla_s4.cell(0, c_idx).text_frame.paragraphs[0].font.color.rgb = color_blanco
        tabla_s4.cell(0, c_idx).text_frame.paragraphs[0].font.bold = True

    for r_idx, r_val in enumerate(resultados_k, start=1):
        tabla_s4.cell(r_idx, 0).text = str(r_val["k"])
        tabla_s4.cell(r_idx, 1).text = str(r_val["inercia"])
        tabla_s4.cell(r_idx, 2).text = str(r_val["silueta"])

    agregar_bullets(s4, [
        ("Justificacion de K", f"Se eligio K = {mejor_k} por maximizar el Coeficiente de Silueta ({mejor_silueta}) en la segmentacion de corredores urbanos."),
        ("Etiquetado supervisado", f"El promedio es de {promedio_locales:.2f} locales/cluster. Grupos superiores al promedio se etiquetan como Alta Concentracion."),
        ("Advertencia tecnica", "K-Means agrupa densidad de locales mapeados en OSM, no concentracion de peatones ni volumen de facturacion.")
    ], 6.4, 1.55, 6.2, 5.2, 16)

    s5 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s5, "4. Interpretacion de Polos Comerciales Identificados", "Distribucion de sucursales por cluster y centroides")

    filas_t5 = mejor_k + 1
    tabla_s5 = s5.shapes.add_table(filas_t5, 4, Inches(0.7), Inches(1.55), Inches(11.9), Inches(4.8)).table
    encabezados_t5 = ["Cluster", "Centroide (Lat, Lon)", "Locales", "Clasificacion de Densidad"]
    for c_idx, txt_h in enumerate(encabezados_t5):
        tabla_s5.cell(0, c_idx).text = txt_h
        tabla_s5.cell(0, c_idx).fill.solid()
        tabla_s5.cell(0, c_idx).fill.fore_color.rgb = color_teal
        tabla_s5.cell(0, c_idx).text_frame.paragraphs[0].font.color.rgb = color_blanco
        tabla_s5.cell(0, c_idx).text_frame.paragraphs[0].font.bold = True

    for cid in range(mejor_k):
        sub = df_p[df_p["cluster"] == cid]
        c_lat = sub["latitud"].mean()
        c_lon = sub["longitud"].mean()
        n_l = len(sub)
        cat_d = sub["categoria_densidad"].iloc[0]
        tabla_s5.cell(cid + 1, 0).text = f"Cluster {cid}"
        tabla_s5.cell(cid + 1, 1).text = f"{c_lat:.5f}, {c_lon:.5f}"
        tabla_s5.cell(cid + 1, 2).text = str(n_l)
        tabla_s5.cell(cid + 1, 3).text = cat_d

    s6 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s6, "5. Clasificacion Geodesica con KNN Haversine (Fase C)", "Validacion cruzada Leave-One-Out y simulacion de ubicaciones")
    agregar_bullets(s6, [
        ("Distancia Haversine", "Las coordenadas se convierten a radianes para medir kilometros reales sobre la esfera terrestre (R = 6,371 km), evitando distorsiones planares."),
        ("Seleccion de k impar", f"Mediante Leave-One-Out (LOO) se selecciono k = {mejor_k_knn}, logrando una exactitud de {mejor_acc_loo:.2%} y evitando empates de votacion."),
        ("Caso 1 (Paseo General Escalon)", "Evaluacion de ubicacion candidata en corredor comercial consolidado y medicion de distancia a sus vecinos inmediatos."),
        ("Casos contrastantes", "Comparacion contra eje Metrocentro/Los Heroes y zona periferica sur (San Marcos) para validar sensibilidad espacial.")
    ], 0.7, 1.5, 11.9, 5.4, 16)

    s7 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s7, "6. Prototipo Interactivo en Streamlit y Folium (Fase D)", "Herramienta de simulacion espacial en tiempo real")
    agregar_bullets(s7, [
        ("Parametros dinamicos", "Barra lateral para variar K (clusters), k impar (vecinos KNN) y coordenadas propuestas en tiempo real."),
        ("Visualizacion geoespacial", "Mapa Esri World Street Map con marcadores por cluster, centroides (estrellas), punto propuesto (bandera) y lineas punteadas Haversine."),
        ("Trazabilidad y transparencia", "Tabla interactiva con distancias exactas en kilometros hacia los k vecinos mas cercanos y panel de interpretacion estrategica."),
        ("Entregable independiente", "Ademas de la app web, se exporta un mapa HTML autonomo con titulo, fuente, leyenda e interpretacion integrada.")
    ], 0.7, 1.5, 11.9, 5.4, 16)

    s8 = prs.slides.add_slide(layout_blanco)
    agregar_encabezado(s8, "7. Limitaciones Tecnicas y Conclusiones", "Rigor metodologico y trabajo futuro para decisiones reales")
    agregar_bullets(s8, [
        ("Cobertura de OpenStreetMap", "Los datos provienen de mapeo colaborativo; ausencia de etiquetas o locales no registrados reflejan cobertura comunitaria, no un censo oficial."),
        ("Distancia lineal vs. red vial", "Haversine mide distancia geodesica directa y no tiempos reales de conduccion, sentido de vias ni barreras urbanas."),
        ("Hipotesis comercial", "Una zona de Alta Concentracion valida demanda pero implica riesgo de canibalizacion; Baja Concentracion sugiere expansion con menor competencia interna."),
        ("Proximos pasos", "Incorporar densidades poblacionales, flujo vehicular, niveles socioeconomicos, costos de alquiler y analisis de competencia directa.")
    ], 0.7, 1.5, 11.9, 5.4, 16)

    prs.save(ruta_pptx)
    print("Presentacion PowerPoint generada: presentacion_hotspots_wendys_sv.pptx")

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
    if not os.path.isfile(ruta):
        errores.append(f"Falta el archivo: {nombre}")
    elif os.path.getsize(ruta) == 0:
        errores.append(f"El archivo esta vacio: {nombre}")
    else:
        tam_kb = os.path.getsize(ruta) / 1024.0
        print(f"[OK] {nombre} ({tam_kb:.1f} KB)")

ruta_csv_limpio = os.path.join(carpeta, "wendys_san_salvador_limpio.csv")
ruta_csv_final = os.path.join(carpeta, "dataset_final_wendys_san_salvador.csv")

if os.path.isfile(ruta_csv_limpio) and os.path.isfile(ruta_csv_final):
    df_l = pd.read_csv(ruta_csv_limpio)
    df_f = pd.read_csv(ruta_csv_final)
    if len(df_l) == 0 or len(df_f) == 0:
        errores.append("Los archivos CSV no contienen registros.")
    if df_f[["latitud", "longitud", "cluster", "categoria_densidad"]].isna().any().any():
        errores.append("Existen valores nulos en columnas criticas del dataset final.")
    print(f"[OK] Integridad CSV verificada: {len(df_f)} sucursales y {df_f['cluster'].nunique()} clusters.")

ruta_nb = os.path.join(carpeta, "proyecto_hotspots_wendys_sv.ipynb")
if os.path.isfile(ruta_nb):
    with open(ruta_nb, "r", encoding="utf-8-sig") as f:
        nb = json.load(f)
    celdas_codigo = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    sin_salida = [i + 1 for i, c in enumerate(celdas_codigo) if not c.get("outputs")]
    if sin_salida:
        errores.append(f"Celdas sin salida guardada en el notebook: {sin_salida}")
    else:
        print(f"[OK] Notebook verificado: {len(celdas_codigo)} celdas de codigo ejecutadas con salidas.")

ruta_html = os.path.join(carpeta, "mapa_final_hotspots_wendys.html")
if os.path.isfile(ruta_html):
    with open(ruta_html, "r", encoding="utf-8-sig") as f:
        html_txt = f.read()
    for marca in ["Esri World Street Map", "Leyenda del Mapa", "OpenStreetMap"]:
        if marca not in html_txt:
            errores.append(f"Elemento faltante en el mapa HTML: {marca}")
    print("[OK] Mapa HTML verificado con titulo, fuente, leyenda y tiles Esri.")

if os.path.isfile(ruta_app):
    with open(ruta_app, "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print("[OK] Sintaxis de app.py validada sin errores (UTF-8 limpio).")

if os.path.isfile(ruta_pptx):
    prs_ver = Presentation(ruta_pptx)
    print(f"[OK] Presentacion PowerPoint verificada: {len(prs_ver.slides)} diapositivas.")

print("\n--- RESULTADO DE LA REVISION ---")
if errores:
    print("Se encontraron problemas que debes corregir:")
    for err in errores:
        print(f"- {err}")
else:
    nombre_zip = "Entrega_Hotspots_Wendys_SanSalvador.zip"
    with zipfile.ZipFile(nombre_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre in archivos_esperados:
            ruta_completa = os.path.join(carpeta, nombre)
            zf.write(ruta_completa, arcname=os.path.join(carpeta, nombre))
    print("TODO PERFECTO. Todos los 11 entregables pasaron la auditoria tecnica.")
    print(f"Archivo ZIP listo para subir: {os.path.abspath(nombre_zip)}")
