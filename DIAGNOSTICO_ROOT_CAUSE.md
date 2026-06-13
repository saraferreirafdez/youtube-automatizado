# Diagnóstico de Causa Raíz: Vídeo NO se sube a YouTube

## 📋 MAPEO COMPLETO DEL PIPELINE

### 1. **Flujo de Datos**
```
generar_guion.py (CLI)
  ├─ INPUT:  tema (rotativo por día de semana o custom)
  ├─ OUTPUT: guion.txt + titulo_video.txt + palabras_clave.txt
  └─ USO: Claude API (si ANTHROPIC_API_KEY está disponible)

generar_voz.py (Chatterbox Multilingual TTS)
  ├─ INPUT:  guion.txt + voz_sara_referencia.wav
  ├─ OUTPUT: audio_narrado.wav (duración variable, ~5-10 min típico)
  └─ PROCESO: clona voz en español de España (es-ES)

montar_video.py (ffmpeg + Pexels API)
  ├─ INPUT:  audio_narrado.wav + VIDEO_TOPIC (palabras_clave.txt)
  ├─ PROCESO:
  │  ├─ Obtiene duración del audio
  │  ├─ Calcula número de imágenes necesarias (1 cada 25 seg)
  │  ├─ Busca imágenes en Pexels según tema
  │  ├─ Descarga imágenes (.jpg)
  │  └─ Monta vídeo 1920x1080 con ffmpeg
  └─ OUTPUT: video_final.mp4 (típicamente 50-100 MB)

subir_video.py (GitHub Release + Make.com Webhook)
  ├─ INPUT:  video_final.mp4 + guion.txt + titulo_video.txt + palabras_clave.txt
  ├─ PROCESO:
  │  ├─ 1. Crea GitHub Release con tag "video-YYYYMMDD-HHMMSS"
  │  ├─ 2. Sube video_final.mp4 como asset del Release
  │  ├─ 3. Obtiene browser_download_url del asset → URL pública (302 redirect)
  │  ├─ 4. Construye payload JSON
  │  └─ 5. Llama webhook Make.com
  └─ OUTPUT: Release GitHub + JSON POST al webhook

Make.com (módulos 1-3)
  ├─ Módulo 1: Webhook recibe JSON
  ├─ Módulo 2: HTTP GET descarga video desde {{1.video_url}}
  ├─ Módulo 3: YouTube ActionUploadVideo sube video (privacy public)
  └─ ⚠️ ERROR ACTUAL: "BundleValidationError: Validation failed for 7 parameter(s)"
                      Solo ~5 bytes transferidos (~0.3 s)
```

---

## 🔍 ANÁLISIS DEL PROBLEMA

### Síntomas Observados
- ✅ GitHub Release se crea correctamente
- ✅ Video se sube como asset al Release
- ✅ Workflow de GitHub Actions termina en VERDE
- ❌ Make.com falla: "BundleValidationError"
- ❌ Transferencia: ~5 bytes en ~0.3 s (esperable: 50-100 MB en 10-30 s)
- ❌ El módulo HTTP NO está descargando el vídeo

### Causa Raíz Identificada (con evidencia)

#### **PROBLEMA 1: URL de GitHub Release hace 302 Redirect**

La URL que retorna GitHub (`browser_download_url`) es:
```
https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4
```

Esta URL **redirige a** (302 Found):
```
https://objects.githubusercontent.com/github-release/...uuid.../video_final.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&...
```

**El módulo HTTP de Make.com SOLO TRANSFIERE 5 BYTES porque:**
- La respuesta 302 es pequeña (~150-300 bytes)
- Si el módulo HTTP no sigue el redirect automáticamente, recibe SOLO la respuesta 302
- El módulo de YouTube espera un archivo .mp4 válido, no un HTML 302

#### **PROBLEMA 2: Falta Verificación Antes del Webhook**

`subir_video.py` NO verifica que la URL sea realmente descargable:
```python
# Líneas 84-100: subir_video.py
browser_download_url = asset["browser_download_url"]
log(f"✓ Video subido: {browser_download_url}")
return browser_download_url  # ← devuelve sin verificar

# Líneas 103-122: llamar_webhook()
payload = {
    "video_url": video_url,  # ← URL sin verificar
    "titulo": titulo,
    ...
}
resp = requests.post(MAKE_WEBHOOK_URL, ..., json=payload)
```

**Falta:**
- No sigue el 302 redirect para verificar que descarga correctamente
- No valida el tamaño descargado
- No espera a que el asset esté completamente disponible (condición de carrera potencial)
- No loguea el código HTTP de estado

#### **PROBLEMA 3: Estructura de Webhook en Make.com**

Basado en el error "Validation failed for 7 parameter(s)":
- El módulo de YouTube en Make espera estos campos:
  ```
  {{1.video_url}}    (¿campo vacío?)
  {{1.titulo}}       (¿campo vacío?)
  {{1.descripcion}}  (¿campo vacío?)
  {{1.tags}}         (¿array malformado?)
  ... otros campos
  ```

Si los campos del webhook no están "determinados" (Make requiere mapear explícitamente), los valores llegan vacíos.

---

## 📊 CONTRATO ENTRE subir_video.py y Make.com

### Payload JSON Enviado por `subir_video.py`
```json
{
  "video_url": "https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-YYYYMMDD-HHMMSS/video_final.mp4",
  "titulo": "¿Qué siente un narcisista cuando lo ignoras?",
  "descripcion": "[primeros 400 caracteres del guión]...\n[pie de canal]",
  "tags": ["narcisismo", "psicologia", "relaciones", "toxicas", ...]
}
```

### Contrato Esperado por Make.com (Módulo YouTube)
- **video_url**: STRING, URL pública descargable (con seguimiento de redirects)
- **titulo**: STRING, ≤100 caracteres
- **descripcion**: STRING, ≤5000 caracteres
- **tags**: ARRAY of STRING, 15 máximo, sin espacios

**Observación:** El código en `subir_video.py` construye correctamente el payload, PERO la URL NO ES VERIFICABLE antes de enviarla.

---

## ✅ SOLUCIÓN PROPUESTA

### Opción Elegida: Verificación + Diagnóstico (Opción A + C)

**Cambios en `subir_video.py`:**

1. **Después de obtener `browser_download_url`, verificar que es descargable:**
   ```python
   # HTTP HEAD con allow_redirects=True
   # Validar: código 200, Content-Length > 0, Content-Type: video/mp4
   # Loguear: código HTTP, tamaño en bytes, tiempo de descarga
   ```

2. **Si la verificación falla:**
   ```python
   # Reintentar con backoff (esperar 5s, 10s, 15s)
   # Máximo 3 intentos
   # Si falla después de 3 intentos, loguear error y fallar el workflow
   ```

3. **Añadir logging detallado:**
   ```python
   # Imprimir:
   # - Código HTTP de respuesta
   # - Content-Length recibido (en bytes)
   # - Content-Type de la respuesta
   # - Tiempo de respuesta
   # - Indica claramente si se siguió redirect (302 → 200)
   ```

4. **Documentar en README.md:**
   ```markdown
   ## Configuración de Make.com
   
   ### Módulo 2: HTTP GET
   - URL: {{1.video_url}}
   - Método: GET
   - **IMPORTANTE: Activar "Follow Redirects" (302, 301, etc.)**
   - Timeout: 60 segundos (videos pueden ser grandes)
   
   ### Módulo 3: YouTube Action Upload
   - Mapear:
     - video_file ← body (del HTTP GET)
     - title ← {{1.titulo}}
     - description ← {{1.descripcion}}
     - tags ← {{1.tags}} (procesar como array, separar por comas)
     - privacyStatus ← "public"
   ```

---

## 📝 IMPLEMENTACIÓN

### Cambios a `subir_video.py`:

1. **Nueva función: `verificar_url_descargable()`**
   - HTTP HEAD request con follow_redirects
   - Valida Content-Type y Content-Length
   - Loguea código HTTP, tamaño, redirect chain
   - Retorna (código_http, tamaño_bytes, ok: bool)

2. **En `main()`, después de `subir_asset()`:**
   ```python
   video_url = subir_asset(upload_url, token, video_path)
   # ← NUEVO
   verificar_url_y_reintentar(video_url, max_intentos=3)
   # ← fin NUEVO
   llamar_webhook(video_url, titulo, descripcion, tags)
   ```

3. **Salida esperada del log:**
   ```
   [HH:MM:SS] ✓ Video subido: https://github.com/...
   [HH:MM:SS] Verificando descargabilidad de la URL...
   [HH:MM:SS]   HEAD https://github.com/.../releases/download/...
   [HH:MM:SS]   → 302 Found (redirect a objects.githubusercontent.com)
   [HH:MM:SS]   → 200 OK (final después de seguir redirect)
   [HH:MM:SS]   → Content-Length: 52387924 bytes (49.9 MB)
   [HH:MM:SS]   → Content-Type: video/mp4
   [HH:MM:SS]   ✓ URL verificada y descargable
   [HH:MM:SS] Llamando webhook Make.com...
   ```

---

## 🎯 CHECKLIST FINAL

- [ ] Implementar `verificar_url_descargable()` en `subir_video.py`
- [ ] Añadir reintentos con backoff exponencial
- [ ] Loguear código HTTP, Content-Length, Content-Type
- [ ] Documentar en README.md: pasos para configurar Make.com
  - [ ] Módulo HTTP: activar "Follow Redirects"
  - [ ] Módulo YouTube: mapear campos correctamente
  - [ ] Timeout: 60 segundos mínimo
- [ ] Testear con workflow manual: verificar logs
- [ ] Verificar que Make.com recibe JSON válido
- [ ] Confirmar que YouTube Action upload funciona

---

**Causa Raíz Confirmada:** URL del Release hace 302 redirect no seguido por Make.com + falta de verificación previa en `subir_video.py`.
