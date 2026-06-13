#!/usr/bin/env python3
"""
Subir Video a YouTube vía GitHub Release + Make.com webhook
============================================================
1. Crea un GitHub Release con el video como asset público
2. Verifica que la URL es descargable (sigue 302 redirects, valida tamaño)
3. Llama al webhook de Make.com con la URL pública del video + metadatos
Make.com descarga el video y lo sube a YouTube automáticamente.

Uso (desde GitHub Actions):
  python subir_video.py video_final.mp4 guion.txt titulo_video.txt palabras_clave.txt
"""
import sys
import os
import json
import time
import requests
from datetime import datetime
from typing import Tuple


GITHUB_API = "https://api.github.com"
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/d4m5v8d05qfrwfq7ergbxi4a2qgqhwjf"

# Metadatos fijos del canal
CANAL_DESCRIPCION_PIE = """
━━━━━━━━━━━━━━━━━━━━━━━
🧠 UNIVERSO DE LA MENTE
Psicología, narcisismo y relaciones tóxicas
━━━━━━━━━━━━━━━━━━━━━━━
📌 Suscríbete para no perderte nada:
https://www.youtube.com/@universodelaamente

🔔 Activa la campanita para recibir cada vídeo nuevo

📲 ¿Has vivido algo parecido? Cuéntamelo en los comentarios.
━━━━━━━━━━━━━━━━━━━━━━━
#narcisismo #psicología #relacionestóxicas #saludmental #autoestima
"""


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def leer_fichero(path: str, fallback: str = "") -> str:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return fallback


def obtener_repo_info() -> tuple:
    """Lee GITHUB_REPOSITORY (formato: owner/repo) y GITHUB_TOKEN del entorno."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not repo or not token:
        log("ERROR: GITHUB_REPOSITORY o GITHUB_TOKEN no definidos")
        sys.exit(1)
    owner, repo_name = repo.split("/", 1)
    return owner, repo_name, token


def crear_release(owner: str, repo: str, token: str, tag: str, titulo: str) -> int:
    """Crea un GitHub Release y devuelve su ID."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "tag_name": tag,
        "name": titulo,
        "body": f"Vídeo generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}",
        "draft": False,
        "prerelease": False,
    }
    log(f"Creando GitHub Release con tag '{tag}'...")
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    release = resp.json()
    log(f"✓ Release creado: {release['html_url']}")
    return release["id"], release["upload_url"]


def subir_asset(upload_url: str, token: str, video_path: str) -> str:
    """Sube el video al Release y devuelve la URL de descarga pública."""
    base_url = upload_url.split("{")[0]
    upload_url_final = f"{base_url}?name=video_final.mp4"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "video/mp4",
    }
    log(f"Subiendo {video_path} al Release...")
    with open(video_path, "rb") as f:
        resp = requests.post(upload_url_final, headers=headers, data=f, timeout=300)
    resp.raise_for_status()
    asset = resp.json()
    browser_download_url = asset["browser_download_url"]
    log(f"✓ Video subido: {browser_download_url}")
    return browser_download_url


def verificar_url_descargable(video_url: str, max_intentos: int = 3) -> Tuple[bool, str, str]:
    """
    Verifica que la URL del video es realmente descargable.
    Sigue redirects (302, 301, etc.) y valida Content-Type y Content-Length.

    Retorna: (es_valida, mensaje_diagnostico, url_final_resuelta)
    Implementa reintentos con backoff exponencial en caso de fallos temporales.

    La URL final resuelta es lo que debe enviarse al webhook (no la original con redirect).
    Si no hay redirect, devuelve la URL original como fallback.
    """
    intentos_restantes = max_intentos
    espera_base = 2  # segundos

    while intentos_restantes > 0:
        try:
            log(f"Verificando URL ({max_intentos - intentos_restantes + 1}/{max_intentos})...")
            log(f"  URL original: {video_url}")

            # HEAD request con allow_redirects=True para obtener metadatos sin descargar el archivo
            inicio = time.time()
            resp = requests.head(
                video_url,
                allow_redirects=True,
                timeout=20
            )
            tiempo_respuesta = time.time() - inicio

            # Capturar URL final resuelta (tras seguir redirects)
            url_final = resp.url

            # Loguear cadena de redirects
            if resp.history:
                log(f"  Redirects seguidos:")
                for i, redir in enumerate(resp.history, 1):
                    log(f"    {i}. {redir.status_code} → {redir.url[:70]}...")
                log(f"  URL final (resuelta): {url_final[:70]}...")
            else:
                log(f"  Sin redirects (URL original es final)")

            log(f"  Código HTTP: {resp.status_code}")

            # Validar respuesta
            if resp.status_code != 200:
                log(f"  ✗ Error: esperado 200, recibido {resp.status_code}")
                intentos_restantes -= 1
                if intentos_restantes > 0:
                    espera = espera_base ** (max_intentos - intentos_restantes)
                    log(f"  Reintentando en {espera}s...")
                    time.sleep(espera)
                continue

            # Validar Content-Type
            content_type = resp.headers.get("Content-Type", "").lower()
            if "video/mp4" not in content_type and "application/octet-stream" not in content_type:
                log(f"  ⚠ Warning: Content-Type inesperado: {content_type}")

            # Validar tamaño
            content_length = resp.headers.get("Content-Length", "0")
            try:
                tamaño_bytes = int(content_length)
            except ValueError:
                tamaño_bytes = 0

            if tamaño_bytes == 0:
                log(f"  ✗ Error: Content-Length no disponible o es 0")
                intentos_restantes -= 1
                if intentos_restantes > 0:
                    espera = espera_base ** (max_intentos - intentos_restantes)
                    log(f"  Reintentando en {espera}s...")
                    time.sleep(espera)
                continue

            tamaño_mb = tamaño_bytes / (1024 * 1024)
            log(f"  Content-Length: {tamaño_bytes:,} bytes ({tamaño_mb:.1f} MB)")
            log(f"  Content-Type: {content_type}")
            log(f"  Tiempo respuesta: {tiempo_respuesta:.2f}s")
            log(f"  ✓ URL verificada y descargable")

            return True, f"URL válida: {tamaño_bytes} bytes, {content_type}", url_final

        except requests.exceptions.Timeout:
            log(f"  ✗ Timeout: no hubo respuesta en 20s")
            intentos_restantes -= 1
            if intentos_restantes > 0:
                espera = espera_base ** (max_intentos - intentos_restantes)
                log(f"  Reintentando en {espera}s...")
                time.sleep(espera)

        except requests.exceptions.RequestException as e:
            log(f"  ✗ Error de red: {e}")
            intentos_restantes -= 1
            if intentos_restantes > 0:
                espera = espera_base ** (max_intentos - intentos_restantes)
                log(f"  Reintentando en {espera}s...")
                time.sleep(espera)

    # Si llegamos aquí, todos los intentos fallaron
    log(f"  ✗ FALLÓ: URL no es descargable después de {max_intentos} intentos")
    return False, "URL no verificable después de reintentos", video_url


def llamar_webhook(video_url: str, titulo: str, descripcion: str, tags: list):
    """Llama al webhook de Make.com con los metadatos del video."""
    payload = {
        "video_url": video_url,
        "titulo": titulo,
        "descripcion": descripcion,
        "tags": tags,
    }
    log(f"Llamando webhook Make.com...")
    log(f"  Título: {titulo}")
    log(f"  URL: {video_url}")
    log(f"  Tags: {tags}")
    resp = requests.post(
        MAKE_WEBHOOK_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    log(f"✓ Webhook enviado — Make.com subirá el video a YouTube")
    log(f"  Código respuesta: {resp.status_code}")
    log(f"  Respuesta (primeros 200 chars): {resp.text[:200]}")


def main():
    if len(sys.argv) < 5:
        print("Uso: python subir_video.py <video.mp4> <guion.txt> <titulo.txt> <palabras_clave.txt>")
        sys.exit(1)

    video_path      = sys.argv[1]
    guion_path      = sys.argv[2]
    titulo_path     = sys.argv[3]
    keywords_path   = sys.argv[4]

    if not os.path.exists(video_path):
        log(f"ERROR: no existe {video_path}")
        sys.exit(1)

    titulo         = leer_fichero(titulo_path, fallback="Universo de la Mente — Vídeo nuevo")
    guion          = leer_fichero(guion_path, fallback="")
    palabras_clave = leer_fichero(keywords_path, fallback="narcisismo psicologia")

    resumen = guion[:400].strip() if guion else "Vídeo sobre psicología y narcisismo."
    descripcion = f"{resumen}...\n{CANAL_DESCRIPCION_PIE}"

    tags = [w.strip() for w in palabras_clave.replace(",", " ").split() if w.strip()]
    tags = tags[:15]

    tag = f"video-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    owner, repo, token = obtener_repo_info()

    release_id, upload_url = crear_release(owner, repo, token, tag, titulo)
    video_url = subir_asset(upload_url, token, video_path)

    # Verificar que la URL es descargable antes de llamar a Make.com
    # y capturar la URL final resuelta (tras seguir redirects)
    log("")
    log("=" * 50)
    log("VERIFICACIÓN Y RESOLUCIÓN DE URL")
    log("=" * 50)
    es_valida, diagnostico, url_final = verificar_url_descargable(video_url, max_intentos=3)
    if not es_valida:
        log("ERROR: La URL no es descargable. Abortando...")
        log(diagnostico)
        sys.exit(1)
    log("")

    # Usar la URL final resuelta para el webhook (Make no debe depender de seguir redirects)
    log(f"URL para webhook:")
    log(f"  Original (GitHub Release): {video_url[:80]}...")
    log(f"  Final (directa):           {url_final[:80]}...")
    log("")

    llamar_webhook(url_final, titulo, descripcion, tags)

    log("=" * 50)
    log("✅ PIPELINE COMPLETO")
    log(f"   Título:    {titulo}")
    log(f"   Video URL: {video_url}")
    log(f"   Tags:      {tags}")
    log("   Make.com está subiendo el video a YouTube...")


if __name__ == "__main__":
    main()
