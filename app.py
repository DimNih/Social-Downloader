from flask import *
import os
import shutil
from datetime import datetime
import yt_dlp
import re
import ffmpeg
import time



app = Flask(__name__)

# Ensure the 'audios', 'videos', 'tiktok_videos', 'audio tiktok' and 'history.txt'
if not os.path.exists('audios'):
    os.mkdir('audios')
if not os.path.exists('videos'):
    os.mkdir('videos')
if not os.path.exists('tiktok_videos'):
    os.mkdir('tiktok_videos')

def sanitize_filename(filename):
    """Remove invalid characters from filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def download_audio(link):
    if len(os.listdir('audios')) > 5:
        shutil.rmtree('audios')
        os.mkdir('audios')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'audios/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            file_name = f"audios/{title}.mp3"

        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        raise Exception(f"Error downloading audio: {str(e)}")
def download_video(link):
    # Check if directory exceeds 2 video files and clean up
    video_files = [f for f in os.listdir('videos') if f.endswith('.mp4')]
    if len(video_files) > 2:
        shutil.rmtree('videos')
        os.mkdir('videos')

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'videos/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    try:
        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            
            # Look for the downloaded video file in the folder
            video_file = next(
                (f for f in os.listdir('videos') if f.startswith(title) and f.endswith('.mp4')), 
                None
            )
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")

            # Construct the full file path
            file_name = os.path.join('videos', video_file)

        # Log the download history
        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        # Log the exception for further debugging
        with open("error_log.txt", "a") as log:
            log.write(f"Error: {str(e)}\n")
        raise Exception(f"Error downloading video: {str(e)}")


def download_tiktok_video(link):
    if os.path.exists('tiktok_videos'):
        if len(os.listdir('tiktok_videos')) > 2:  
            shutil.rmtree('tiktok_videos')  
    else:
        os.mkdir('tiktok_videos')  

    ydl_opts = {
        'format': 'best',  
        'outtmpl': 'tiktok_videos/%(title)s.%(ext)s',  
        'merge_output_format': 'mp4', 
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',  
            'preferedformat': 'mp4',  
        }],
        'nocheckcertificate': True,  
    }


    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            video_file = next(
                (f for f in os.listdir('tiktok_videos') if f.startswith(title) and f.endswith('.mp4')),
                None
            )
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")
            file_name = f"tiktok_videos/{video_file}"

        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        raise Exception(f"Error downloading TikTok video: {str(e)}")

def convert_mp4_to_mp3(mp4_path):
    timestamp = int(time.time())  
    base_name = os.path.basename(mp4_path)
    mp3_filename = f"{base_name.replace('.mp4', '')}_{timestamp}.mp3"
    mp3_path = os.path.join(os.path.dirname(mp4_path), mp3_filename)

    try:
        ffmpeg.input(mp4_path).output(mp3_path, format='mp3').run()
        return mp3_path
    except Exception as e:
        raise Exception(f"Error converting MP4 to MP3: {str(e)}")


@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/submit_audio', methods=['POST'])
def submit_audio():
    data = request.form.get('link')
    if not data:
        return "Error: No URL provided", 400

    try:
        file_path = download_audio(data)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading audio: {str(e)}", 500

@app.route('/submit_tiktok_mp4_to_mp3', methods=['POST'])
def submit_tiktok_mp4_to_mp3():
    data = request.form.get('link')
    if not data:
        return "Error: No URL provided", 400

    try:
        mp4_file_path = download_tiktok_video(data)
        
        mp3_file_path = convert_mp4_to_mp3(mp4_file_path)
        
        return send_file(mp3_file_path, as_attachment=True)
    except Exception as e:
        return f"Error processing TikTok MP4 to MP3: {str(e)}", 500


@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.get('link')
    if not data:
        return "Error: No URL provided", 400

    try:
        file_path = download_video(data)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading video: {str(e)}", 500

@app.route('/submit_tiktok', methods=['POST'])
def submit_tiktok():
    data = request.form.get('link')
    if not data:
        return "Error: No URL provided", 400

    try:
        file_path = download_tiktok_video(data)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading TikTok video: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=False, port=5000, host="penjualan.ddns.net")
