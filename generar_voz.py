#!/usr/bin/env python3
"""
Generador de voz clonada - Universo de la Mente
Usa Chatterbox Multilingual (open source, licencia MIT, uso comercial OK)
Clona la voz de Sara desde voz_sara_referencia.wav

Uso:
    python generar_voz.py "texto del guion" output.wav
    python generar_voz.py guion.txt output.wav   (si el primer arg es un .txt lo lee)
"""

import sys
import os

def main():
    if len(sys.argv) < 3:
        print("Uso: python generar_voz.py <texto|archivo.txt> <output.wav>")
        sys.exit(1)

    texto_arg = sys.argv[1]
    output_path = sys.argv[2]
    ref_audio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voz_sara_referencia.wav")

    if not os.path.exists(ref_audio):
        print(f"ERROR: no se encuentra el audio de referencia: {ref_audio}")
        sys.exit(1)

    # Lee el texto (de archivo o directo)
    if texto_arg.endswith(".txt") and os.path.exists(texto_arg):
        with open(texto_arg, "r", encoding="utf-8") as f:
            texto = f.read()
    else:
        texto = texto_arg

    print(f"[1/3] Cargando modelo Chatterbox Multilingual...")
    import torch
    import torchaudio
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    print(f"[2/3] Generando audio con la voz clonada (idioma: español)...")

    # Divide el texto en fragmentos por párrafos para textos largos
    parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    if not parrafos:
        parrafos = [texto]

    fragmentos = []
    for i, parrafo in enumerate(parrafos):
        print(f"   Fragmento {i+1}/{len(parrafos)}...")
        wav = model.generate(
            parrafo,
            language_id="es",
            audio_prompt_path=ref_audio,
            exaggeration=0.5,
            cfg_weight=0.5,
        )
        fragmentos.append(wav)

    # Une los fragmentos con pequeñas pausas
    sr = model.sr
    silencio = torch.zeros(1, int(sr * 0.4))
    piezas = []
    for frag in fragmentos:
        piezas.append(frag)
        piezas.append(silencio)
    audio_final = torch.cat(piezas, dim=1)

    print(f"[3/3] Guardando en {output_path}...")
    torchaudio.save(output_path, audio_final, sr)

    dur = audio_final.shape[1] / sr
    print(f"OK - Audio generado: {dur:.1f} segundos ({dur/60:.1f} min)")

if __name__ == "__main__":
    main()
