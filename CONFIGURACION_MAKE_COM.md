# Configuración Detallada de Make.com para YouTube Upload

## 🎯 Objetivo
Recibir un webhook de GitHub (con URL del video en el Release), descargarlo, y subirlo a YouTube automáticamente.

## ⚠️ Problema Previo (YA SOLUCIONADO)
- La URL de GitHub Release hacía un redirect 302
- Make.com no seguía el redirect → solo recibía 5 bytes
- El módulo de YouTube fallaba: "BundleValidationError"

**Solución**: `subir_video.py` ahora verifica que la URL es descargable ANTES de llamar al webhook.

---

## 📋 Estructura del Webhook JSON

Este es el JSON que `subir_video.py` envía a Make.com:

```json
{
  "video_url": "https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4",
  "titulo": "¿Qué siente un narcisista cuando lo ignoras?",
  "descripcion": "[guión abreviado]...\n[pie de canal]",
  "tags": [
    "narcisismo",
    "psicologia",
    "relaciones",
    "toxicas",
    "saludmental",
    "autoestima"
  ]
}
```

---

## 🔧 Paso a Paso: Configuración en Make.com

### MÓDULO 1: Webhook Receptor

Este módulo debería estar YA CONFIGURADO. Si necesitas recrearlo:

**Path**: Webhooks → Custom webhook → Create a webhook
**Nombre**: `GitHub Release Webhook`
**URL del webhook**: Nota esta URL (se usa en GitHub Actions)
```
https://hook.eu1.make.com/d4m5v8d05qfrwfq7ergbxi4a2qgqhwjf
```

**Paso Crítico**: Después de crear el webhook:
1. Haz clic en "Determine data structure"
2. En otra ventana, abre GitHub Actions y triggereo manualmente un workflow
3. Cuando Make reciba el POST, debería auto-mapear los campos
4. Si no lo hace, copia-pega este JSON de ejemplo en "Request Body":

```json
{
  "video_url": "https://github.com/saraferreirafdez/youtube-automatizado/releases/download/video-20260613-120000/video_final.mp4",
  "titulo": "¿Qué siente un narcisista cuando lo ignoras?",
  "descripcion": "Los primeros 400 caracteres del guión...\n\n[pie de canal]",
  "tags": ["narcisismo", "psicologia", "relaciones", "toxicas", "saludmental", "autoestima"]
}
```

5. Make debería determinar la estructura automáticamente

**Salida del Módulo 1**:
- `{{1.video_url}}` → URL pública del video en GitHub Release
- `{{1.titulo}}` → Título del video
- `{{1.descripcion}}` → Descripción (guión + pie de canal)
- `{{1.tags}}` → Array de palabras clave

---

### MÓDULO 2: HTTP GET (Descargar Video)

**Tipo de módulo**: HTTP → Make a request

**Configuración Básica**:
```
URL:           {{1.video_url}}
Method:        GET
Timeout:       60 segundos (CRÍTICO: videos son 50-100 MB)
```

**Headers Avanzados** (opcional, pero recomendado):
```
User-Agent: Mozilla/5.0 (compatible; YouTubeAutoUploader)
```

**⚠️ CONFIGURACIÓN CRÍTICA - "Follow Redirects"**:
- En la sección "Advanced settings" o "Show advanced options"
- **Busca**: "Follow Redirects" o "Allow Redirects" (depende de versión de Make)
- **Valor**: ACTIVADO (checkbox marcado)
- **Por qué**: GitHub Release devuelve 302 → objects.githubusercontent.com
  - Sin esto: Make obtiene el HTML de la redirección (5 bytes)
  - Con esto: Make sigue el 302 y obtiene el video real (50-100 MB)

**Salida del Módulo 2**:
- Cuerpo: Los bytes del video (.mp4)
- Headers: `Content-Type: video/mp4`, `Content-Length: 52387924`

---

### MÓDULO 3: YouTube Action - Upload Video

**Tipo de módulo**: YouTube → Upload Video to Channel

**Configuración Requerida**:

| Campo | Valor | Notas |
|-------|-------|-------|
| **Video File / Upload** | [respuesta del módulo 2] | Clic en botón, selecciona "Body" del módulo 2 HTTP |
| **Title** | `{{1.titulo}}` | Máx. 100 caracteres |
| **Description** | `{{1.descripcion}}` | Máx. 5000 caracteres |
| **Privacy Status** | `public` | "public", "unlisted", "private" |
| **Tags** | `{{1.tags}}` | Array de strings, máx. 15 tags |
| **Language** | (opcional) | Español (es) |
| **Category** | (opcional) | Selecciona: "Education" o "People & Blogs" |
| **License** | (opcional) | "standard" |
| **Recording Date** | (opcional) | Hoy o dejalo vacío |
| **Thumbnail** | (opcional) | URL pública de imagen 1280x720px |

**Atención especial con Tags**:
- Si `{{1.tags}}` es un array JSON como `["narcisismo", "psicologia"]`
- Algunos módulos requieren: `join({{1.tags}}, ", ")`
- Prueba las dos formas en Make

**Salida del Módulo 3**:
- Video URL en YouTube
- Video ID
- Estado: "uploaded" o "processed"

---

## 🧪 Testing

### Test 1: Estructura del Webhook
1. Abre el Módulo 1 (Webhook)
2. Haz clic en "Test"
3. Debería mostrar: "Data was saved successfully"
4. Verifica que aparecen los campos: `video_url`, `titulo`, `descripcion`, `tags`

### Test 2: HTTP GET descarga el video
1. Triggereo manual del workflow desde GitHub Actions
2. Espera a que genere el video y cree el Release
3. En Make, ejecuta el scenario
4. Módulo 2 debería mostrar:
   - Status: 200
   - Bytes recibidos: > 1,000,000 (> 1 MB)
   - Content-Type: video/mp4
5. **Si ve "5 bytes"** → El "Follow Redirects" NO está activado

### Test 3: Upload a YouTube
1. Ejecuta el scenario completo
2. Módulo 3 debería devolver un video_id
3. Verifica: [youtube.com/@universodelaamente](https://youtube.com/@universodelaamente)
4. Debería verse el video (puede tardar 5-10 minutos en indexarse)

---

## 🐛 Troubleshooting

### Problema 1: Module 2 devuelve "5 bytes" o "302 error"
**Causa**: "Follow Redirects" no está activado

**Solución**:
1. Abre el Módulo 2 (HTTP GET)
2. Busca "Follow Redirects" o "Allow Redirects"
3. Marca el checkbox
4. Prueba de nuevo

### Problema 2: Module 3 dice "Invalid video file"
**Causa**: El archivo recibido es HTML (302) en lugar de MP4

**Solución**: Igual que Problema 1 (verificar Follow Redirects)

### Problema 3: "Validation failed for 7 parameter(s)"
**Causa**: El webhook no está correctamente mapeado, o los campos están vacíos

**Solución**:
1. Módulo 1: Abre "Determine data structure"
2. Reentra con el JSON de ejemplo (arriba)
3. Verifica que aparecen estos campos:
   - `video_url` (string)
   - `titulo` (string)
   - `descripcion` (string)
   - `tags` (array de strings)

### Problema 4: YouTube dice "Quota exceeded"
**Causa**: Tu cuenta de YouTube tiene límite de uploads

**Solución**:
1. Verifica el estado del acceso en [Google Cloud Console](https://console.cloud.google.com)
2. Aumenta el quota si es posible
3. O contacta con Google YouTube API support

### Problema 5: Video se sube pero sin descripción/tags
**Causa**: Los campos no están mapeados correctamente en Module 3

**Solución**:
1. Módulo 3: Abre "Description"
2. Limpia y vuelve a escribir: `{{1.descripcion}}`
3. Igual con "Title" y "Tags"
4. Prueba de nuevo

---

## 📊 Logs Esperados

### En GitHub Actions (subir_video.py)
```
[HH:MM:SS] Creando GitHub Release con tag 'video-20260613-120000'...
[HH:MM:SS] ✓ Release creado: https://github.com/saraferreirafdez/youtube-automatizado/releases/tag/...

[HH:MM:SS] Subiendo video_final.mp4 al Release...
[HH:MM:SS] ✓ Video subido: https://github.com/saraferreirafdez/youtube-automatizado/releases/download/...

==================================================
VERIFICACIÓN DE DESCARGABILIDAD
==================================================
[HH:MM:SS] Verificando URL (1/3)...
[HH:MM:SS]   Redirects seguidos:
[HH:MM:SS]     1. 302 → https://objects.githubusercontent.com/...
[HH:MM:SS]   URL final: https://objects.githubusercontent.com/.../video_final.mp4
[HH:MM:SS]   Código HTTP: 200
[HH:MM:SS]   Content-Length: 52387924 bytes (49.9 MB)
[HH:MM:SS]   ✓ URL verificada y descargable

[HH:MM:SS] Llamando webhook Make.com...
[HH:MM:SS] ✓ Webhook enviado
```

### En Make.com (ejecución del scenario)
```
Webhook: ✓ Received JSON with 4 fields
HTTP: ✓ Status 200, 52387924 bytes, video/mp4
YouTube: ✓ Video uploaded successfully (ID: dQw4w9WgXcQ)
```

---

## 🎬 Flujo Completo Visual

```
┌─────────────────────────────────────┐
│   GitHub Actions (generar-video.yml) │
│   • Genera guión, voz, video         │
│   • Crea GitHub Release              │
│   • Llama webhook Make.com           │
└──────────────┬──────────────────────┘
               │
               ├─ URL verificada (subir_video.py)
               │  • Sigue 302 → 200
               │  • Valida Content-Length > 0
               │  • Loguea código HTTP
               │
               └─→ POST webhook
                   https://hook.eu1.make.com/...
                   {
                     "video_url": "...",
                     "titulo": "...",
                     "descripcion": "...",
                     "tags": [...]
                   }
                   
┌──────────────────────────────────────┐
│   Make.com Scenario (3 módulos)      │
├──────────────────────────────────────┤
│ Módulo 1: Webhook                    │
│   • Recibe JSON                      │
│   • Mapea campos                     │
│   ├─ {{1.video_url}}                 │
│   ├─ {{1.titulo}}                    │
│   ├─ {{1.descripcion}}               │
│   └─ {{1.tags}}                      │
├──────────────────────────────────────┤
│ Módulo 2: HTTP GET                   │
│   • URL: {{1.video_url}}             │
│   • Follow Redirects: ✓ ACTIVADO     │
│   • Descarga video_final.mp4         │
│   • Retorna cuerpo (bytes del video) │
├──────────────────────────────────────┤
│ Módulo 3: YouTube Upload             │
│   • Title: {{1.titulo}}              │
│   • Description: {{1.descripcion}}   │
│   • Tags: {{1.tags}}                 │
│   • Privacy: public                  │
│   • File: [cuerpo del módulo 2]      │
│   • Sube a YouTube                   │
└────────────────┬─────────────────────┘
                 │
                 └─→ YouTube Channel
                     https://youtube.com/@universodelaamente
                     [Vídeo público, indexado, descargable]
```

---

## ✅ Checklist de Implementación

- [ ] Módulo 1 está configurado y "data structure" está determinada
- [ ] Módulo 2 tiene "Follow Redirects" **ACTIVADO**
- [ ] Módulo 2 timeout es 60 segundos o más
- [ ] Módulo 3 está conectado a una cuenta YouTube autorizada
- [ ] Los campos están mapeados: `{{1.video_url}}`, `{{1.titulo}}`, etc.
- [ ] Test 1: Webhook recibe JSON correctamente
- [ ] Test 2: HTTP GET obtiene > 1 MB (no 5 bytes)
- [ ] Test 3: YouTube recibe el video y lo procesa
- [ ] El video aparece en el canal de YouTube (puede tardar 5-10 min)
- [ ] Los tags y descripción se ven en YouTube

---

**Last Updated**: 2026-06-13
**Status**: ✅ Configuración lista para usar

Si tienes problemas, verifica primero que "Follow Redirects" está activado en Módulo 2. Es el punto crítico.
