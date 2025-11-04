import os
import socket
import subprocess
import threading
import time
from pathlib import Path

screen_proc = None
webcam_proc = None
should_exit = False
proc_lock = threading.Lock()

# 🎮 ゲーム音（ステレオミックスなど）
GAME_AUDIO_DEVICE = "ライン (Astro MixAmp Pro Game)"

# 🧑‍💻 マイク＆カメラ
MIC_AUDIO_DEVICE = "ヘッドセット マイク (2- Astro MixAmp Pro Voice)"
WEBCAM_DEVICE = "Logi C270 HD WebCam"
OUTPUT_DIR = Path(os.environ.get("RECORD_OUTPUT_DIR", "recordings"))
SCRIPT_DIR = Path(__file__).resolve().parent


def _resolve_output_dir():
    target = OUTPUT_DIR
    if not target.is_absolute():
        target = SCRIPT_DIR / target
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_cmds():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = _resolve_output_dir()
    screen_file = output_dir / f"screen_{timestamp}.mp4"
    webcam_file = output_dir / f"webcam_{timestamp}.mp4"

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
        "-pix_fmt",
        "yuv420p",
        str(screen_file),
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
        str(webcam_file),
    ]

    return screen_cmd, webcam_cmd, output_dir


def start_recording():
    """ffmpeg を二重起動しないようロックで保護しつつ開始する。"""
    global screen_proc, webcam_proc
    with proc_lock:
        if screen_proc or webcam_proc:
            print("ℹ️ 既に録画中です")
            return

        screen_cmd, webcam_cmd, output_dir = build_cmds()
        new_screen_proc = None
        new_webcam_proc = None

        try:
            new_screen_proc = subprocess.Popen(screen_cmd, stdin=subprocess.PIPE)
            new_webcam_proc = subprocess.Popen(webcam_cmd, stdin=subprocess.PIPE)
        except Exception as exc:
            # 片方だけ起動した場合に備えて必ず停止させる
            if new_screen_proc and new_screen_proc.poll() is None:
                _force_terminate(new_screen_proc)
            if new_webcam_proc and new_webcam_proc.poll() is None:
                _force_terminate(new_webcam_proc)
            print(f"⚠️ 録画開始に失敗しました: {exc}")
            return

        screen_proc = new_screen_proc
        webcam_proc = new_webcam_proc
        print(f"🎥 録画開始: {output_dir}")


def stop_recording():
    global screen_proc, webcam_proc
    with proc_lock:
        if screen_proc:
            _graceful_stop(screen_proc, "screen")
            screen_proc = None

        if webcam_proc:
            _graceful_stop(webcam_proc, "webcam")
            webcam_proc = None

    print("⏹️ 録画停止")


def _graceful_stop(proc, name):
    if proc.poll() is not None:
        return
    try:
        if proc.stdin:
            proc.stdin.write(b"q\n")
            proc.stdin.flush()
        proc.wait(timeout=5)
    except Exception as exc:
        print(f"⚠️ {name} 停止失敗: {exc}, 強制終了")
        _force_terminate(proc)
    finally:
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass


def _force_terminate(proc):
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _current_status():
    with proc_lock:
        if screen_proc or webcam_proc:
            return "RUNNING"
    return "IDLE"


def handle_client(conn, addr):
    with conn:
        cmd = conn.recv(1024).decode().strip()
        print(f"{addr} → {cmd}")

        if cmd == "start":
            start_recording()
            status = _current_status()
        elif cmd == "stop":
            stop_recording()
            status = "STOPPED"
        else:
            status = "UNKNOWN"
        conn.sendall(f"{status}\n".encode())


def run_server(host="0.0.0.0", port=5001):
    global should_exit
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        s.settimeout(1.0)

        print(f"📡 録画サーバー起動中...（port {port}）")
        try:
            while not should_exit:
                try:
                    conn, addr = s.accept()
                    worker = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                    worker.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n🛑 Ctrl+C を検出。サーバーを終了します。")
            stop_recording()


if __name__ == "__main__":
    run_server()
