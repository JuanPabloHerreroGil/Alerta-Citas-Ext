"""
diagnostico.py — Comprueba si el problema es un bloqueo de IP o de "huella" de navegador.
No usa Playwright, solo una petición HTTP normal (como haría 'requests' de toda la vida).
"""
import requests
 
url = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
 
print(f"Probando conexión a: {url}")
try:
    r = requests.get(url, headers=headers, timeout=20)
    print(f"✅ Respuesta recibida. Status code: {r.status_code}")
    print(f"Tamaño de la respuesta: {len(r.text)} caracteres")
    print("Primeros 500 caracteres de la respuesta:")
    print(r.text[:500])
except requests.exceptions.Timeout:
    print("❌ TIMEOUT: la conexión ni siquiera responde. Fuerte indicio de bloqueo por IP.")
except requests.exceptions.ConnectionError as e:
    print(f"❌ ERROR DE CONEXIÓN: {e}")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
