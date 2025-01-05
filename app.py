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



app = Flask(__name__)

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
    """Remove invalid characters from filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def is_youtube_link(link):
    # Validasi link YouTube
    youtube_regex = r'(https?://(?:www\.)?youtube\.com/.+|https?://(?:www\.)?youtu\.be/.+)'
    return bool(re.match(youtube_regex, link))

def download_audio(link):
    if not is_youtube_link(link):
        raise ValueError("Invalid link! Only YouTube links are allowed.")
    
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
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = sanitize_filename(info['title'])
            
            video_file = next(
                (f for f in os.listdir('videos') if f.startswith(title) and f.endswith('.mp4')), 
                None
            )
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")

            file_name = os.path.join('videos', video_file)

        with open("history.txt", "a") as myfile:
            myfile.write(f"\n{datetime.now().strftime('%d/%m/%y__%H:%M:%S')} --> {link}\n")

        return file_name

    except Exception as e:
        with open("error_log.txt", "a") as log:
            log.write(f"Error: {str(e)}\n")
        raise Exception(f"Error downloading video: {str(e)}")



def is_tiktok_link(link):
    tiktok_regex = r'(https?://(?:www\.)?tiktok\.com/.+)'
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

def download_instagram_video(link):
    if not is_instagram_link(link):
        raise ValueError("Invalid link! Only Instagram links are allowed.")
    
    if os.path.exists('instagram_videos'):
        if len(os.listdir('instagram_videos')) > 2:
            shutil.rmtree('instagram_videos')
    else:
        os.mkdir('instagram_videos')

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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info['title']
            video_file = next((f for f in os.listdir('instagram_videos') if f.startswith(title) and f.endswith('.mp4')), None)
            if not video_file:
                raise FileNotFoundError("Downloaded MP4 file not found!")
            return f"instagram_videos/{video_file}"
    except Exception as e:
        raise Exception(f"downloading Instagram video: {str(e)}")

def download_instagram_audio(link):
    if not is_instagram_link(link):
        raise ValueError("Invalid link! Only Instagram links are allowed.")

    if os.path.exists('instagram_audios'):
        if len(os.listdir('instagram_audios')) > 2:
            shutil.rmtree('instagram_audios')
    else:
        os.mkdir('instagram_audios')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'instagram_audios/%(title)s.%(ext)s',
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            title = info['title']
            audio_file = next((f for f in os.listdir('instagram_audios') if f.startswith(title)), None)
            if not audio_file:
                raise FileNotFoundError("Downloaded audio file not found!")

            audio_path = os.path.join('instagram_audios', audio_file)

            if os.path.exists(audio_path):
                os.remove(audio_path)

            mp3_file = audio_path.replace('.m4a', '.mp3').replace('.webm', '.mp3')
            os.system(f"ffmpeg -i \"{audio_path}\" \"{mp3_file}\"")

            if os.path.exists(audio_path):
                os.remove(audio_path)

            return mp3_file
    except Exception as e:
        raise Exception(f"Error downloading Instagram audio: {str(e)}")


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
    return text.replace(u"\u2019", "'")

def convert_word_to_pdf(filename, pdf_filename):
    # Check if the file extension is .docx
    if not filename.lower().endswith('.docx'):
        raise ValueError("Only .docx files are allowed for conversion")

    # Proceed with the conversion if the file is a .docx
    doc = Document(filename)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for para in doc.paragraphs:
        clean_text = replace_unsupported_characters(para.text)
        pdf.multi_cell(0, 10, clean_text)

    pdf.output(pdf_filename)
    print(f"Conversion successful! The PDF has been saved as {pdf_filename}")



@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    
    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        
        pdf_filename = filename.rsplit('.', 1)[0] + '.pdf'
        convert_word_to_pdf(filename, pdf_filename)
        
        return send_file(pdf_filename, as_attachment=True)

    return 'Invalid file format. Only DOCX is allowed.', 400



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
  