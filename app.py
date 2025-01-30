from flask import Flask, request, jsonify, send_from_directory, render_template
import os
import json
import uuid
from yt_dlp import YoutubeDL
import threading

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
STATUS_FILE = "conversion_status.json"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_status(status):
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=4)


def update_progress(task_id, status, progress, download_url=None):
    statuses = load_status()
    statuses[task_id] = {"status": status, "progress": progress, "download_url": download_url}
    save_status(statuses)


def handle_progress(task_id, d):
    if d["status"] == "downloading":
        progress = d.get("_percent_str", "0%")
        update_progress(task_id, "converting", progress)


import shutil  # Importar shutil para mover archivos


def download_and_convert(url, download_type, quality, task_id):
    try:
        update_progress(task_id, "pending", "0%")
        output_file = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.%(ext)s")

        ydl_opts = {
            "outtmpl": output_file,
            "progress_hooks": [lambda d: handle_progress(task_id, d)],
            "keepvideo": True  # Evita que yt-dlp elimine los archivos originales
        }

        if download_type == "audio":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }]
            })
            final_ext = "mp3"
        elif download_type == "video":
            ydl_opts[
                "format"] = f"bestvideo[height<={quality}]+bestaudio/best" if quality != "best" else "bestvideo+bestaudio/best"
            final_ext = "mp4"

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Buscar el archivo descargado
        downloaded_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(task_id)]
        if downloaded_files:
            for file in downloaded_files:
                if file.endswith(final_ext):  # Verifica si ya es el formato final
                    final_filename = file
                    break
            else:
                # Si no se encontró, intenta renombrarlo
                for file in downloaded_files:
                    if file.endswith(".webm") or file.endswith(".m4a") or file.endswith(".mp4"):
                        final_filename = f"{task_id}.{final_ext}"
                        shutil.move(os.path.join(DOWNLOAD_FOLDER, file), os.path.join(DOWNLOAD_FOLDER, final_filename))
                        break
        else:
            raise Exception("No se encontró el archivo convertido")

        update_progress(task_id, "finished", "100%", f"/download/{final_filename}")

    except Exception as e:
        update_progress(task_id, "error", str(e))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    url = request.form.get("url")
    download_type = request.form.get("download_type")
    quality = request.form.get("quality", "best")

    if not url or not download_type:
        return jsonify({"error": "Missing parameters"}), 400

    task_id = str(uuid.uuid4())
    threading.Thread(target=download_and_convert, args=(url, download_type, quality, task_id)).start()

    return jsonify({"task_id": task_id})


@app.route("/status/<task_id>", methods=["GET"])
def get_status(task_id):
    statuses = load_status()
    return jsonify(statuses.get(task_id, {"error": "Task not found"}))


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)
