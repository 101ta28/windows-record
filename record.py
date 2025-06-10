import subprocess
import time

# タイムスタンプ付きのファイル名
timestamp = time.strftime("%Y%m%d_%H%M%S")
screen_file = f"screen_{timestamp}.mp4"
webcam_file = f"webcam_{timestamp}.mp4"

# --- 設定: 環境に合わせて調整 ---
# 空なら音声無効
AUDIO_DEVICE = "マイク (Realtek(R) Audio)"
WEBCAM_DEVICE = "HD Webcam"
# --------------------------------

# 画面録画コマンド
screen_cmd = ["ffmpeg", "-y", "-f", "gdigrab", "-framerate", "30", "-i", "desktop"]

if AUDIO_DEVICE:
    screen_cmd += ["-f", "dshow", "-i", f"audio={AUDIO_DEVICE}"]
    screen_cmd += [
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        screen_file,
    ]
else:
    screen_cmd += [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-an",
        screen_file,
    ]

# Webカメラ録画コマンド
webcam_cmd = [
    "ffmpeg",
    "-y",
    "-f",
    "dshow",
    "-i",
    f"video={WEBCAM_DEVICE}",
    "-c:v",
    "libx264",
    "-preset",
    "ultrafast",
    webcam_file,
]

# 両方同時に開始（標準入力を使えるようにする）
print("🎥 録画開始")
screen_proc = subprocess.Popen(screen_cmd, stdin=subprocess.PIPE)
webcam_proc = subprocess.Popen(webcam_cmd, stdin=subprocess.PIPE)

input("⏹️  Enterキーで録画を停止します...")

# 正常終了のために "q\n" を送る
screen_proc.stdin.write(b"q\n")
screen_proc.stdin.flush()

webcam_proc.stdin.write(b"q\n")
webcam_proc.stdin.flush()

# プロセスが終了するのを待つ
screen_proc.wait()
webcam_proc.wait()

print("✅ 録画を停止しました")
print(f"保存ファイル: {screen_file}, {webcam_file}")
