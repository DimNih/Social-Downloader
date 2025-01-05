

# Social Downloader

Social Downloader adalah aplikasi web yang memungkinkan pengguna untuk mengunduh audio, video, dan video TikTok menggunakan URL dari berbagai platform. Aplikasi ini dibangun menggunakan Flask dan `yt-dlp` untuk mengambil konten dari berbagai sumber media.

## PREVIEW 

![Demo GIF](dokumentasi/test.gif)

## Fitur
- Mengunduh audio dari video YouTube dalam format MP3.
- Mengunduh video dari YouTube dalam format MP4.
- Mengunduh video dari TikTok dalam format MP4.

## Prasyarat

Sebelum memulai, pastikan Anda telah menginstal:

- Python 3.7 atau lebih baru
- Git
- pip (Python Package Installer)

## Cara Instalasi

Ikuti langkah-langkah di bawah ini untuk menyiapkan proyek di lingkungan lokal Anda.

### 1. Clone Repository

Pertama, clone repository ke mesin lokal Anda menggunakan Git.

```bash
git clone https://github.com/DimNih/Social-Downloader.git
cd Social-Downloader

## Instal Virtual Environment

python3 -m venv venv
source venv/bin/activate   # Di Linux/macOS
venv\Scripts\activate      # Di Windows

## Instal Dependensi Python

pip install flask yt-dlp ffmpeg-python

