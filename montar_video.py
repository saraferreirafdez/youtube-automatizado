#!/usr/bin/env python3
"""
Universo de la Mente - Montaje de vídeo (v2)
- Clips de vídeo en movimiento (Pexels Video) en 1080p
- Subtítulos quemados PALABRA POR PALABRA (transcripción con faster-whisper)
- Música de fondo suave bajo la voz (archivos en ./music, opcional)
- Duración = duración de la narración
Uso: python montar_video.py narracion.mp3 "tema del video" video_final.mp4
"""
import os, sys, math, random, subprocess, tempfile, shutil, requests
from datetime import datetime

PEXELS_API_KEY = "5xDsiCUy8o48AqBu5BOpnUF5KkBaM6AReIRKgGNphlHTLHoVu4Tjbc7y"
AUDIO  = sys.argv[1] if len(sys.argv) > 1 else None
TOPIC  = sys.argv[2] if len(sys.argv) > 2 else "narcisismo psicología"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "video_final.mp4"

W, H, FPS = 1920, 1080, 30
CLIP_SECS = 6           # duración de cada segmento de b-roll
MAX_DOWNLOAD = 18       # nº de clips únicos a descargar (se reutilizan en bucle)
MUSIC_DIR = "music"     # carpeta opcional con mp3 libres de derechos
MUSIC_VOL = 0.12        # volumen de la música respecto a la voz

def log(m): print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log("FFMPEG/CMD FAIL: " + " ".join(str(c) for c in cmd[:8]) + " ...")
        log(r.stderr[-900:])
    return r

def dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())

# ---------------- B-ROLL (Pexels Video) ----------------
GENERIC = ["sad woman alone", "lonely person window rain", "man shadow silhouette dark",
           "couple arguing conflict", "woman crying emotional", "thinking person portrait",
           "dark moody cinematic", "person walking away street", "anxious woman face",
           "broken relationship", "city night lonely", "abstract dark smoke"]
TOPIC_HINTS = {
    "narcis": ["man shadow silhouette dark", "woman crying emotional", "couple arguing conflict",
               "manipulation control", "sad woman alone", "anxious woman face"],
    "psicolog": ["brain mind abstract", "thinking person portrait", "therapy calm", "neurons abstract"],
    "ansied": ["anxious woman face", "stressed person", "panic dark"],
    "abandon": ["person walking away street", "empty room lonely", "sad woman window"],
}

def queries_for(topic):
    t = topic.lower()
    qs = []
    for k, v in TOPIC_HINTS.items():
        if k in t:
            qs += v
    qs += GENERIC
    seen, out = set(), []
    for q in qs:
        if q not in seen:
            seen.add(q); out.append(q)
    return out

def pexels_videos(query, per_page=8):
    h = {"Authorization": PEXELS_API_KEY}
    p = {"query": query, "per_page": per_page, "orientation": "landscape", "size": "medium"}
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers=h, params=p, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log(f"  Pexels error '{query}': {e}"); return []
    links = []
    for v in r.json().get("videos", []):
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        if not files: continue
        files.sort(key=lambda f: abs((f["width"] or 0) - 1920))
        links.append(files[0]["link"])
    return links

def gather_clips(topic, carpeta, needed_unique):
    urls = []
    for q in queries_for(topic):
        if len(urls) >= needed_unique: break
        for u in pexels_videos(q, 6):
            if u not in urls:
                urls.append(u)
            if len(urls) >= needed_unique: break
    log(f"Clips encontrados: {len(urls)}")
    rutas = []
    for i, u in enumerate(urls):
        raw = os.path.join(carpeta, f"raw_{i:02d}.mp4")
        try:
            with requests.get(u, timeout=90, stream=True) as r:
                r.raise_for_status()
                with open(raw, "wb") as f:
                    for ch in r.iter_content(1 << 16): f.write(ch)
            norm = os.path.join(carpeta, f"clip_{i:02d}.mp4")
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
            res = run(["ffmpeg","-y","-t",str(CLIP_SECS),"-i",raw,"-an","-vf",vf,
                       "-c:v","libx264","-preset","veryfast","-crf","23", norm])
            if res.returncode == 0 and os.path.exists(norm):
                rutas.append(norm)
                log(f"  Clip {len(rutas)} normalizado")
            os.remove(raw)
        except Exception as e:
            log(f"  Error clip {i}: {e}")
    return rutas

# ---------------- SUBTÍTULOS palabra por palabra (ASS) ----------------
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,DejaVu Sans,130,&H00FFFFFF,&H000000FF,&H00101010,&H64000000,-1,0,0,0,100,100,0,0,1,7,4,2,100,100,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def ts(t):
    if t < 0: t = 0
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    cs = int(round((s - int(s)) * 100))
    return f"{h:d}:{m:02d}:{int(s):02d}.{cs:02d}"

def make_ass(audio, ass_path):
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        log(f"faster-whisper no disponible ({e}); el vídeo se hará SIN subtítulos.")
        return 0
    log("Transcribiendo audio con Whisper (palabra por palabra)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio, language="es", word_timestamps=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            t = (w.word or "").strip()
            if t:
                words.append((w.start, w.end, t))
    if not words:
        log("Whisper no devolvió palabras; sin subtítulos."); return 0
    lines = []
    for i, (st, en, t) in enumerate(words):
        end = words[i+1][0] if i+1 < len(words) else en + 0.3
        end = max(end, st + 0.12)
        txt = t.upper().replace("{","(").replace("}",")").replace("\\","")
        lines.append(f"Dialogue: 0,{ts(st)},{ts(end)},Word,,0,0,0,,{txt}")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER + "\n".join(lines) + "\n")
    log(f"Subtítulos generados: {len(words)} palabras")
    return len(words)

# ---------------- MONTAJE FINAL ----------------
def find_music():
    if not os.path.isdir(MUSIC_DIR): return None
    tracks = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR)
              if f.lower().endswith((".mp3", ".m4a", ".wav"))]
    return random.choice(tracks) if tracks else None

def build(audio, clips, ass_path, output):
    duracion = dur(audio)
    log(f"Duración narración: {duracion:.1f}s ({duracion/60:.1f} min)")
    if not clips:
        log("ERROR: no hay clips de vídeo."); sys.exit(1)

    # construir lista de segmentos hasta cubrir la duración (reutiliza y baraja)
    n_seg = max(1, math.ceil(duracion / CLIP_SECS) + 1)
    pool = clips[:]
    random.shuffle(pool)
    seq = [pool[i % len(pool)] for i in range(n_seg)]

    tmp = tempfile.mkdtemp()
    list_path = os.path.join(tmp, "list.txt")
    with open(list_path, "w") as f:
        for c in seq:
            f.write(f"file '{os.path.abspath(c)}'\n")
    concat = os.path.join(tmp, "concat.mp4")
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",list_path,"-c","copy", concat])

    music = find_music()
    has_subs = ass_path and os.path.exists(ass_path)
    vchain = []
    if has_subs:
        vchain.append(f"ass={os.path.abspath(ass_path)}")
    vchain.append("fade=t=in:st=0:d=0.6")
    vchain.append(f"fade=t=out:st={max(0,duracion-0.8):.2f}:d=0.8")
    vfilter = "[0:v]" + ",".join(vchain) + "[v]"

    cmd = ["ffmpeg","-y","-i",concat]
    if music:
        log(f"Música de fondo: {os.path.basename(music)}")
        cmd += ["-stream_loop","-1","-i",music,"-i",audio]
        afilter = f"[1:a]volume={MUSIC_VOL}[m];[2:a]volume=1.0[n];[n][m]amix=inputs=2:duration=first:dropout_transition=2[a]"
        filt = vfilter + ";" + afilter
        amap = "[a]"
    else:
        log("Sin música (añade mp3 libres de derechos a la carpeta 'music').")
        cmd += ["-i",audio]
        filt = vfilter
        amap = "2:a" if False else "1:a"
    cmd += ["-filter_complex", filt, "-map","[v]", "-map", amap,
            "-t", f"{duracion:.2f}", "-c:v","libx264","-preset","veryfast","-crf","21",
            "-c:a","aac","-b:a","192k","-pix_fmt","yuv420p","-movflags","+faststart", output]
    res = run(cmd)
    shutil.rmtree(tmp, ignore_errors=True)
    if res.returncode != 0 or not os.path.exists(output):
        log("ERROR en el montaje final."); sys.exit(1)
    log(f"Vídeo final: {output} ({os.path.getsize(output)/1e6:.1f} MB, {dur(output)/60:.1f} min)")

def main():
    if not AUDIO or not os.path.exists(AUDIO):
        log("Falta el audio. Uso: python montar_video.py narracion.mp3 'tema' salida.mp4"); sys.exit(1)
    duracion = dur(AUDIO)
    needed_unique = min(MAX_DOWNLOAD, max(8, math.ceil(duracion / CLIP_SECS)))
    tmp = tempfile.mkdtemp()
    try:
        clips = gather_clips(TOPIC, tmp, needed_unique)
        ass_path = os.path.join(tmp, "subs.ass")
        make_ass(AUDIO, ass_path)
        build(AUDIO, clips, ass_path, OUTPUT)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
