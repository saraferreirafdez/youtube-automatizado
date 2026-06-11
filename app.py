from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/generar-video', methods=['POST'])
def generar_video():
    data = request.json
    audio_url = data.get('audio_url')
    tema = data.get('tema', 'narcisismo psicologia')

    # Descarga el audio
    import requests as req
    r = req.get(audio_url)
    audio_path = '/tmp/audio.mp3'
    with open(audio_path, 'wb') as f:
        f.write(r.content)

    output_path = '/tmp/output.mp4'

    # Ejecuta el script
    result = subprocess.run([
        'python', 'montar_video.py',
        audio_path, tema, output_path
    ], capture_output=True, text=True)

    if result.returncode == 0:
        return jsonify({'status': 'ok', 'video_path': output_path})
    else:
        return jsonify({'status': 'error', 'log': result.stderr}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
