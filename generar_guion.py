#!/usr/bin/env python3
"""
Generador de guiones para Universo de la Mente
Genera un guión en español de España sobre narcisismo y psicología.

Uso:
  python generar_guion.py [tema] > guion.txt
  python generar_guion.py "triangulación narcisista" > guion.txt

Si la variable de entorno ANTHROPIC_API_KEY está disponible, usa Claude API.
Si no, usa un guión de ejemplo sobre el tema más reciente.
"""
import os
import sys
import requests
from datetime import datetime

# ── Temas rotativos (uno por día de la semana) ─────────────────────────────────
TEMAS = [
    {
        "tema": "¿Qué siente un narcisista cuando lo ignoras?",
        "palabras_clave": "narcisismo psicologia relaciones toxicas manipulacion",
    },
    {
        "tema": "Las 7 frases que usa un narcisista para manipularte",
        "palabras_clave": "narcisismo gaslighting manipulacion psicologia",
    },
    {
        "tema": "Por qué te enganchas a una persona tóxica",
        "palabras_clave": "trauma bond apego toxicidad relaciones",
    },
    {
        "tema": "Cómo detectar el amor bomba desde el principio",
        "palabras_clave": "love bombing narcisismo manipulacion relaciones",
    },
    {
        "tema": "Qué pasa en tu cerebro después de una relación narcisista",
        "palabras_clave": "trauma psicologia cerebro narcisismo recuperacion",
    },
    {
        "tema": "El ciclo de idealización, devaluación y abandono",
        "palabras_clave": "narcisismo ciclo abuso psicologia relaciones toxicas",
    },
    {
        "tema": "Cómo recuperar tu autoestima tras un narcisista",
        "palabras_clave": "autoestima recuperacion narcisismo psicologia sanacion",
    },
]

# ── Guiones de ejemplo ──────────────────────────────────────────────────────────
GUIONES_EJEMPLO = {
    0: """\
¿Qué siente un narcisista cuando lo ignoras?

Hola, soy Sara, y bienvenida a Universo de la Mente. Hoy vamos a hablar de algo que muchas de vosotras habéis vivido en primera persona: el silencio como herramienta de poder frente al narcisista.

Cuando decides ignorar a un narcisista, ocurre algo fascinante en su interior. Su ego, esa estructura tan frágil que han construido durante años, empieza a resquebrajarse. El narcisista necesita atención constante, lo que los psicólogos llamamos suministro narcisista. Sin esa atención, se siente vacío, invisible, como si dejara de existir.

La primera reacción suele ser el pánico. No el pánico que sentimos tú o yo, sino una especie de rabia fría mezclada con desesperación. Es posible que intente llamarte, enviarte mensajes, aparecer donde sabe que vas a estar. Esto se llama hoovering, porque intenta absorberte de nuevo, como una aspiradora.

Si el hoovering no funciona, muchos narcisistas pasan a la fase de la devaluación. Empiezan a hablar mal de ti con los demás, a construir una narrativa en la que tú eres la villana de la historia. Esto es un mecanismo de defensa: si consiguen convencerse a sí mismos de que eres mala persona, pueden explicar por qué los ignoras sin asumir ninguna responsabilidad.

Pero hay algo que el narcisista nunca te dirá: el silencio le duele. Le duele más que cualquier discusión, porque no puede contra algo que no puede controlar. Y para una persona que necesita controlarlo todo, eso es devastador.

Si estás en este proceso, recuerda que el silencio no es venganza, es protección. Es poner una barrera entre tú y alguien que te ha causado daño. Y eso, siempre, es válido.

Suscríbete si quieres seguir aprendiendo sobre psicología y relaciones tóxicas. Hasta la próxima.
""",
    1: """\
Las 7 frases que usa un narcisista para manipularte

Hola, soy Sara, y bienvenida a Universo de la Mente. Hoy vamos a desgranar las siete frases más comunes que usa un narcisista para manipularte, para que cuando las escuches, las reconozcas de inmediato.

La primera es: "Eres demasiado sensible." Esta frase es puro gaslighting. Cuando expresas que algo te ha dolido, el narcisista no valida tu emoción. En vez de eso, convierte tu dolor en un defecto tuyo. Si lo escuchas con frecuencia, empieza a sospechar.

La segunda es: "Nadie más te aguantaría como yo." Esta frase busca aislarte y hacerte creer que no mereces amor. Es una mentira diseñada para que te quedes.

La tercera es: "Yo nunca dije eso." Una de las más duras, porque te hace dudar de tu propia memoria. Se llama amnesia selectiva y es una forma clásica de gaslighting.

La cuarta es: "Todo lo que hago, lo hago por ti." Los narcisistas utilizan el sacrificio como moneda de control. Cada favor tiene un precio, y te lo cobrarán cuando menos te lo esperes.

La quinta es: "Estás loca." O loco, o histérica. Esta frase busca invalidar tu percepción de la realidad por completo y aislarte de las personas que podrían apoyarte.

La sexta es: "Así soy yo, acéptame o déjame." Parece honestidad radical, pero en realidad es negativa a crecer y cambiar. Nadie tiene derecho a hacerte daño y escudarse en su personalidad.

Y la séptima es: "Si me quisieras de verdad, lo harías." La manipulación emocional más directa: convertir el amor en deuda.

Guardar estas frases en tu memoria te puede proteger. El conocimiento es tu mejor escudo. Nos vemos en el siguiente vídeo.
""",
}


def generar_con_claude(tema: str, api_key: str) -> str:
    """Genera un guión usando la API de Claude."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    prompt = f"""Eres la guionista del canal de YouTube 'Universo de la Mente', en español de España.
Escribe un guión de vídeo de 5 a 7 minutos sobre el tema: "{tema}"

El canal está dirigido a mujeres españolas de 25-45 años que han vivido o están en relaciones con narcisistas.

Requisitos del guión:
- Empieza siempre con una pregunta o frase gancho que enganche desde el primer segundo
- Saluda como: "Hola, soy Sara, y bienvenida a Universo de la Mente."
- Usa vocabulario español de España (vosotras, tío/tía, vale, venga, etc.)
- Tono cálido, empático, cercano, como si hablaras con una amiga
- Incluye datos psicológicos reales (menciona términos como gaslighting, hoovering, trauma bond si aplica)
- Termina con una llamada a la acción: suscribirse y comentar
- NO incluyas indicaciones de escena, [pausa], (música), etc. Solo texto para narrar
- Escribe en párrafos cortos (3-5 frases), uno por idea
- Longitud: entre 700 y 900 palabras

Devuelve ÚNICAMENTE el texto del guión, sin explicaciones ni metadatos."""

    payload = {
        "model": "claude-opus-4-8",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"].strip()


def main():
    # Determinar tema
    if len(sys.argv) > 1:
        tema_custom = " ".join(sys.argv[1:])
        tema_info = {"tema": tema_custom, "palabras_clave": "narcisismo psicologia relaciones"}
        tema_idx = None
    else:
        # Rotar por día de la semana
        tema_idx = datetime.now().weekday() % len(TEMAS)
        tema_info = TEMAS[tema_idx]
        tema_custom = None

    tema = tema_info["tema"]
    palabras_clave = tema_info["palabras_clave"]

    print(f"# TEMA: {tema}", file=sys.stderr)
    print(f"# PALABRAS CLAVE: {palabras_clave}", file=sys.stderr)

    # Intentar con Claude API
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        print("# Generando guión con Claude API...", file=sys.stderr)
        try:
            guion = generar_con_claude(tema, api_key)
            print("# ✓ Guión generado con Claude API", file=sys.stderr)
        except Exception as e:
            print(f"# ✗ Error con Claude API: {e}", file=sys.stderr)
            print("# Usando guión de ejemplo...", file=sys.stderr)
            idx = tema_idx if tema_idx is not None else 0
            guion = GUIONES_EJEMPLO.get(idx % len(GUIONES_EJEMPLO), GUIONES_EJEMPLO[0])
    else:
        print("# ANTHROPIC_API_KEY no encontrada, usando guión de ejemplo.", file=sys.stderr)
        idx = tema_idx if tema_idx is not None else 0
        guion = GUIONES_EJEMPLO.get(idx % len(GUIONES_EJEMPLO), GUIONES_EJEMPLO[0])

    # Escribir guión a stdout (para redirigir a fichero)
    print(guion)

    # Escribir palabras clave en un fichero separado para montar_video.py
    with open("palabras_clave.txt", "w", encoding="utf-8") as f:
        f.write(palabras_clave)

    # Escribir título en fichero separado
    with open("titulo_video.txt", "w", encoding="utf-8") as f:
        f.write(tema)

    print(f"# Ficheros auxiliares escritos: palabras_clave.txt, titulo_video.txt", file=sys.stderr)


if __name__ == "__main__":
    main()
