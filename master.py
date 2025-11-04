import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# クライアントPCのIP一覧
# CLIENTS = [
#     "192.168.xxx.xxx",
#     "192.168.xxx.xxx",
# ]
CLIENTS = []

PORT = 5001


def _send_to_client(ip, cmd):
    try:
        with socket.create_connection((ip, PORT), timeout=3) as sock:
            sock.sendall(cmd.encode())
            resp = sock.recv(1024).decode().strip()
            return f"{ip} → {resp}"
    except Exception as e:
        return f"{ip} → 接続失敗: {e}"


def send_command(cmd):
    if not CLIENTS:
        return

    workers = min(len(CLIENTS), 32)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_send_to_client, ip, cmd): idx
            for idx, ip in enumerate(CLIENTS)
        }

        results = [None] * len(CLIENTS)
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()

    for message in results:
        print(message)


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
