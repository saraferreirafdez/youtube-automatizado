#!/usr/bin/env python3
"""
Generador de voz clonada para Universo de la Mente
Usa Chatterbox Multilingual TTS para clonar la voz de Sara
en español de España (es-ES).

Uso:
  python generar_voz.py <texto|archivo.txt> <output.wav>
  python generar_voz.py guion.txt audio_narrado.wav
"""
import sys
import os
from datetime import datetime


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def leer_texto(texto_arg: str) -> str:
    """Lee el texto del argumento o de un fichero .txt."""
    if texto_arg.endswith(".txt") and os.path.exists(texto_arg):
        with open(texto_arg, "r", encoding="utf-8") as f:
            contenido = f.read()
        log(f"Texto leído desde fichero: {texto_arg} ({len(contenido)} caracteres)")
        return contenido
    log(f"Texto recibido como argumento ({len(texto_arg)} caracteres)")
    return texto_arg


def dividir_en_fragmentos(texto: str, max_chars: int = 250) -> list:
    """
    Divide el texto en fragmentos para TTS.
    Respeta párrafos y limita cada fragmento a max_chars caracteres
    para evitar errores de memoria o de calidad en el modelo.
    """
    parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    fragmentos = []

    for parrafo in parrafos:
        # Si el párrafo es corto, lo usamos directamente
        if len(parrafo) <= max_chars:
            fragmentos.append(parrafo)
            continue

        # Si es largo, lo dividimos por punto + espacio
        oraciones = []
        actual = ""
        for parte in parrafo.replace(". ", ".|").replace("? ", "?|").replace("! ", "!|").split("|"):
            parte = parte.strip()
            if not parte:
                continue
            if len(actual) + len(parte) + 1 <= max_chars:
                actual = (actual + " " + parte).strip()
            else:
                if actual:
                    oraciones.append(actual)
                actual = parte
        if actual:
            oraciones.append(actual)
        fragmentos.extend(oraciones)

    return fragmentos


def main():
    if len(sys.argv) < 3:
        print("Uso: python generar_voz.py <texto|archivo.txt> <output.wav>")
        sys.exit(1)

    texto_arg = sys.argv[1]
    output_path = sys.argv[2]

    # Audio de referencia de la voz de Sara (español de España)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ref_audio = os.path.join(script_dir, "voz_sara_referencia.wav")
    if not os.path.exists(ref_audio):
        log(f"ERROR: no se encuentra el audio de referencia: {ref_audio}")
        sys.exit(1)

    texto = leer_texto(texto_arg)
    if not texto.strip():
        log("ERROR: el texto está vacío")
        sys.exit(1)

    # Cargar dependencias
    log("Cargando librerías (torch, torchaudio, chatterbox)...")
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"Dispositivo de cómputo: {device}")

    log("Cargando modelo Chatterbox Multilingual TTS...")
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)
    log("✓ Modelo cargado")

    # Dividir texto en fragmentos manejables
    fragmentos = dividir_en_fragmentos(texto, max_chars=220)
    log(f"Texto dividido en {len(fragmentos)} fragmentos")

    # Generar audio fragmento a fragmento
    audios = []
    for i, fragmento in enumerate(fragmentos):
        preview = fragmento[:70] + "..." if len(fragmento) > 70 else fragmento
        log(f"  [{i + 1}/{len(fragmentos)}] '{preview}'")

        wav = model.generate(
            fragmento,
            language_id="es",           # Español; la voz de referencia define el acento (es-ES)
            audio_prompt_path=ref_audio, # Voz de Sara → clona timbre y acento español de España
            exaggeration=0.45,           # Expresividad natural (0=plana, 1=exagerada)
            cfg_weight=0.5,              # Balance fluidez / fidelidad al texto
        )
        audios.append(wav)

    log("Montando audio final con silencios naturales entre párrafos...")
    sr = model.sr

    # Índices de fragmentos que corresponden a inicio de párrafo original
    # (usamos silencio largo entre párrafos, corto entre oraciones del mismo párrafo)
    parrafos_originales = set()
    idx = 0
    for p in [p.strip() for p in texto.split("\n") if p.strip()]:
        parrafos_originales.add(idx)
        # Cuántos fragmentos ocupa este párrafo
        n = max(1, (len(p) + 219) // 220)
        idx += n

    silencio_entre_oraciones = torch.zeros(1, int(sr * 0.35))  # 350 ms
    silencio_entre_parrafos = torch.zeros(1, int(sr * 0.70))   # 700 ms

    piezas = []
    for i, audio in enumerate(audios):
        piezas.append(audio)
        if i < len(audios) - 1:
            if (i + 1) in parrafos_originales:
                piezas.append(silencio_entre_parrafos)
            else:
                piezas.append(silencio_entre_oraciones)

    audio_final = torch.cat(piezas, dim=1)
    torchaudio.save(output_path, audio_final, sr)

    duracion = audio_final.shape[1] / sr
    log(f"✓ Audio guardado en: {output_path}")
    log(f"  Duración: {duracion:.1f} s ({duracion / 60:.1f} min)")
    log(f"  Sample rate: {sr} Hz")


if __name__ == "__main__":
    main()
