"""
main.py — Detector de citas de Extranjería (Registro de Ciudadano de la Unión)
--------------------------------------------------------------------------------
Diseñado para ejecutarse UNA VEZ por invocación (GitHub Actions lo relanza
cada 15 minutos vía cron). No reserva citas, solo detecta y avisa por Telegram.

MODO DEBUG: si algún paso falla (no encuentra la provincia/trámite/oficina
esperados), el script:
  1) imprime en los logs TODAS las opciones reales que ha visto en la web
  2) guarda una captura de pantalla (debug.png)
para que puedas ajustar los textos de configuración sin tener que inspeccionar
la web tú mismo con F12.
"""

import os
import sys
import requests
from playwright.sync_api import sync_playwright

# ==============================================================================
# CONFIGURACIÓN — ajusta esto a tu caso
# ==============================================================================
PROVINCIA = "Illes Balears"
TRAMITE_TEXTO = "REGISTRO DE CIUDADANO DE LA UNIÓN"   # palabra clave del trámite
OFICINA_TEXTO = ""   # déjalo vacío si Mallorca solo tiene una oficina para este trámite

# Credenciales — NUNCA las escribas aquí directamente. Se leen de GitHub Secrets.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

URL_INICIO = "https://icp.administracionelectronica.gob.es/icpplus/index.html"


def notificar_telegram(mensaje: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no configurados (revisa los Secrets).")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("✅ Telegram OK" if r.status_code == 200 else f"❌ Telegram error: {r.text}")
    except Exception as e:
        print(f"❌ Excepción enviando Telegram: {e}")


def guardar_captura(page, nombre="debug.png"):
    try:
        page.screenshot(path=nombre, full_page=True)
        print(f"📸 Captura guardada: {nombre} (se subirá como artifact)")
    except Exception as e:
        print(f"No se pudo guardar captura: {e}")


def elegir_opcion(select_locator, texto_buscado: str, nombre_paso: str):
    """
    Busca en un <select> la opción cuyo texto contenga `texto_buscado`.
    Si no la encuentra, imprime TODAS las opciones reales para que puedas
    corregir la configuración.
    """
    opciones = select_locator.locator("option").all_inner_texts()
    print(f"--- Opciones reales encontradas en '{nombre_paso}' ---")
    for o in opciones:
        print(f"   · {o.strip()}")

    encontrada = next((o for o in opciones if texto_buscado.lower() in o.lower()), None)
    if not encontrada:
        print(f"⚠️ No se encontró ninguna opción que contenga '{texto_buscado}' en '{nombre_paso}'.")
        print("   Copia el texto EXACTO de arriba y actualiza la variable correspondiente.")
        return None
    select_locator.select_option(label=encontrada)
    print(f"✅ '{nombre_paso}' → seleccionado: {encontrada.strip()}")
    return encontrada


def comprobar_citas():
    print("🔎 Iniciando comprobación...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        )
        page = context.new_page()

        try:
            # 1. Página inicial
            page.goto(URL_INICIO, timeout=90000, wait_until="domcontentloaded")

            # 2. Provincia
            try:
                select_provincia = page.locator("select[name='form']").first
                if elegir_opcion(select_provincia, PROVINCIA, "Provincia") is None:
                    guardar_captura(page, "debug_provincia.png")
                    return
                page.click("input[id='btnAceptar']")
            except Exception as e:
                print(f"❌ Error en el paso Provincia: {e}")
                guardar_captura(page, "debug_provincia.png")
                return

            # 3. Trámite
            try:
                page.wait_for_selector("select[id^='tramiteGrupo']", timeout=10000)
                select_tramite = page.locator("select[id^='tramiteGrupo']").first
                if elegir_opcion(select_tramite, TRAMITE_TEXTO, "Trámite") is None:
                    guardar_captura(page, "debug_tramite.png")
                    return
                page.click("input[id='btnAceptar']")
            except Exception as e:
                print(f"❌ Error en el paso Trámite: {e}")
                guardar_captura(page, "debug_tramite.png")
                return

            # 4. Oficina (opcional — solo si hay más de una en Mallorca)
            if OFICINA_TEXTO:
                try:
                    if page.locator("select[id='sede']").count() > 0:
                        select_oficina = page.locator("select[id='sede']").first
                        elegir_opcion(select_oficina, OFICINA_TEXTO, "Oficina")
                except Exception as e:
                    print(f"(Aviso, no bloqueante) Paso Oficina: {e}")

            # 5. Entrar
            try:
                page.wait_for_selector("input[id='btnEntrar']", timeout=10000)
                page.click("input[id='btnEntrar']")
            except Exception as e:
                print(f"❌ Error en el paso 'Entrar': {e}")
                guardar_captura(page, "debug_entrar.png")
                return

            # 6. Resultado
            contenido = page.content().lower()
            guardar_captura(page, "debug_resultado.png")

            sin_citas = (
                "en este momento no hay citas disponibles" in contenido
                or "no hay citas disponibles" in contenido
                or "el número de citas disponible es muy reducido" in contenido
            )

            if not sin_citas:
                mensaje = (
                    "🚨 <b>¡CITAS DISPONIBLES EN EXTRANJERÍA!</b> 🚨\n\n"
                    f"<b>Provincia:</b> {PROVINCIA}\n"
                    f"<b>Trámite:</b> {TRAMITE_TEXTO}\n\n"
                    f"👉 Entra ya a reservar: {URL_INICIO}"
                )
                print("🎉 ¡CITAS DETECTADAS!")
                notificar_telegram(mensaje)
            else:
                print("ℹ️ Sin citas disponibles por ahora.")

        except Exception as e:
            print(f"❌ Error general: {e}")
            guardar_captura(page, "debug_error.png")
        finally:
            browser.close()


if __name__ == "__main__":
    comprobar_citas()
