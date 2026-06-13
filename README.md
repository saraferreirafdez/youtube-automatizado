# YouTube Automatizado — Universo de la Mente

Pipeline automatizado que genera y publica vídeos en YouTube sobre psicología y narcisismo.

## 📹 Pipeline Completo

```
1. generar_guion.py
   ├─ Genera guión en español de España (Claude API o ejemplo predefinido)
   └─ OUTPUT: guion.txt, titulo_video.txt, palabras_clave.txt

2. generar_voz.py
   ├─ Clona voz de Sara usando Chatterbox Multilingual TTS
   └─ OUTPUT: audio_narrado.wav (~5-10 min típicamente)

3. montar_video.py
   ├─ Descarga imágenes de Pexels según tema
   ├─ Monta vídeo 1920x1080 con ffmpeg
   └─ OUTPUT: video_final.mp4 (50-100 MB típicamente)

4. subir_video.py
   ├─ Crea GitHub Release con el vídeo como asset público
   ├─ Verifica que la URL es descargable (sigue 302 redirects)
   ├─ Llama webhook Make.com con metadatos
   └─ Make.com descarga y sube a YouTube automáticamente

GitHub Actions (generar-video.yml)
   └─ Ejecuta todo el pipeline: lunes, miércoles, viernes, sábado a las 22:00 (ES)
```

---

## 🔧 Setup Local

### Requisitos
- Python 3.11+
- ffmpeg (`apt-get install ffmpeg` o similiar)
- Librerías Python: `requests`, `chatterbox-tts`, `torch`, `torchaudio`

### Instalación
```bash
pip install requests chatterbox-tts torch torchaudio
```

### Variables de Entorno (si usas Claude API)
```bash
export ANTHROPIC_API_KEY="sk-..."  # Para generar guiones con Claude
export PEXELS_API_KEY="tu_api_key"  # Para buscar imágenes (no usado en local típicamente)
```

### Ejecutar Manual
```bash
# 1. Generar guión
python generar_guion.py > guion.txt

# 2. Generar voz clonada
python generar_voz.py guion.txt audio_narrado.wav

# 3. Montar vídeo
PALABRAS=$(cat palabras_clave.txt)
python montar_video.py audio_narrado.wav "$PALABRAS" video_final.mp4

# 4. Subir a YouTube (requiere GitHub Release + Make.com)
# En GitHub Actions esto se hace automáticamente
```

---

## 🚀 GitHub Actions

### Requisitos
Crear estos secrets en tu repositorio GitHub (`Settings > Secrets and variables > Actions`):

```
ANTHROPIC_API_KEY    → sk-... (opcional, para Claude API)
PEXELS_API_KEY       → ... (opcional, Pexels API key)
GITHUB_TOKEN         → ${{ secrets.GITHUB_TOKEN }} (automático)
```

### Trigger del Workflow
- **Automático**: Lunes, miércoles, viernes, sábado a las 22:00 (horario España)
- **Manual**: Tab "Actions" → "Generar Video YouTube" → "Run workflow"

---

## 📡 Integración con Make.com

### Problema Resuelto
El pipeline verificaba que el video se subía a GitHub Release, pero **Make.com fallaba** porque:
- La URL del Release hace un **redirect 302** a `objects.githubusercontent.com`
- El módulo HTTP de Make no seguía el redirect automáticamente
- Solo recibía ~5 bytes (la respuesta 302) en lugar del video completo (~50-100 MB)

### Solución Implementada
`subir_video.py` ahora **verifica la descargabilidad de la URL** antes de llamar al webhook:
- Hace HTTP HEAD request con `allow_redirects=True`
- Sigue la cadena de redirects (302 → 200)
- Valida `Content-Type: video/mp4` y `Content-Length > 0`
- Loguea código HTTP, tamaño en bytes, y detalles del redirect
- Reintentas automáticos si falla (máx. 3 intentos)

### Configuración de Make.com (CRÍTICA)

Estos son los pasos exactos para que Make.com descargue y suba el video correctamente:

#### 📋 Requisitos
1. **Módulo 1: Webhook** (ya existe, recibe POST del workflow)
   - URL: `https://hook.eu1.make.com/d4m5v8d05qfrwfq7ergbxi4a2qgqhwjf`
   - Estructura de datos: **debe estar determinada** (mapper los campos)

2. **Módulo 2: HTTP GET** (descargar el vídeo)
   ```
   URL: {{1.video_url}}
   Método: GET
   Timeout: 60 segundos (mínimo)
   
   ⚠️ IMPORTANTE: Activar "Follow Redirects"
      (esto sigue los 302 → 200 del servidor de GitHub)
   
   No añadir headers especiales (requests automático sigue redirects)
   ```

3. **Módulo 3: YouTube Action Upload Video**
   ```
   Title: {{1.titulo}}
   Description: {{1.descripcion}}
   Privacy Status: public
   Tags: {{1.tags}}  (procesar como array, separar con comas)
   
   Video file/content: [cuerpo de respuesta del módulo HTTP]
   ```

#### ⚙️ Configuración Paso a Paso

**Paso 1: Mapper del Webhook (Módulo 1)**
- Abre el módulo 1 (Webhook)
- Haz clic en "Determine data structure" o similar
- Copiar este JSON de ejemplo:
  ```json
  {
    "video_url": "https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4",
    "titulo": "¿Qué siente un narcisista cuando lo ignoras?",
    "descripcion": "[descripción del vídeo]...",
    "tags": ["narcisismo", "psicologia", "relaciones", "toxicas"]
  }
  ```
- Make debería auto-mapear los campos
- Si no, hazlo manualmente: campo por campo

**Paso 2: HTTP GET (Módulo 2)**
- Crear nuevo módulo: Google > HTTP > GET
- URL: {{1.video_url}}
- **Activar "Follow all redirects" o "Follow Redirects"** (checkbox importante)
- Timeout: 60s
- Respuesta: será el video en bytes

**Paso 3: YouTube Upload (Módulo 3)**
- Crear nuevo módulo: Google > YouTube > Upload Video
- Title: {{1.titulo}}
- Description: {{1.descripcion}}
- Privacy Status: public
- Tags: {{1.tags}} (o procesar con texto "narcisismo, psicologia, relaciones, ...")
- Video file: [seleccionar cuerpo del módulo 2 (HTTP GET)]

**Paso 4: Testear**
- Hacer clic en "Run once" o triggear manualmente desde GitHub Actions
- Verificar logs en Make.com
- Expected: Module 2 descarga >1MB, Module 3 sube video a YouTube

---

## 📊 Logs de Diagnóstico

### Salida Esperada en `subir_video.py`

```
[HH:MM:SS] Creando GitHub Release con tag 'video-20260613-120000'...
[HH:MM:SS] ✓ Release creado: https://github.com/saraferreirafdez/youtube-automatizado/releases/tag/video-20260613-120000

[HH:MM:SS] Subiendo audio_narrado.wav al Release...
[HH:MM:SS] ✓ Video subido: https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4

==================================================
VERIFICACIÓN DE DESCARGABILIDAD
==================================================
[HH:MM:SS] Verificando URL (1/3)...
[HH:MM:SS]   URL: https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4
[HH:MM:SS]   Redirects seguidos:
[HH:MM:SS]     1. 302 → https://objects.githubusercontent.com/github-release/...
[HH:MM:SS]   URL final: https://objects.githubusercontent.com/github-release/.../video_final.mp4
[HH:MM:SS]   Código HTTP: 200
[HH:MM:SS]   Content-Length: 52387924 bytes (49.9 MB)
[HH:MM:SS]   Content-Type: video/mp4
[HH:MM:SS]   Tiempo respuesta: 1.23s
[HH:MM:SS]   ✓ URL verificada y descargable

[HH:MM:SS] Llamando webhook Make.com...
[HH:MM:SS]   Título: ¿Qué siente un narcisista cuando lo ignoras?
[HH:MM:SS]   URL: https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4
[HH:MM:SS]   Tags: ['narcisismo', 'psicologia', ...]
[HH:MM:SS] ✓ Webhook enviado — Make.com subirá el video a YouTube
[HH:MM:SS]   Código respuesta: 200
[HH:MM:SS]   Respuesta: OK

==================================================
✅ PIPELINE COMPLETO
[HH:MM:SS]    Título:    ¿Qué siente un narcisista cuando lo ignoras?
[HH:MM:SS]    Video URL: https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4
[HH:MM:SS]    Tags:      ['narcisismo', 'psicologia', 'relaciones', 'toxicas', ...]
[HH:MM:SS]    Make.com está subiendo el video a YouTube...
```

### Si Falla la Verificación

```
[HH:MM:SS] ✗ Timeout: no hubo respuesta en 20s
[HH:MM:SS]   Reintentando en 2s...
[HH:MM:SS] Verificando URL (2/3)...
[HH:MM:SS]   ✗ Error: esperado 200, recibido 404
[HH:MM:SS]   Reintentando en 4s...
[HH:MM:SS] Verificando URL (3/3)...
[HH:MM:SS]   ✓ URL verificada y descargable
```

---

## 🐛 Solución de Problemas

### Error: "BundleValidationError: Validation failed for 7 parameter(s)"
**Causa**: Módulo de YouTube no recibe los parámetros correctamente.

**Soluciones**:
1. Verifica que el webhook en Make tiene la estructura de datos **determinada** (paso 1 arriba)
2. Confirma que los mapeos en el módulo de YouTube están correctos: `{{1.titulo}}`, `{{1.descripcion}}`, etc.
3. Verifica que el módulo HTTP tiene **"Follow Redirects" activado**

### Error: "Content-Length: 0 bytes" en los logs
**Causa**: El asset en GitHub aún no está completamente disponible.

**Solución**: El código incluye reintentos automáticos (máx. 3 intentos, con espera exponencial de 2s, 4s, 8s). Si aún falla:
1. Espera 30 segundos manualmente
2. Retriggereo el workflow desde GitHub Actions

### Make.com ejecuta pero no sube a YouTube
**Causa**: El módulo HTTP está descargando solo 5 bytes.

**Solución**: Confirma que "Follow Redirects" está ACTIVADO en el módulo HTTP de Make.

---

## 📝 Notas de Desarrollador

- **Palabras clave**: Se generan automáticamente según el tema del guión
- **Tags de YouTube**: Se limitan a 15 máximo (por especificación de YouTube)
- **Descripción**: Se genera con los primeros 400 caracteres del guión + pie de canal
- **Imágenes**: Se descargan de Pexels en tiempo de ejecución (requiere API key)
- **Audio**: Se genera con voz clonada de Sara (Chatterbox Multilingual TTS)
- **Duración típica del pipeline**: 30-45 minutos (depende de tamaño de video y velocidad de red)

---

## 📞 Contacto / Soporte

- **Canal**: [Universo de la Mente](https://www.youtube.com/@universodelaamente)
- **Tema**: Psicología, narcisismo, relaciones tóxicas

---

**Last Updated**: 2026-06-13
**Status**: ✅ Pipeline funcional con verificación de descargabilidad
