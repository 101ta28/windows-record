import socket

# クライアントPCのIP一覧
# CLIENTS = [
#     "192.168.xxx.xxx",
#     "192.168.xxx.xxx",
# ]
CLIENTS = []

PORT = 5001


def send_command(cmd):
    for ip in CLIENTS:
        try:
            with socket.create_connection((ip, PORT), timeout=3) as sock:
                sock.sendall(cmd.encode())
                resp = sock.recv(1024).decode().strip()
                print(f"{ip} → {resp}")
        except Exception as e:
            print(f"{ip} → 接続失敗: {e}")


if __name__ == "__main__":
    print("1. 録画開始 → start")
    print("2. 録画停止 → stop")
    print("3. 終了 → exit")

    while True:
        cmd = input(">>> ").strip().lower()
        if cmd in ["start", "stop"]:
            send_command(cmd)
        elif cmd == "exit":
            break
