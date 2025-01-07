from flask import Flask, request, send_file, render_template_string, render_template
import os
import shutil
from datetime import datetime
import yt_dlp
import re
import ffmpeg
import time
import subprocess
from fpdf import FPDF
from docx import Document
from zipfile import BadZipFile
import zipfile
from werkzeug.utils import secure_filename



app = Flask(__name__)

cancel_download = False


UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'docx'}


# Ensure the 'audios', 'videos', 'tiktok_videos', 'audio tiktok' and 'history.txt'
if not os.path.exists('audios'):
    os.mkdir('audios')
if not os.path.exists('videos'):
    os.mkdir('videos')
if not os.path.exists('tiktok_videos'):
    os.mkdir('tiktok_videos')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def sanitize_filename(filename):
    # Remove invalid characters and trim the filename
    return re.sub(r'[<>:"/\\|?*]', '_', filename)



def is_youtube_link(link):
    # Validasi link YouTube
    youtube_regex = r'(https?://(?:www\.)?youtube\.com/.+|https?://(?:www\.)?youtu\.be/.+)'
    return bool(re.match(youtube_regex, link))

def download_audio(link):
    if not is_youtube_link(link):
        raise ValueError("Invalid link! Only YouTube links are allowed.")
    
    # Ensure the 'audios' directory exists
    if not os.path.exists('audios'):
        os.mkdir('audios')
    
    # Clean up 'audios' folder if it has more than 5 files
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
        'keepvideo': True,  # Prevent deletion of the original video file
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            file_name = f"audios/{title}.mp3"

            # Ensure the file name is valid
            file_name = os.path.join('audios', title + '.mp3')

            # Check if the MP4 file exists and convert it
            mp4_file = f"audios/{title}.webm"
            if os.path.exists(mp4_file):
                mp3_path = convert_mp4_to_mp3(mp4_file)
                return mp3_path

            if not os.path.exists(file_name):
                raise FileNotFoundError(f"Downloaded file not found: {file_name}")

        # Logging download history
        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        raise Exception(f"Error downloading audio: {str(e)}")



def stop_download():
    global cancel_download
    cancel_download = True

def progress_hook(d):
    global cancel_download
    if cancel_download:
        if 'ydl' in globals():
            ydl.abort()  # This will stop the download immediately
        raise Exception("Download canceled by the user")
    if d['status'] == 'finished':
        print(f"Download finished: {d['filename']}")

# Function to download video
def download_video(link):
    global ydl
    if not is_youtube_link(link):
        raise ValueError("Invalid link! Only YouTube links are allowed.")
    
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
        'progress_hooks': [progress_hook],  # Hook to monitor progress
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl_instance:
            global ydl
            ydl = ydl_instance
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            
            video_file = next(
                (f for f in os.listdir('videos') if f.startswith(title) and f.endswith('.mp4')), 
                None
            )
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")

            file_name = os.path.join('videos', video_file)

        # Logging download history
        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        with open("error_log.txt", "a") as log:
            log.write(f"Error: {str(e)}\n")
        raise Exception(f"Error downloading video: {str(e)}")



def is_tiktok_link(link):
    tiktok_regex = r'(https?://(?:www\.)?tiktok\.com/[^/]+/[a-zA-Z0-9]+/?|https?://vt\.tiktok\.com/[a-zA-Z0-9]+/?)'
    return bool(re.match(tiktok_regex, link))


def download_tiktok_video(link):
    if not is_tiktok_link(link):
        raise ValueError("Invalid link! Only TikTok links are allowed.")
    
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



def is_instagram_link(link):
    return bool(re.match(r'https://www.instagram.com/', link))

def is_instagram_link(link):
    # Example: Check if the link contains "instagram.com"
    return isinstance(link, str) and "instagram.com" in link

def download_instagram_video(link):
    if not isinstance(link, str) or not link.strip():
        raise ValueError("Invalid link! Please provide a non-empty Instagram link.")
    
    if not is_instagram_link(link):
        raise ValueError("Invalid link! Only Instagram links are allowed.")
    
    try:
        # Manage directory
        if os.path.exists('instagram_videos'):
            if len(os.listdir('instagram_videos')) > 2:
                shutil.rmtree('instagram_videos')
                os.mkdir('instagram_videos')  # Recreate after deletion
        else:
            os.mkdir('instagram_videos')

        # YouTube-DL options
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'instagram_videos/%(title)s.%(ext)s',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info.get('title', 'video')  # Fallback title
            video_file = next(
                (f for f in os.listdir('instagram_videos') if f.endswith('.mp4')),
                None
            )
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")
            return f"instagram_videos/{video_file}"
    except Exception as e:
        raise Exception(f"Error downloading Instagram video: {str(e)}")

import os
import shutil
import subprocess
import yt_dlp
import re

def download_instagram_audio(link):
    if not is_instagram_link(link):
        raise ValueError("Invalid link! Only Instagram links are allowed.")
    
    audio_folder = 'instagram_audios'
    if os.path.exists(audio_folder):
        if len(os.listdir(audio_folder)) > 2:
            shutil.rmtree(audio_folder)
    else:
        os.mkdir(audio_folder)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{audio_folder}/%(title)s.%(ext)s',
        'nocheckcertificate': True,
        'extractaudio': True,
        'audioquality': 0,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info['title']

            files_in_directory = os.listdir(audio_folder)
            audio_file = next((f for f in files_in_directory if f.startswith(title) and f.lower().endswith(('webm', 'm4a'))), None)

            if not audio_file:
                raise FileNotFoundError(f"Downloaded audio file for title '{title}' not found in the directory.")

            audio_path = os.path.join(audio_folder, audio_file)
            mp3_file = os.path.join(audio_folder, f"{title}.mp3")

            if os.path.exists(mp3_file):
                os.remove(mp3_file)

            if not audio_file.endswith('.mp3'):
                subprocess.run(['ffmpeg', '-i', audio_path, mp3_file], check=True)
                os.remove(audio_path)

            return mp3_file

    except Exception as e:
        raise Exception(f"Error downloading Instagram audio: {str(e)}")

def is_instagram_link(link):
    return bool(re.match(r'https://www.instagram.com/', link))


def is_facebook_link(link):
    return bool(re.match(r'https://www.facebook.com/', link))

def download_facebook_video(link):
    if not is_facebook_link(link):
        raise ValueError("Invalid link! Only Facebook links are allowed.")
    
    video_folder = 'facebook_videos'
    if os.path.exists(video_folder):
        if len(os.listdir(video_folder)) > 2:
            shutil.rmtree(video_folder)
    else:
        os.mkdir(video_folder)

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{video_folder}/%(title)s.%(ext)s',
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
            title = info['title']
            video_file = next((f for f in os.listdir(video_folder) if f.startswith(title) and f.endswith('.mp4')), None)
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")
            return f"{video_folder}/{video_file}"
    except Exception as e:
        raise Exception(f"Error downloading Facebook video: {str(e)}")

def download_facebook_audio(link):
    if not is_facebook_link(link):
        raise ValueError("Invalid link! Only Facebook links are allowed.")

    audio_folder = 'facebook_audios'
    if os.path.exists(audio_folder):
        if len(os.listdir(audio_folder)) > 2:
            shutil.rmtree(audio_folder)
    else:
        os.mkdir(audio_folder)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{audio_folder}/%(title)s.%(ext)s',
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info['title']

            audio_file = next((f for f in os.listdir(audio_folder) if f.startswith(title)), None)
            if not audio_file:
                raise FileNotFoundError("Downloaded audio file not found!")

            audio_path = os.path.join(audio_folder, audio_file)

            mp3_file = audio_path.replace('.m4a', '.mp3').replace('.webm', '.mp3')
            if os.path.exists(mp3_file):
                os.remove(mp3_file)

            os.system(f"ffmpeg -i \"{audio_path}\" \"{mp3_file}\"")

            if os.path.exists(audio_path):
                os.remove(audio_path)

            return mp3_file
    except Exception as e:
        raise Exception(f"Error downloading Facebook audio: {str(e)}")




def is_facebook_link(link):
    # Check if the link is a Facebook video link
    return bool(re.match(r'https://www.facebook.com/', link))

def download_facebook_video(link):
    if not is_facebook_link(link):
        raise ValueError("Invalid link! Only Facebook links are allowed.")
    
    if os.path.exists('facebook_videos'):
        if len(os.listdir('facebook_videos')) > 2:
            shutil.rmtree('facebook_videos')
    else:
        os.mkdir('facebook_videos')

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'facebook_videos/%(title)s.%(ext)s',
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
            title = info['title']
            video_file = next((f for f in os.listdir('facebook_videos') if f.startswith(title) and f.endswith('.mp4')), None)
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")
            return f"facebook_videos/{video_file}"
    except Exception as e:
        raise Exception(f"Error downloading Facebook video: {str(e)}")
    
def download_facebook_audio(link):
    if not is_facebook_link(link):
        raise ValueError("Invalid link! Only Facebook links are allowed.")

    audio_folder = 'facebook_audios'
    if os.path.exists(audio_folder):
        if len(os.listdir(audio_folder)) > 2:
            shutil.rmtree(audio_folder)
    else:
        os.mkdir(audio_folder)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{audio_folder}/%(title)s.%(ext)s',
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info['title']

            audio_file = next((f for f in os.listdir(audio_folder) if f.startswith(title)), None)
            if not audio_file:
                raise FileNotFoundError("Downloaded audio file not found!")

            audio_path = os.path.join(audio_folder, audio_file)

            if os.path.exists(audio_path):
                os.remove(audio_path)

            mp3_file = audio_path.replace('.m4a', '.mp3').replace('.webm', '.mp3')
            os.system(f"ffmpeg -i \"{audio_path}\" \"{mp3_file}\"")

            if os.path.exists(audio_path):
                os.remove(audio_path)

            return mp3_file
    except Exception as e:
        raise Exception(f"Error downloading Facebook audio: {str(e)}")

def replace_unsupported_characters(text):
    """Replace unsupported characters with safe alternatives."""
    return text.replace(u"\u2019", "'")


def is_valid_docx(file_path):
    """Check if the uploaded file is a valid and non-corrupted DOCX file."""
    try:
        with zipfile.ZipFile(file_path, 'r') as zipf:
            corrupt_file = zipf.testzip()
            if corrupt_file:
                print(f"Corrupted file inside DOCX: {corrupt_file}")
                return False
        return True
    except zipfile.BadZipFile:
        print("Not a valid DOCX (ZIP) file.")
        return False


def check_images_in_docx(file_path):
    """Check for corrupted images in a DOCX file."""
    try:
        with zipfile.ZipFile(file_path, 'r') as zipf:
            for file in zipf.namelist():
                if file.startswith("word/media/"):
                    with zipf.open(file) as img_file:
                        img_file.read()  # Attempt to read the image
        return True
    except Exception as e:
        print(f"Corrupted image detected: {e}")
        return False


def convert_word_to_pdf(filename, pdf_filename):
    """Convert a Word document to a PDF."""
    try:
        doc = Document(filename)
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        for para in doc.paragraphs:
            clean_text = replace_unsupported_characters(para.text)
            pdf.multi_cell(0, 10, clean_text)

        pdf.output(pdf_filename)
    except zipfile.BadZipFile:
        raise ValueError("The uploaded DOCX file is corrupted.")
    except Exception as e:
        raise ValueError(f"Error during conversion: {e}")


@app.route('/')
def hello_world():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    """Handle file upload and conversion to PDF."""
    if 'file' not in request.files:
        return "No file part in the request.", 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Validate DOCX file
        if not is_valid_docx(file_path):
            return "The uploaded file is corrupted or not a valid DOCX file.", 400

        if not check_images_in_docx(file_path):
            return "The uploaded DOCX file contains corrupted images.", 400

        # Convert to PDF
        try:
            pdf_filename = filename.rsplit('.', 1)[0] + ".pdf"
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            convert_word_to_pdf(file_path, pdf_path)
            return send_file(pdf_path, as_attachment=True)
        except ValueError as e:
            return str(e), 400
    else:
        return "Invalid file type. Only .docx files are allowed.", 400


@app.route('/submit_audio', methods=['POST'])
def submit_audio():
    data = request.form.get('link')
    if not data:
        return "Error: No URL provided", 400

    try:
        audio_file_path = download_audio(data)
        return send_file(audio_file_path, as_attachment=True)
    
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
    
@app.route('/submit_instagram_video', methods=['POST'])
def submit_instagram_video():
    link = request.form.get('link')
    if not link:
        return "Error: No URL provided", 400

    try:
        video_file_path = download_instagram_video(link)
        return send_file(video_file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading Instagram video: {str(e)}", 500



@app.route('/submit_instagram_audio', methods=['POST'])
def submit_instagram_audio():
    link = request.form.get('link')
    if not link:
        return "Error: No URL provided", 400

    try:
        audio_file_path = download_instagram_audio(link)
        return send_file(audio_file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading Instagram audio: {str(e)}", 500

@app.route('/submit_facebook_video', methods=['POST'])
def submit_facebook_video():
    link = request.form.get('link')
    if not link:
        return "Error: No URL provided", 400

    try:
        video_file_path = download_facebook_video(link)
        return send_file(video_file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading Facebook video: {str(e)}", 500

@app.route('/submit_facebook_audio', methods=['POST'])
def submit_facebook_audio():
    link = request.form.get('link')
    if not link:
        return "Error: No URL provided", 400

    try:
        audio_file_path = download_facebook_audio(link)
        return send_file(audio_file_path, as_attachment=True)
    except Exception as e:
        return f"Error downloading Facebook audio: {str(e)}", 500


    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # Mendapatkan port dari variabel lingkungan atau default ke 8000
    app.run(debug=False, host="0.0.0.0", port=port)  # Mendengarkan di semua alamat IP dan port yang benar
  