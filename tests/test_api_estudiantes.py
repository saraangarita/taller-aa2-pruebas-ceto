"""
Pruebas automatizadas para la API REST de Inscripciones CETO (/api/estudiantes).
Cubre operaciones CRUD, valores limite, clases de equivalencia y manejo de errores HTTP.
"""
import itertools
import uuid

import pytest
import requests

pytestmark = pytest.mark.api
TIMEOUT = 10

_secuencia_doc = itertools.count(1)


def correo_unico():
    """Genera un correo institucional distinto en cada prueba para asegurar independencia."""
    return f"est_{uuid.uuid4().hex[:8]}@ceto.edu.co"


def documento_unico():
    """Genera un documento numerico de 10 digitos unico en cada invocacion."""
    prefijo = str(uuid.uuid4().int)[:6]
    return f"{prefijo}{next(_secuencia_doc):04d}"


@pytest.fixture
def estudiante_valido():
    """Datos base validos e independientes para registrar un estudiante."""
    return {
        "nombre": "Ana Ruiz",
        "correo": correo_unico(),
        "documento": documento_unico(),
        "programa": "Ingenieria de Sistemas",
        "semestre": 4,
    }


@pytest.fixture
def estudiante_creado(api_url, estudiante_valido):
    """Crea un estudiante antes de la prueba (setup) y lo elimina al terminar (teardown)."""
    r = requests.post(api_url, json=estudiante_valido, timeout=TIMEOUT)
    assert r.status_code == 201
    creado = r.json()
    yield creado
    requests.delete(f"{api_url}/{creado['id']}", timeout=TIMEOUT)


# ------------------------- Camino feliz y valores limite validos -------------------------

def test_crear_estudiante_devuelve_201_y_el_recurso(api_url, estudiante_valido):
    r = requests.post(api_url, json=estudiante_valido, timeout=TIMEOUT)

    assert r.status_code == 201
    assert r.headers["Content-Type"].startswith("application/json")
    cuerpo = r.json()
    assert isinstance(cuerpo["id"], int)
    assert cuerpo["nombre"] == estudiante_valido["nombre"]
    assert cuerpo["correo"] == estudiante_valido["correo"]
    assert cuerpo["documento"] == estudiante_valido["documento"]
    assert cuerpo["programa"] == estudiante_valido["programa"]
    assert cuerpo["semestre"] == estudiante_valido["semestre"]

    requests.delete(f"{api_url}/{cuerpo['id']}", timeout=TIMEOUT)


def test_consultar_estudiante_por_id(api_url, estudiante_creado):
    r = requests.get(f"{api_url}/{estudiante_creado['id']}", timeout=TIMEOUT)

    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")
    assert r.json() == estudiante_creado


def test_listar_estudiantes_contiene_el_creado(api_url, estudiante_creado):
    r = requests.get(api_url, timeout=TIMEOUT)

    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/json")
    listado = r.json()
    assert isinstance(listado, list)
    assert estudiante_creado in listado


def test_filtrar_estudiantes_por_programa(api_url, estudiante_creado):
    # Se crea un estudiante de otro programa para verificar que el filtro realmente excluye
    otro_estudiante = {
        "nombre": "Carlos Mejia",
        "correo": correo_unico(),
        "documento": documento_unico(),
        "programa": "Ingenieria Industrial",
        "semestre": 3,
    }
    r_otro = requests.post(api_url, json=otro_estudiante, timeout=TIMEOUT)
    assert r_otro.status_code == 201
    otro_id = r_otro.json()["id"]

    try:
        r = requests.get(
            api_url,
            params={"programa": "Ingenieria de Sistemas"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        filtrados = r.json()
        assert len(filtrados) >= 1
        assert all(e["programa"] == "Ingenieria de Sistemas" for e in filtrados)
        assert any(e["id"] == estudiante_creado["id"] for e in filtrados)
        assert all(e["id"] != otro_id for e in filtrados)
    finally:
        requests.delete(f"{api_url}/{otro_id}", timeout=TIMEOUT)


def test_eliminar_estudiante_devuelve_204_y_luego_404(api_url, estudiante_creado):
    url_recurso = f"{api_url}/{estudiante_creado['id']}"

    r_del = requests.delete(url_recurso, timeout=TIMEOUT)
    assert r_del.status_code == 204
    assert r_del.text == ""

    r_get = requests.get(url_recurso, timeout=TIMEOUT)
    assert r_get.status_code == 404
    assert r_get.json()["error"] == "Estudiante no encontrado"


@pytest.mark.parametrize(
    "semestre_limite",
    [1, 10],
    ids=["semestre_minimo_1", "semestre_maximo_10"],
)
def test_semestre_en_valores_limite_validos_devuelve_201(api_url, estudiante_valido, semestre_limite):
    estudiante_valido["semestre"] = semestre_limite
    r = requests.post(api_url, json=estudiante_valido, timeout=TIMEOUT)

    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["semestre"] == semestre_limite
    requests.delete(f"{api_url}/{cuerpo['id']}", timeout=TIMEOUT)


# ------------------------- Casos de error (422, 409, 400 y 404) -------------------------

@pytest.mark.parametrize(
    "campo, valor, mensaje",
    [
        ("nombre", "", "El nombre es obligatorio (minimo 3 caracteres)"),
        ("correo", "correo-sin-arroba", "Correo invalido"),
        ("documento", "12345", "El documento debe contener entre 6 y 10 digitos"),
        ("documento", "12345678901", "El documento debe contener entre 6 y 10 digitos"),
        ("documento", "12345abc", "El documento debe contener entre 6 y 10 digitos"),
        ("programa", "Medicina", "Programa no valido"),
        ("semestre", 0, "El semestre debe ser un numero entre 1 y 10"),
        ("semestre", 11, "El semestre debe ser un numero entre 1 y 10"),
    ],
    ids=[
        "nombre_vacio",
        "correo_invalido",
        "documento_corto_5",
        "documento_largo_11",
        "documento_no_numerico",
        "programa_inexistente",
        "semestre_0",
        "semestre_11",
    ],
)
def test_datos_invalidos_devuelven_422(api_url, estudiante_valido, campo, valor, mensaje):
    estudiante_valido[campo] = valor
    r = requests.post(api_url, json=estudiante_valido, timeout=TIMEOUT)

    assert r.status_code == 422
    cuerpo = r.json()
    assert cuerpo["errores"][campo] == mensaje
    assert len(cuerpo["errores"]) == 1


def test_correo_duplicado_devuelve_409(api_url, estudiante_creado, estudiante_valido):
    # pytest comparte la instancia de estudiante_valido con estudiante_creado en el mismo test;
    # se genera un documento nuevo para aislar unicamente el conflicto de correo (409).
    nuevo = {
        **estudiante_valido,
        "correo": estudiante_creado["correo"],
        "documento": documento_unico(),
    }
    r = requests.post(api_url, json=nuevo, timeout=TIMEOUT)

    assert r.status_code == 409
    assert r.json()["errores"]["correo"] == "El correo ya esta registrado"


def test_documento_duplicado_devuelve_409(api_url, estudiante_creado, estudiante_valido):
    # Se genera un correo nuevo para aislar unicamente el conflicto de documento (409).
    nuevo = {
        **estudiante_valido,
        "correo": correo_unico(),
        "documento": estudiante_creado["documento"],
    }
    r = requests.post(api_url, json=nuevo, timeout=TIMEOUT)

    assert r.status_code == 409
    assert r.json()["errores"]["documento"] == "El documento ya esta registrado"


def test_cuerpo_no_json_devuelve_400(api_url):
    r = requests.post(
        api_url,
        data="texto plano sin formato json",
        headers={"Content-Type": "text/plain"},
        timeout=TIMEOUT,
    )

    assert r.status_code == 400
    assert r.json()["error"] == "El cuerpo debe ser JSON"


def test_consultar_y_eliminar_id_inexistente_devuelve_404(api_url):
    url_inexistente = f"{api_url}/999999"

    r_get = requests.get(url_inexistente, timeout=TIMEOUT)
    assert r_get.status_code == 404
    assert r_get.json()["error"] == "Estudiante no encontrado"

    r_del = requests.delete(url_inexistente, timeout=TIMEOUT)
    assert r_del.status_code == 404
    assert r_del.json()["error"] == "Estudiante no encontrado"