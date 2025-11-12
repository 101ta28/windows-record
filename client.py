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

OUTPUT_DIR = Path(r"C:\Users\User\Downloads")

SCRIPT_DIR = Path(__file__).resolve().parent


def set_output_dir(path):
    """実行時に保存先を変更するためのユーティリティ（Path へ変換して設定）"""
    global OUTPUT_DIR
    OUTPUT_DIR = Path(path)


def _resolve_output_dir():
    """
    OUTPUT_DIR を Path に正規化して返す。
    - expanduser() を行う（~ を使える）
    - 文字列や Path オブジェクトを受け付ける
    - 相対パスならスクリプト位置を基準に絶対化する
    - ディレクトリがなければ作る
    """
    target = OUTPUT_DIR

    # 文字列や Path 以外が来たら早期にわかるようにエラー
    if not isinstance(target, (str, Path)):
        raise RuntimeError(f"Invalid RECORD_OUTPUT_DIR value: {repr(target)} (type={type(target)})")

    # Path に変換してホーム展開
    target_path = Path(str(target)).expanduser()

    # 相対パスならスクリプトディレクトリ基準で絶対化
    if not target_path.is_absolute():
        target_path = (SCRIPT_DIR / target_path)

    # 作成（存在すれば何もしない）
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def _get_screen_resolution():
    """
    Windows API から画面解像度を取得する。
    取得に失敗した場合は 1920x1080 を返す（フォールバック）。
    """
    try:
        user32 = ctypes.windll.user32
        try:
            # DPI の影響を抑える（環境により例外になることがある）
            user32.SetProcessDPIAware()
        except Exception:
            pass
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return int(w), int(h)
    except Exception:
        return 1920, 1080


def build_cmds():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = _resolve_output_dir()
    screen_file = output_dir / f"screen_{timestamp}.mp4"
    webcam_file = output_dir / f"webcam_{timestamp}.mp4"

    # 画面解像度を取得して gdigrab に渡す（安定化のため）
    screen_w, screen_h = _get_screen_resolution()
    video_size = f"{screen_w}x{screen_h}"

    # ゲーム画面 + ステレオミックス音声
    # -draw_mouse 1 でカーソルも保存、-video_size で確実に画面全体をキャプチャ
    screen_cmd = [
        "ffmpeg",
        "-y",
        "-f", "gdigrab",
        "-framerate", "30",
        "-draw_mouse", "1",
        "-offset_x", "0",
        "-offset_y", "0",
        "-video_size", video_size,
        "-i", "desktop",
        "-f", "dshow",
        "-i", f"audio={GAME_AUDIO_DEVICE}",
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
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
    global screen_proc, webcam_proc, screen_log_f, webcam_log_f
    with proc_lock:
        if screen_proc or webcam_proc:
            print("ℹ️ 既に録画中です")
            return

        screen_cmd, webcam_cmd, output_dir = build_cmds()
        new_screen_proc = None
        new_webcam_proc = None

        # ログファイルを用意
        screen_log = output_dir / "screen_ffmpeg.log"
        webcam_log = output_dir / "webcam_ffmpeg.log"

        # ログファイルハンドルはグローバルに保持しておく（プロセス終了まで開いたままにする）
        screen_log_f = None
        webcam_log_f = None

        try:
            # バイナリで開く（ffmpeg の出力をそのまま保存）
            screen_log_f = open(screen_log, "ab")
            webcam_log_f = open(webcam_log, "ab")

            # ffmpeg のエラーログを確認しやすくするため stdout/stderr をログへリダイレクト
            new_screen_proc = subprocess.Popen(
                screen_cmd,
                stdin=subprocess.PIPE,
                stdout=screen_log_f,
                stderr=subprocess.STDOUT,
                creationflags=0
            )
            new_webcam_proc = subprocess.Popen(
                webcam_cmd,
                stdin=subprocess.PIPE,
                stdout=webcam_log_f,
                stderr=subprocess.STDOUT,
                creationflags=0
            )

            # 少し待ってプロセスが即終了していないか確認（起動エラーの検出）
            time.sleep(0.6)
            if new_screen_proc.poll() is not None:
                # 起動失敗 -> ログの末尾を表示して原因の手がかりを出す
                try:
                    screen_log_f.flush()
                    screen_log_f.close()
                except Exception:
                    pass
                try:
                    with open(screen_log, "rb") as lf:
                        lines = lf.read().splitlines()[-200:]
                        print("⚠️ screen ffmpeg failed to start. last log lines:")
                        for line in lines[-20:]:
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
                        for line in lines[-20:]:
                            try:
                                print(line.decode(errors="replace"))
                            except Exception:
                                print(line)
                except Exception:
                    pass
                raise RuntimeError("webcam ffmpeg failed to start (see log).")

            # 成功したのでグローバルに格納してログハンドルを保持
            screen_proc = new_screen_proc
            webcam_proc = new_webcam_proc
            globals()["screen_log_f"] = screen_log_f
            globals()["webcam_log_f"] = webcam_log_f

        except Exception as exc:
            # 片方だけ起動した場合に備えて必ず停止させる
            if new_screen_proc and new_screen_proc.poll() is None:
                _force_terminate(new_screen_proc)
            if new_webcam_proc and new_webcam_proc.poll() is None:
                _force_terminate(new_webcam_proc)
            # 未保持のファイルハンドルは閉じる
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

        # ログファイルを閉じる（存在する場合）
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
