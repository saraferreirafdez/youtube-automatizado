#!/usr/bin/env python3
"""
YouTube Automatizado - Universo de la Mente
Monta un vídeo automáticamente con:
- Audio MP3 de Google Drive (generado por ElevenLabs)
- Imágenes de Pexels relacionadas con el tema
- ffmpeg para montar el vídeo final
- Guarda el resultado en Google Drive
"""
import os
import sys
import json
import time
import requests
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# ============================================================
# CONFIGURACIÓN — rellena estos valores
# ============================================================
PEXELS_API_KEY = "5xDsiCUy8o48AqBu5BOpnUF5KkBaM6AReIRKgGNphlHTLHoVu4Tjbc7y"  # gratis en pexels.com/api
AUDIO_FILE_PATH = sys.argv[1] if len(sys.argv) > 1 else None  # ruta al MP3
VIDEO_TOPIC = sys.argv[2] if len(sys.argv) > 2 else "narcisismo psicología"
OUTPUT_PATH = sys.argv[3] if len(sys.argv) > 3 else "output_video.mp4"
# ============================================================

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_audio_duration(audio_path):
    """Obtiene la duración del audio en segundos con ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def buscar_imagenes_pexels(query, num_imagenes=20):
    """Busca imágenes en Pexels relacionadas con el tema."""
    log(f"Buscando {num_imagenes} imágenes para: {query}")

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": num_imagenes,
        "orientation": "landscape",
        "size": "large"
    }

    r = requests.get("https://api.pexels.com/v1/search", headers=headers, params=params)
    r.raise_for_status()

    fotos = r.json().get("photos", [])
    urls = [f["src"]["large"] for f in fotos]
    log(f" → {len(urls)} imágenes encontradas")
    return urls

def descargar_imagenes(urls, carpeta):
    """Descarga las imágenes a una carpeta temporal."""
    rutas = []
    for i, url in enumerate(urls):
        ruta = os.path.join(carpeta, f"img_{i:03d}.jpg")
        r = requests.get(url, timeout=15)
        with open(ruta, "wb") as f:
            f.write(r.content)
        rutas.append(ruta)
        log(f"  Descargada imagen {i+1}/{len(urls)}")
    return rutas

def crear_video_con_imagenes(rutas_imagenes, audio_path, output_path, duracion_total):
    """Monta el vídeo final con ffmpeg."""
    log("Montando vídeo con ffmpeg...")

    # Calcula cuánto tiempo mostrar cada imagen
    num_imgs = len(rutas_imagenes)
    tiempo_por_imagen = duracion_total / num_imgs

    # Crea el archivo de lista de imágenes para ffmpeg
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        lista_path = f.name
        for ruta in rutas_imagenes:
            f.write(f"file '{ruta}'\n")
            f.write(f"duration {tiempo_por_imagen:.2f}\n")
        # Repite la última imagen para evitar problemas de corte
        f.write(f"file '{rutas_imagenes[-1]}'\n")

    # Comando ffmpeg: combina imágenes + audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", lista_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log(f"Error ffmpeg: {result.stderr[-500:]}")
        # Intenta versión más simple sin zoom
        cmd_simple = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", lista_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_simple, check=True)

    os.unlink(lista_path)
    log(f"Video generado: {output_path}")

def main():
    if not AUDIO_FILE_PATH or not os.path.exists(AUDIO_FILE_PATH):
        log("Error: necesitas pasar la ruta al archivo de audio como primer argumento")
        log("   Uso: python montar_video.py audio.mp3 'narcisismo psicologia' output.mp4")
        sys.exit(1)

    if PEXELS_API_KEY == "TU_PEXELS_API_KEY":
        log("Error: configura tu PEXELS_API_KEY en el script")
        sys.exit(1)

    log(f"Iniciando montaje de video")
    log(f"   Audio: {AUDIO_FILE_PATH}")
    log(f"   Tema: {VIDEO_TOPIC}")
    log(f"   Output: {OUTPUT_PATH}")

    # 1. Obtener duración del audio
    duracion = get_audio_duration(AUDIO_FILE_PATH)
    log(f"   Duracion del audio: {duracion:.1f} segundos ({duracion/60:.1f} minutos)")

    # 2. Calcular cuántas imágenes necesitamos (1 imagen cada 25 segundos aprox)
    num_imagenes = max(10, int(duracion / 25))

    # 3. Buscar imágenes en Pexels
    queries = {
        "narcisismo": "psychology mind manipulation emotions",
        "narcisista": "toxic relationship manipulation control",
        "psicologia": "psychology mind brain therapy",
        "suenos": "dreams sleep night surreal",
        "default": "psychology emotions mind mental health"
    }

    query_ingles = "psychology mind manipulation emotions"
    for key, val in queries.items():
        if key.lower() in VIDEO_TOPIC.lower():
            query_ingles = val
            break

    # Crea carpeta temporal
    temp_dir = tempfile.mkdtemp()

    try:
        # 4. Descargar imágenes
        urls = buscar_imagenes_pexels(query_ingles, num_imagenes)
        if not urls:
            log("No se encontraron imagenes, usando busqueda generica")
            urls = buscar_imagenes_pexels("psychology emotions", num_imagenes)

        rutas = descargar_imagenes(urls, temp_dir)

        # 5. Montar vídeo
        crear_video_con_imagenes(rutas, AUDIO_FILE_PATH, OUTPUT_PATH, duracion)

        # 6. Verificar resultado
        if os.path.exists(OUTPUT_PATH):
            size_mb = os.path.getsize(OUTPUT_PATH) / (1024*1024)
            log(f"Video listo! Tamano: {size_mb:.1f} MB")
            log(f"   Ruta: {OUTPUT_PATH}")
        else:
            log("Error: no se genero el video")
            sys.exit(1)

    finally:
        # Limpia archivos temporales
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
