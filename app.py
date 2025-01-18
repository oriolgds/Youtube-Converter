from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os
import uuid

app = Flask(__name__)

# Carpeta para almacenar los archivos descargados
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


@app.route('/convert', methods=['GET'])
def convert_video():
    try:
        # Obtener la URL del video desde los parámetros
        video_url = request.args.get("url")

        if not video_url:
            return jsonify({"error": "La URL del video es requerida"}), 400

        # Descargar el audio usando yt-dlp
        unique_filename = f"{uuid.uuid4()}.mp3"
        output_path = os.path.join(DOWNLOAD_FOLDER, unique_filename)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Devolver la URL de descarga
        download_url = f"http://127.0.0.1:5000/downloads/{unique_filename}"
        return jsonify({
            "message": "Conversión exitosa",
            "download_url": download_url
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    """Proporciona acceso a los archivos descargados."""
    return send_from_directory(DOWNLOAD_FOLDER, filename)


@app.route('/')
def home():
    return jsonify(
        {"message": "Bienvenido a la API de YouTube Converter. Usa el endpoint /convert con un parámetro 'url'."})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
