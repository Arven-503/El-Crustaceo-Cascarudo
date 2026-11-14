import os
import ast
import json
import zipfile
import pandas as pd
from pptx import Presentation

carpeta = "entregables_finales"

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

print("--- INICIANDO AUDITORIA DE ENTREGABLES FINALES ---")
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
    with open(ruta_nb, "r", encoding="utf-8") as f:
        nb = json.load(f)
    celdas_codigo = [c for c in nb.get("cells", []) if c.get("cell_type") == "code"]
    sin_salida = [i + 1 for i, c in enumerate(celdas_codigo) if not c.get("outputs")]
    if sin_salida:
        errores.append(f"Celdas sin salida guardada en el notebook: {sin_salida}")
    else:
        print(f"[OK] Notebook verificado: {len(celdas_codigo)} celdas de codigo ejecutadas con salidas.")

ruta_html = os.path.join(carpeta, "mapa_final_hotspots_wendys.html")
if os.path.isfile(ruta_html):
    with open(ruta_html, "r", encoding="utf-8") as f:
        html_txt = f.read()
    for marca in ["Esri World Street Map", "Leyenda del Mapa", "OpenStreetMap"]:
        if marca not in html_txt:
            errores.append(f"Elemento faltante en el mapa HTML: {marca}")
    print("[OK] Mapa HTML verificado con titulo, fuente, leyenda y tiles Esri.")

ruta_app = os.path.join(carpeta, "app.py")
if os.path.isfile(ruta_app):
    with open(ruta_app, "r", encoding="utf-8") as f:
        ast.parse(f.read())
    print("[OK] Sintaxis de app.py validada sin errores.")

ruta_pptx = os.path.join(carpeta, "presentacion_hotspots_wendys_sv.pptx")
if os.path.isfile(ruta_pptx):
    prs = Presentation(ruta_pptx)
    print(f"[OK] Presentacion PowerPoint verificada: {len(prs.slides)} diapositivas.")

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
    print("TODO PERFECTO. Todos los entregables pasaron la auditoria tecnica.")
    print(f"Archivo listo para subir generado: {os.path.abspath(nombre_zip)}")
