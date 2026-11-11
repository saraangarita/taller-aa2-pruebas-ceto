"""
Page Objects de las vistas web de Inscripciones CETO (/inscripcion y /estudiantes).
Separa los localizadores y las acciones de Selenium de las aserciones de prueba.
"""
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class InscripcionPage:
    NOMBRE = (By.ID, "nombre")
    CORREO = (By.ID, "correo")
    DOCUMENTO = (By.ID, "documento")
    PROGRAMA = (By.ID, "programa")
    SEMESTRE = (By.ID, "semestre")
    BOTON = (By.ID, "btn-inscribir")
    EXITO = (By.ID, "mensaje-exito")
    ERRORES = (By.CSS_SELECTOR, ".error")

    def __init__(self, driver, base_url, timeout=10):
        self.driver = driver
        self.url = f"{base_url}/inscripcion"
        self.wait = WebDriverWait(driver, timeout)

    def abrir(self):
        self.driver.get(self.url)
        self.wait.until(EC.visibility_of_element_located(self.NOMBRE))
        return self

    def _escribir(self, localizador, valor):
        campo = self.driver.find_element(*localizador)
        campo.clear()
        if valor is not None and str(valor) != "":
            campo.send_keys(str(valor))

    def inscribir(self, nombre, correo, documento, programa, semestre):
        self._escribir(self.NOMBRE, nombre)
        self._escribir(self.CORREO, correo)
        self._escribir(self.DOCUMENTO, documento)

        selector = Select(self.driver.find_element(*self.PROGRAMA))
        if programa:
            selector.select_by_visible_text(programa)
        else:
            selector.select_by_value("")

        self._escribir(self.SEMESTRE, semestre)

        boton = self.driver.find_element(*self.BOTON)
        boton.click()
        # Espera explicita a que el DOM anterior deje de existir tras la recarga del envio
        WebDriverWait(self.driver, 10, ignored_exceptions=(WebDriverException,)).until(
            EC.staleness_of(boton)
        )

    def mensaje_exito(self):
        return self.wait.until(EC.visibility_of_element_located(self.EXITO)).text

    def errores(self):
        return [e.text for e in self.driver.find_elements(*self.ERRORES)]

    def error_de(self, campo):
        return self.wait.until(
            EC.visibility_of_element_located((By.ID, f"error-{campo}"))
        ).text

    def valor_de(self, campo):
        return self.driver.find_element(By.ID, campo).get_attribute("value")

    def programa_seleccionado(self):
        return Select(self.driver.find_element(*self.PROGRAMA)).first_selected_option.get_attribute("value")


class ListadoPage:
    FILAS = (By.CSS_SELECTOR, "#tabla-estudiantes tbody tr.fila-estudiante")
    TOTAL = (By.ID, "total")

    def __init__(self, driver, base_url, timeout=10):
        self.driver = driver
        self.url = f"{base_url}/estudiantes"
        self.wait = WebDriverWait(driver, timeout)

    def abrir(self):
        self.driver.get(self.url)
        self.wait.until(EC.visibility_of_element_located(self.TOTAL))
        return self

    def correos(self):
        # Columnas: Codigo(0) | Nombre(1) | Correo(2) | Programa(3) | Semestre(4)
        return [
            fila.find_elements(By.TAG_NAME, "td")[2].text
            for fila in self.driver.find_elements(*self.FILAS)
        ]