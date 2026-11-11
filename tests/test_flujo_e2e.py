"""
Flujos funcionales de punta a punta (E2E) que cruzan la interfaz web (Selenium)
y la API REST (requests) para el modulo Inscripciones CETO — Foco 1: Ciclo de vida del registro.
"""
import itertools
import uuid

import pytest
import requests

from pages.inscripcion_page import InscripcionPage, ListadoPage

pytestmark = [pytest.mark.ui, pytest.mark.e2e]
TIMEOUT = 10

_secuencia_e2e = itertools.count(1)


def correo_unico_e2e(prefijo="e2e"):
    """Genera un correo institucional unico por prueba para evitar colisiones entre corridas."""
    return f"{prefijo}_{uuid.uuid4().hex[:6]}@ceto.edu.co"


def documento_unico_e2e():
    """Genera un documento numerico de 10 digitos unico en cada llamada."""
    base = str(uuid.uuid4().int)[:6]
    return f"{base}{next(_secuencia_e2e):04d}"


def test_e2e_inscripcion_web_persiste_en_api(driver, base_url, api_url, evidencia):
    """Inscribe por el formulario web y verifica por API que todos los campos quedaron guardados."""
    correo = correo_unico_e2e("web")
    documento = documento_unico_e2e()

    pagina = InscripcionPage(driver, base_url).abrir()
    pagina.inscribir(
        nombre="Sofia Mejia",
        correo=correo,
        documento=documento,
        programa="Ingenieria Industrial",
        semestre=7,
    )
    assert pagina.mensaje_exito().startswith("Inscripcion exitosa. Codigo: EST-")
    evidencia("e2e_01_inscripcion_web")

    r_lista = requests.get(api_url, timeout=TIMEOUT)
    assert r_lista.status_code == 200
    estudiantes = r_lista.json()
    registro = next((e for e in estudiantes if e["correo"] == correo), None)
    assert registro is not None, "La inscripcion realizada en la web no aparece en GET /api/estudiantes"

    try:
        r_detalle = requests.get(f"{api_url}/{registro['id']}", timeout=TIMEOUT)
        assert r_detalle.status_code == 200
        detalle = r_detalle.json()
        assert detalle["nombre"] == "Sofia Mejia"
        assert detalle["correo"] == correo
        assert detalle["documento"] == documento
        assert detalle["programa"] == "Ingenieria Industrial"
        assert detalle["semestre"] == 7
    finally:
        requests.delete(f"{api_url}/{registro['id']}", timeout=TIMEOUT)


def test_e2e_creacion_api_aparece_en_listado_web(driver, base_url, api_url, evidencia):
    """Crea un estudiante mediante POST en la API y comprueba su visualizacion en /estudiantes."""
    nuevo = {
        "nombre": "Mateo Vargas",
        "correo": correo_unico_e2e("api"),
        "documento": documento_unico_e2e(),
        "programa": "Tecnologia en Desarrollo de Software",
        "semestre": 3,
    }
    r_post = requests.post(api_url, json=nuevo, timeout=TIMEOUT)
    assert r_post.status_code == 201
    creado_id = r_post.json()["id"]

    try:
        listado = ListadoPage(driver, base_url).abrir()
        evidencia("e2e_02_listado_desde_api")
        assert nuevo["correo"] in listado.correos()
    finally:
        requests.delete(f"{api_url}/{creado_id}", timeout=TIMEOUT)


def test_e2e_ciclo_completo_vida_registro(driver, base_url, api_url, evidencia):
    """Ejecuta el ciclo completo: crear en web -> listar -> consultar API -> eliminar API -> ausente en web y API."""
    datos_testigo = {
        "nombre": "Camila Torres",
        "correo": correo_unico_e2e("testigo"),
        "documento": documento_unico_e2e(),
        "programa": "Ingenieria Industrial",
        "semestre": 2,
    }
    r_testigo = requests.post(api_url, json=datos_testigo, timeout=TIMEOUT)
    assert r_testigo.status_code == 201
    testigo_id = r_testigo.json()["id"]

    correo_objetivo = correo_unico_e2e("ciclo")
    doc_objetivo = documento_unico_e2e()
    objetivo_id = None

    try:
        pagina = InscripcionPage(driver, base_url).abrir()
        pagina.inscribir(
            nombre="Valentina Rios",
            correo=correo_objetivo,
            documento=doc_objetivo,
            programa="Ingenieria de Sistemas",
            semestre=8,
        )
        assert pagina.mensaje_exito().startswith("Inscripcion exitosa. Codigo: EST-")

        listado_inicial = ListadoPage(driver, base_url).abrir()
        assert correo_objetivo in listado_inicial.correos()

        estudiantes = requests.get(api_url, timeout=TIMEOUT).json()
        encontrado = next((e for e in estudiantes if e["correo"] == correo_objetivo), None)
        assert encontrado is not None
        objetivo_id = encontrado["id"]

        r_get = requests.get(f"{api_url}/{objetivo_id}", timeout=TIMEOUT)
        assert r_get.status_code == 200
        assert r_get.json()["documento"] == doc_objetivo

        r_del = requests.delete(f"{api_url}/{objetivo_id}", timeout=TIMEOUT)
        assert r_del.status_code == 204
        objetivo_id = None

        r_post_borrado = requests.get(f"{api_url}/{encontrado['id']}", timeout=TIMEOUT)
        assert r_post_borrado.status_code == 404

        listado_final = ListadoPage(driver, base_url).abrir()
        evidencia("e2e_03_post_eliminacion")
        correos_finales = listado_final.correos()
        assert correo_objetivo not in correos_finales
        assert datos_testigo["correo"] in correos_finales
    finally:
        requests.delete(f"{api_url}/{testigo_id}", timeout=TIMEOUT)
        if objetivo_id is not None:
            requests.delete(f"{api_url}/{objetivo_id}", timeout=TIMEOUT)


def test_e2e_duplicado_api_rechazado_en_formulario_web(driver, base_url, api_url, evidencia):
    """Registra un correo por API y verifica que el formulario web rechaza reutilizarlo sin duplicar datos."""
    existente = {
        "nombre": "Andres Molina",
        "correo": correo_unico_e2e("dup"),
        "documento": documento_unico_e2e(),
        "programa": "Ingenieria de Sistemas",
        "semestre": 6,
    }
    r_post = requests.post(api_url, json=existente, timeout=TIMEOUT)
    assert r_post.status_code == 201
    creado_id = r_post.json()["id"]

    try:
        pagina = InscripcionPage(driver, base_url).abrir()
        pagina.inscribir(
            nombre="Laura Perez",
            correo=existente["correo"],
            documento=documento_unico_e2e(),
            programa="Ingenieria Industrial",
            semestre=4,
        )
        evidencia("e2e_04_rechazo_duplicado_web")
        assert pagina.error_de("correo") == "El correo ya esta registrado"

        estudiantes = requests.get(api_url, timeout=TIMEOUT).json()
        coincidencias = [e for e in estudiantes if e["correo"] == existente["correo"]]
        assert len(coincidencias) == 1
        assert coincidencias[0]["nombre"] == "Andres Molina"
    finally:
        requests.delete(f"{api_url}/{creado_id}", timeout=TIMEOUT)