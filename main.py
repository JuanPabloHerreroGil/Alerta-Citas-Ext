import os
import requests
from playwright.sync_api import sync_playwright

PROVINCIA = "Illes Balears"
TRAMITE_TEXTO = "TOMA DE HUELLAS"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
URL_INICIO = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

# Lista de proxies gratuitos de apoyo (HTTP/SOCKS)
PROXIES = [
    None,  # Intento directo primero
    "http://185.162.229.74:80",
    "http://51.159.66.157:3128",
]

def notificar(mensaje):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            print(f"Error enviando notificación: {e}")

def comprobar():
    print("🔎 Iniciando revisión con evitación de bloqueos...")
    
    with sync_playwright() as p:
        for proxy_url in PROXIES:
            browser = None
            try:
                launch_options = {"headless": True}
                if proxy_url:
                    print(f"🔄 Intentando conexión a través de proxy: {proxy_url}")
                    launch_options["proxy"] = {"server": proxy_url}

                browser = p.chromium.launch(**launch_options)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="es-ES"
                )
                page = context.new_page()

                # Timeout de 20 segundos por intento
                page.goto(URL_INICIO, timeout=20000, wait_until="domcontentloaded")
                
                print("✅ Conexión establecida con la Sede Electrónica.")
                page.select_option("select[name='form']", label=PROVINCIA)
                page.click("input[id='btnAceptar']")
                
                page.wait_for_selector("select[id^='tramiteGrupo']", timeout=10000)
                select_elem = page.locator("select[id^='tramiteGrupo']").first
                options = select_elem.locator("option").all_inner_texts()
                opcion = next((opt for opt in options if TRAMITE_TEXTO.lower() in opt.lower()), None)
                
                if opcion:
                    select_elem.select_option(label=opcion)
                    page.click("input[id='btnAceptar']")
                    page.wait_for_selector("input[id='btnEntrar']", timeout=10000)
                    page.click("input[id='btnEntrar']")
                    
                    contenido = page.content().lower()
                    sin_citas = "no hay citas disponibles" in contenido or "en este momento no hay citas" in contenido
                    
                    if not sin_citas:
                        msg = f"🚨 <b>¡CITAS DISPONIBLES EN {PROVINCIA}!</b>\nTrámite: {TRAMITE_TEXTO}\n👉 Entra ya: {URL_INICIO}"
                        notificar(msg)
                        print("🎉 ¡Cita detectada!")
                    else:
                        print("ℹ️ No hay citas en este momento.")
                
                # Si todo sale bien, salimos del bucle
                browser.close()
                return

            except Exception as e:
                print(f"⚠️ Fallo en intento: {e}")
                if browser:
                    browser.close()

    print("❌ Todos los intentos de conexión han sido bloqueados por el cortafuegos.")

if __name__ == "__main__":
    comprobar()
