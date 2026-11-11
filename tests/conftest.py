"""
Fixtures compartidas.
  - servidor: levanta la mini app en un hilo (puerto libre) una sola vez por sesion.
  - api_url / base_url: direcciones para las pruebas.
  - driver: navegador Chrome (headless por defecto) que se cierra siempre.
  - Captura de pantalla automatica cuando falla una prueba de interfaz.
"""
import os
import re
import threading
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from werkzeug.serving import make_server

from app.servidor import crear_app

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"


@pytest.fixture(scope="session")
def base_url():
    # Si se define BASE_URL se prueba un servidor externo; si no, se levanta uno local
    externo = os.environ.get("BASE_URL")
    if externo:
        yield externo.rstrip("/")
        return
    # puerto 0 = el sistema elige uno libre; threaded=True atiende al navegador y a requests a la vez
    servidor = make_server("127.0.0.1", 0, crear_app(), threaded=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_port}"
    servidor.shutdown()


@pytest.fixture(scope="session")
def api_url(base_url):
    return f"{base_url}/api/estudiantes"


@pytest.fixture
def driver():
    opciones = webdriver.ChromeOptions()
    if os.environ.get("HEADLESS", "1") == "1":
        opciones.add_argument("--headless=new")
    opciones.add_argument("--window-size=1366,900")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    if os.environ.get("CHROME_BIN"):
        opciones.binary_location = os.environ["CHROME_BIN"]
    servicio = Service(os.environ["CHROMEDRIVER"]) if os.environ.get("CHROMEDRIVER") else Service()
    navegador = webdriver.Chrome(options=opciones, service=servicio)
    yield navegador
    navegador.quit()


@pytest.fixture
def evidencia(driver, request):
    """Permite guardar capturas a voluntad: evidencia('01_formulario_lleno')."""
    EVIDENCIAS.mkdir(exist_ok=True)

    def tomar(nombre):
        ruta = EVIDENCIAS / f"{request.node.name}__{nombre}.png"
        driver.save_screenshot(str(ruta))
        return ruta
    return tomar


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    reporte = resultado.get_result()
    if reporte.when == "call" and reporte.failed:
        navegador = item.funcargs.get("driver")
        if navegador is not None:
            EVIDENCIAS.mkdir(exist_ok=True)
            nombre = re.sub(r"[^\w\-]", "_", item.name)
            navegador.save_screenshot(str(EVIDENCIAS / f"FALLO__{nombre}.png"))
