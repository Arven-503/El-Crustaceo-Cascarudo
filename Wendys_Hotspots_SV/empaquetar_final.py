import os
import io
import ast
import json
import shutil
import contextlib

carpeta = "entregables_finales"

shutil.copy2("wendys_san_salvador_limpio.csv", os.path.join(carpeta, "wendys_san_salvador_limpio.csv"))
shutil.copy2("app.py", os.path.join(carpeta, "app.py"))

ruta_req = os.path.join(carpeta, "requirements.txt")
with open(ruta_req, "w", encoding="utf-8") as f:
    f.write("pandas\nnumpy\nscikit-learn\nfolium\nstreamlit\nrequests\n")

ruta_readme = os.path.join(carpeta, "README.md")
readme_txt = [
    "# Hotspots Comerciales de El Salvador - Caso Wendy's (San Salvador)",
    "",
    "## Instrucciones de Ejecucion",
    "1. Instalar dependencias: `pip install -r requirements.txt`",
    "2. Ejecutar aplicacion interactiva: `streamlit run app.py`",
    "3. Abrir mapa independiente: doble clic en `mapa_final_hotspots_wendys.html`",
    "4. Abrir notebook ejecutable: `proyecto_hotspots_wendys_sv.ipynb`"
]
with open(ruta_readme, "w", encoding="utf-8") as f:
    f.write("\n".join(readme_txt))

ruta_nb = os.path.join(carpeta, "proyecto_hotspots_wendys_sv.ipynb")
with open(ruta_nb, "r", encoding="utf-8") as f:
    nb_data = json.load(f)

for celda in nb_data.get("cells", []):
    if celda.get("cell_type") == "code":
        celda["source"] = [
            linea.replace("../wendys_san_salvador_limpio.csv", "wendys_san_salvador_limpio.csv")
            for linea in celda.get("source", [])
        ]

dir_original = os.getcwd()
os.chdir(carpeta)
entorno_exec = {}
contador = 1

try:
    for celda in nb_data.get("cells", []):
        if celda.get("cell_type") != "code":
            continue
        codigo = "".join(celda.get("source", []))
        buf = io.StringIO()
        res = None
        arbol = ast.parse(codigo)
        with contextlib.redirect_stdout(buf):
            if arbol.body and isinstance(arbol.body[-1], ast.Expr):
                previo = ast.Module(body=arbol.body[:-1], type_ignores=[])
                ultima = ast.Expression(body=arbol.body[-1].value)
                exec(compile(previo, "<nb>", "exec"), entorno_exec)
                res = eval(compile(ultima, "<nb>", "eval"), entorno_exec)
            else:
                exec(compile(arbol, "<nb>", "exec"), entorno_exec)

        salidas = []
        txt_out = buf.getvalue()
        if txt_out:
            salidas.append({"name": "stdout", "output_type": "stream", "text": txt_out.splitlines(keepends=True)})
        if res is not None:
            dd = {"text/plain": repr(res).splitlines(keepends=True)}
            if hasattr(res, "to_html"):
                dd["text/html"] = res.to_html().splitlines(keepends=True)
            salidas.append({"data": dd, "execution_count": contador, "metadata": {}, "output_type": "execute_result"})
        celda["execution_count"] = contador
        celda["outputs"] = salidas
        contador += 1
finally:
    os.chdir(dir_original)

with open(ruta_nb, "w", encoding="utf-8") as f:
    json.dump(nb_data, f, indent=2, ensure_ascii=False)

print("Carpeta entregables_finales actualizada y 100% autocontenida.")
