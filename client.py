import subprocess
import time
import socket
import threading

screen_proc = None
webcam_proc = None

# 🎮 ゲーム音（ステレオミックスなど）
GAME_AUDIO_DEVICE = "ライン (Astro MixAmp Pro Game)"

# 🧑‍💻 マイク＆カメラ
MIC_AUDIO_DEVICE = "ヘッドセット マイク (2- Astro MixAmp Pro Voice)"
WEBCAM_DEVICE = "Logi C270 HD WebCam"


def build_cmds():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    screen_file = f"screen_{timestamp}.mp4"
    webcam_file = f"webcam_{timestamp}.mp4"

    # ゲーム画面 + ステレオミックス音声
    screen_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "gdigrab",
        "-framerate",
        "30",
        "-i",
        "desktop",
        "-f",
        "dshow",
        "-i",
        f"audio={GAME_AUDIO_DEVICE}",
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

    # Webカメラ + マイク音声
    webcam_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "dshow",
        "-i",
        f"video={WEBCAM_DEVICE}:audio={MIC_AUDIO_DEVICE}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-c:a",
        "aac",
        webcam_file,
    ]

    return screen_cmd, webcam_cmd


def start_recording():
    global screen_proc, webcam_proc
    if screen_proc or webcam_proc:
        return  # 重複起動防止
    screen_cmd, webcam_cmd = build_cmds()
    screen_proc = subprocess.Popen(screen_cmd, stdin=subprocess.PIPE)
    webcam_proc = subprocess.Popen(webcam_cmd, stdin=subprocess.PIPE)
    print("🎥 録画開始")


def stop_recording():
    global screen_proc, webcam_proc
    if screen_proc:
        try:
            if screen_proc.poll() is None:  # 実行中かチェック
                screen_proc.stdin.write(b"q\n")
                screen_proc.stdin.flush()
                screen_proc.wait(timeout=5)
        except Exception as e:
            print(f"⚠️ screen 停止失敗: {e}, 強制終了")
            screen_proc.terminate()
        screen_proc = None

    if webcam_proc:
        try:
            if webcam_proc.poll() is None:
                webcam_proc.stdin.write(b"q\n")
                webcam_proc.stdin.flush()
                webcam_proc.wait(timeout=5)
        except Exception as e:
            print(f"⚠️ webcam 停止失敗: {e}, 強制終了")
            webcam_proc.terminate()
        webcam_proc = None

    print("⏹️ 録画停止")


def handle_client(conn, addr):
    with conn:
        cmd = conn.recv(1024).decode().strip()
        print(f"{addr} → {cmd}")
        if cmd == "start":
            start_recording()
        elif cmd == "stop":
            stop_recording()
        conn.sendall(b"OK\n")


def run_server(host="0.0.0.0", port=5001):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"📡 録画サーバー起動中...（port {port}）")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()


if __name__ == "__main__":
    run_server()
