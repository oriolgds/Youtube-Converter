from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_socketio import SocketIO, emit
import yt_dlp
import os
import uuid

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Configuración para WebSockets

# Configuración de carpetas
app.config["TEMPLATES_FOLDER"] = "templates"
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def progress_hook(d):
    """Función de progreso para informar el estado de la descarga."""
    if d['status'] == 'downloading':
        progress = d.get('_percent_str', '0%').strip()
        speed = d.get('_speed_str', '0 KB/s').strip()
        eta = d.get('eta', 0)
        socketio.emit('progress', {
            'progress': progress,
            'speed': speed,
            'eta': eta
        })
    elif d['status'] == 'finished':
        socketio.emit('progress', {'progress': '100%', 'message': 'Descarga completada'})

@app.route('/')
def index():
    """Ruta para servir la página HTML."""
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_video():
    try:
        # Obtener parámetros del formulario
        video_url = request.form.get("url")
        download_type = request.form.get("type", "audio")
        quality = request.form.get("quality", "best")

        if not video_url:
            return jsonify({"error": "La URL del video es requerida"}), 400

        unique_filename = f"{uuid.uuid4()}"
        output_path = os.path.join(DOWNLOAD_FOLDER, unique_filename)

        if download_type == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f"{output_path}.mp3",
                'progress_hooks': [progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        elif download_type == "video":
            ydl_opts = {
                'format': quality,
                'outtmpl': f"{output_path}.mp4",
                'progress_hooks': [progress_hook],
            }
        else:
            return jsonify({"error": "El tipo de descarga debe ser 'audio' o 'video'"}), 400

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        extension = "mp3" if download_type == "audio" else "mp4"
        download_url = f"http://127.0.0.1:5000/downloads/{unique_filename}.{extension}"

        return jsonify({
            "message": "Descarga exitosa",
            "download_url": download_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
