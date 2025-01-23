import os
import json
import uuid
from flask import Flask, request, jsonify, render_template
from yt_dlp import YoutubeDL


app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
PROGRESS_FILE = "progress.json"

# Asegúrate de que la carpeta de descargas exista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Cargar el progreso desde el archivo JSON
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}

# Guardar el progreso en el archivo JSON
def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=4)

# Actualizar el progreso de una tarea
def update_progress(task_id, status, progress, download_url=None):
    progress_data = load_progress()
    progress_data[task_id] = {
        "status": status,
        "progress": progress,
        "download_url": download_url
    }
    save_progress(progress_data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download/<task_id>', methods=['GET'])
def download(task_id):
    progress_data = load_progress()
    if task_id in progress_data:
        download_url = progress_data[task_id].get("download_url")
        if download_url:
            return jsonify({"download_url": download_url})
    return jsonify({"error": "Task not found or not finished yet."}), 404

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get("url")
    download_type = request.form.get("download_type")
    quality = request.form.get("quality", "best")

    if not url or not download_type:
        return jsonify({"error": "URL and download type are required."}), 400

    task_id = str(uuid.uuid4())
    update_progress(task_id, "pending", "0%")

    # Configurar opciones de descarga
    options = {
        "outtmpl": os.path.join(DOWNLOAD_FOLDER, f"{task_id}.%(ext)s"),
        "progress_hooks": [lambda d: handle_progress(task_id, d)],
    }

    if download_type == "audio":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif download_type == "video":
        if quality == "best":
            options["format"] = "bestvideo+bestaudio/best"
        else:
            options["format"] = f"bestvideo[height<={quality}]+bestaudio/best"

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([url])

        # Archivo combinado listo
        download_url = f"/download/{task_id}.mp4"
        update_progress(task_id, "finished", "100%", download_url)

    except Exception as e:
        update_progress(task_id, "error", str(e))

    return jsonify({"task_id": task_id})

def handle_progress(task_id, data):
    if data["status"] == "downloading":
        percent = float(data["downloaded_bytes"]) / float(data["total_bytes"]) * 100
        update_progress(task_id, "converting", f"{int(percent)}%")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
