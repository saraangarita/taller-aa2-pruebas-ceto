"""
Pruebas automatizadas de interfaz web para el formulario de inscripcion (/inscripcion)
y su verificacion en el listado (/estudiantes), aplicando Page Object Model y datos CSV.
"""
import csv
import itertools
import uuid
from pathlib import Path

import pytest

from pages.inscripcion_page import InscripcionPage, ListadoPage

pytestmark = pytest.mark.ui
DATOS = Path(__file__).resolve().parent.parent / "data" / "casos_formulario.csv"

_secuencia_ui = itertools.count(1)


def documento_unico_ui():
    prefijo = str(uuid.uuid4().int)[:6]
    return f"{prefijo}{next(_secuencia_ui):04d}"


def cargar_casos_invalidos():
    with open(DATOS, encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        return [
            pytest.param(fila, id=fila["caso"].strip())
            for fila in lector
            if fila.get("caso") and fila["caso"].strip()
        ]


def test_inscripcion_exitosa_aparece_en_listado(driver, base_url, evidencia):
    correo = f"carlos_{uuid.uuid4().hex[:6]}@ceto.edu.co"
    documento = documento_unico_ui()

    pagina = InscripcionPage(driver, base_url).abrir()
    evidencia("01_formulario_vacio")

    pagina.inscribir(
        nombre="Carlos Gomez",
        correo=correo,
        documento=documento,
        programa="Ingenieria de Sistemas",
        semestre=5,
    )
    evidencia("02_resultado")

    assert pagina.mensaje_exito().startswith("Inscripcion exitosa. Codigo: EST-")

    listado = ListadoPage(driver, base_url).abrir()
    evidencia("03_listado")
    assert correo in listado.correos()


@pytest.mark.parametrize("caso", cargar_casos_invalidos())
def test_formulario_muestra_error_por_campo(driver, base_url, caso):
    pagina = InscripcionPage(driver, base_url).abrir()
    pagina.inscribir(
        nombre=caso["nombre"],
        correo=caso["correo"],
        documento=caso["documento"],
        programa=caso["programa"],
        semestre=caso["semestre"],
    )

    assert pagina.error_de(caso["campo_error"]) == caso["mensaje_esperado"]
    assert len(pagina.errores()) == 1


def test_formulario_conserva_datos_validos_tras_error(driver, base_url):
    pagina = InscripcionPage(driver, base_url).abrir()
    pagina.inscribir(
        nombre="Luis Pinto",
        correo="luis-ceto.edu.co",
        documento="1020304050",
        programa="Ingenieria de Sistemas",
        semestre=3,
    )

    assert pagina.error_de("correo") == "Correo invalido"
    assert pagina.valor_de("nombre") == "Luis Pinto"
    assert pagina.valor_de("documento") == "1020304050"
    assert pagina.programa_seleccionado() == "Ingenieria de Sistemas"