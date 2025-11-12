import os
import socket
import subprocess
import threading
import time
import argparse
import ctypes
from pathlib import Path

# グローバルプロセス&ログハンドル
screen_proc = None
webcam_proc = None
screen_log_f = None
webcam_log_f = None

should_exit = False
proc_lock = threading.Lock()

# 🎮 ゲーム音（ステレオミックスなど）
GAME_AUDIO_DEVICE = "ライン (Astro MixAmp Pro Game)"

# 🧑‍💻 マイク＆カメラ
MIC_AUDIO_DEVICE = "ヘッドセット マイク (2- Astro MixAmp Pro Voice)"
WEBCAM_DEVICE = "Logi C270 HD WebCam"

# 出力先（必要なら set_output_dir() で変更）
OUTPUT_DIR = Path(r"C:\Users\User\Downloads")

SCRIPT_DIR = Path(__file__).resolve().parent


def set_output_dir(path):
    """実行時に保存先を変更（Pathに変換）"""
    global OUTPUT_DIR
    OUTPUT_DIR = Path(path)


def _resolve_output_dir():
    target = OUTPUT_DIR
    if not isinstance(target, (str, Path)):
        raise RuntimeError(f"Invalid RECORD_OUTPUT_DIR value: {repr(target)} (type={type(target)})")
    target_path = Path(str(target)).expanduser()
    if not target_path.is_absolute():
        target_path = (SCRIPT_DIR / target_path)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def _get_screen_resolution():
    """
    Windows API から画面解像度を取得（フォールバックは 1920x1080）
    """
    try:
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return int(w), int(h)
    except Exception:
        return 1920, 1080


def build_cmds():
    """
    ffmpeg コマンドを返す。
    重要な点：
      - screen: gdigrab 用に video_size / draw_mouse / offset を指定
      - probe/analyzeduration / thread_queue_size / rtbufsize を指定して安定化
      - 出力コンテナは .mkv（途中停止時の壊れにくさ）
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = _resolve_output_dir()
    screen_file = output_dir / f"screen_{timestamp}.mkv"
    webcam_file = output_dir / f"webcam_{timestamp}.mkv"

    screen_w, screen_h = _get_screen_resolution()
    video_size = f"{screen_w}x{screen_h}"

    # 注意: -probesize/-analyzeduration は入力解析に影響するため入力の前に置く
    # thread_queue_size は入力直前に置くことで入力キューを確保します
    screen_cmd = [
        "ffmpeg",
        "-y",
        # 入力解析の余裕を増やす（警告対処）
        "-probesize", "50M",
        "-analyzeduration", "100M",
        # gdigrab 入力
        "-f", "gdigrab",
        "-framerate", "30",
        "-draw_mouse", "1",
        "-offset_x", "0",
        "-offset_y", "0",
        "-video_size", video_size,
        "-rtbufsize", "200M",
        "-i", "desktop",
        # 音声入力（dshow）に対するキュー
        "-thread_queue_size", "512",
        "-f", "dshow",
        "-i", f"audio={GAME_AUDIO_DEVICE}",
        # マッピングとエンコード
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", "30",  # 出力フレームレートを固定
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(screen_file),
    ]

    # Webカメラ + マイク
    webcam_cmd = [
        "ffmpeg",
        "-y",
        "-probesize", "25M",
        "-analyzeduration", "50M",
        "-thread_queue_size", "512",
        "-f", "dshow",
        "-rtbufsize", "200M",
        "-i", f"video={WEBCAM_DEVICE}:audio={MIC_AUDIO_DEVICE}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(webcam_file),
    ]

    return screen_cmd, webcam_cmd, output_dir


def start_recording():
    global screen_proc, webcam_proc, screen_log_f, webcam_log_f
    with proc_lock:
        if screen_proc or webcam_proc:
            print("ℹ️ 既に録画中です")
            return

        screen_cmd, webcam_cmd, output_dir = build_cmds()
        new_screen_proc = None
        new_webcam_proc = None

        screen_log = output_dir / "screen_ffmpeg.log"
        webcam_log = output_dir / "webcam_ffmpeg.log"

        screen_log_f = None
        webcam_log_f = None

        try:
            # ログは追記モードで開く（プロセスが再試行されても追記される）
            screen_log_f = open(screen_log, "ab")
            webcam_log_f = open(webcam_log, "ab")

            new_screen_proc = subprocess.Popen(
                screen_cmd,
                stdin=subprocess.PIPE,
                stdout=screen_log_f,
                stderr=subprocess.STDOUT,
            )
            new_webcam_proc = subprocess.Popen(
                webcam_cmd,
                stdin=subprocess.PIPE,
                stdout=webcam_log_f,
                stderr=subprocess.STDOUT,
            )

            # 起動の安定を見るため少し長めに待つ
            time.sleep(1.2)

            # 即死チェック
            if new_screen_proc.poll() is not None:
                try:
                    screen_log_f.flush()
                    screen_log_f.close()
                except Exception:
                    pass
                try:
                    with open(screen_log, "rb") as lf:
                        lines = lf.read().splitlines()[-200:]
                        print("⚠️ screen ffmpeg failed to start. last log lines:")
                        for line in lines[-30:]:
                            try:
                                print(line.decode(errors="replace"))
                            except Exception:
                                print(line)
                except Exception:
                    pass
                raise RuntimeError("screen ffmpeg failed to start (see log).")

            if new_webcam_proc.poll() is not None:
                try:
                    webcam_log_f.flush()
                    webcam_log_f.close()
                except Exception:
                    pass
                try:
                    with open(webcam_log, "rb") as lf:
                        lines = lf.read().splitlines()[-200:]
                        print("⚠️ webcam ffmpeg failed to start. last log lines:")
                        for line in lines[-30:]:
                            try:
                                print(line.decode(errors="replace"))
                            except Exception:
                                print(line)
                except Exception:
                    pass
                raise RuntimeError("webcam ffmpeg failed to start (see log).")

            # 成功 -> グローバルに保持（ログハンドルはプロセス存続中保持）
            screen_proc = new_screen_proc
            webcam_proc = new_webcam_proc
            globals()["screen_log_f"] = screen_log_f
            globals()["webcam_log_f"] = webcam_log_f

        except Exception as exc:
            if new_screen_proc and new_screen_proc.poll() is None:
                _force_terminate(new_screen_proc)
            if new_webcam_proc and new_webcam_proc.poll() is None:
                _force_terminate(new_webcam_proc)
            try:
                if screen_log_f and not screen_log_f.closed:
                    screen_log_f.close()
            except Exception:
                pass
            try:
                if webcam_log_f and not webcam_log_f.closed:
                    webcam_log_f.close()
            except Exception:
                pass
            print(f"⚠️ 録画開始に失敗しました: {exc}")
            return

        print(f"🎥 録画開始: {output_dir} (screen log → {screen_log}, webcam log → {webcam_log})")


def stop_recording():
    global screen_proc, webcam_proc, screen_log_f, webcam_log_f
    with proc_lock:
        if screen_proc:
            _graceful_stop(screen_proc, "screen")
            screen_proc = None

        if webcam_proc:
            _graceful_stop(webcam_proc, "webcam")
            webcam_proc = None

        try:
            if screen_log_f and not screen_log_f.closed:
                screen_log_f.flush()
                screen_log_f.close()
        except Exception:
            pass
        try:
            if webcam_log_f and not webcam_log_f.closed:
                webcam_log_f.flush()
                webcam_log_f.close()
        except Exception:
            pass
        screen_log_f = None
        webcam_log_f = None

    print("⏹️ 録画停止")


def _graceful_stop(proc, name):
    if proc.poll() is not None:
        return
    try:
        if proc.stdin:
            try:
                proc.stdin.write(b"q\n")
                proc.stdin.flush()
            except Exception:
                pass
        proc.wait(timeout=7)
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
    try:
        resolved = _resolve_output_dir()
    except Exception as exc:
        print(f"ERROR: 出力先の解決に失敗しました: {exc}")
        raise

    print(f"📁 出力先ディレクトリ: {resolved}")

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
    parser = argparse.ArgumentParser(description="録画サーバー")
    parser.add_argument("--host", default="0.0.0.0", help="バインドするホスト")
    parser.add_argument("--port", "-p", type=int, default=5001, help="ポート番号")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
