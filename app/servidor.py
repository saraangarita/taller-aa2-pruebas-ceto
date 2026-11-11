"""
Mini aplicacion "Inscripciones CETO" (sistema bajo prueba del Taller U2).

Incluye:
  - API REST  /api/estudiantes   (GET, POST, GET/<id>, DELETE/<id>)
  - Formulario web /inscripcion  (para pruebas con Selenium)
  - Listado web    /estudiantes

Ejecutar:  python -m app.servidor      ->  http://127.0.0.1:5000
Los datos viven en memoria: al reiniciar el servidor se pierden (ideal para pruebas).
"""
import re
import time

from flask import Flask, jsonify, render_template, request

PROGRAMAS = ["Ingenieria de Sistemas", "Tecnologia en Desarrollo de Software", "Ingenieria Industrial"]
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def crear_app():
    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False
    estudiantes = {}
    contador = {"id": 0}

    def validar(datos):
        """Devuelve un diccionario de errores {campo: mensaje}. Vacio = datos validos."""
        errores = {}
        nombre = (datos.get("nombre") or "").strip()
        correo = (datos.get("correo") or "").strip().lower()
        documento = (datos.get("documento") or "").strip()
        programa = (datos.get("programa") or "").strip()
        semestre = datos.get("semestre")
        
        if not documento.isdigit() or not 6 <= len(documento) <= 10:
            errores["documento"] = "El documento debe contener entre 6 y 10 digitos"
        elif any(e["documento"] == documento for e in estudiantes.values()):
             errores["documento"] = "El documento ya esta registrado"

        if len(nombre) < 3:
            errores["nombre"] = "El nombre es obligatorio (minimo 3 caracteres)"
        if not PATRON_CORREO.match(correo):
            errores["correo"] = "Correo invalido"
        elif any(e["correo"] == correo for e in estudiantes.values()):
            errores["correo"] = "El correo ya esta registrado"
        if programa not in PROGRAMAS:
            errores["programa"] = "Programa no valido"
        try:
            semestre = int(semestre)
            if not 1 <= semestre <= 10:
                raise ValueError
        except (TypeError, ValueError):
            errores["semestre"] = "El semestre debe ser un numero entre 1 y 10"
        return errores, {"nombre": nombre, "correo": correo, "documento": documento, "programa": programa, "semestre": semestre}

    def guardar(limpio):
        contador["id"] += 1
        estudiante = {"id": contador["id"], **limpio}
        estudiantes[estudiante["id"]] = estudiante
        return estudiante

    # ------------------------- API REST -------------------------
    @app.get("/api/estudiantes")
    def listar():
        programa = request.args.get("programa")
        datos = [e for e in estudiantes.values() if not programa or e["programa"] == programa]
        return jsonify(datos), 200

    @app.get("/api/estudiantes/<int:id_est>")
    def obtener(id_est):
        if id_est not in estudiantes:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        return jsonify(estudiantes[id_est]), 200

    @app.post("/api/estudiantes")
    def crear():
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify({"error": "El cuerpo debe ser JSON"}), 400
        errores, limpio = validar(datos)
        if errores:
            duplicado = errores.get("correo") == "El correo ya esta registrado" or errores.get("documento") == "El documento ya esta registrado"
            codigo = 409 if duplicado and len(errores) == 1 else 422
            return jsonify({"errores": errores}), codigo
        return jsonify(guardar(limpio)), 201

    @app.delete("/api/estudiantes/<int:id_est>")
    def eliminar(id_est):
        if estudiantes.pop(id_est, None) is None:
            return jsonify({"error": "Estudiante no encontrado"}), 404
        return "", 204

    # ------------------------- Paginas web -------------------------
    @app.route("/inscripcion", methods=["GET", "POST"])
    def inscripcion():
        if request.method == "GET":
            return render_template("inscripcion.html", programas=PROGRAMAS, errores={}, datos={}, exito=None)
        time.sleep(0.5)  # latencia simulada del servidor: obliga a usar esperas explicitas
        errores, limpio = validar(request.form)
        if errores:
            return render_template("inscripcion.html", programas=PROGRAMAS, errores=errores,
                                   datos=request.form, exito=None), 200
        est = guardar(limpio)
        return render_template("inscripcion.html", programas=PROGRAMAS, errores={}, datos={},
                               exito=f"Inscripcion exitosa. Codigo: EST-{est['id']:04d}")

    @app.get("/estudiantes")
    def pagina_listado():
        return render_template("estudiantes.html", estudiantes=list(estudiantes.values()))

    return app


if __name__ == "__main__":
    crear_app().run(port=5000, debug=False)
