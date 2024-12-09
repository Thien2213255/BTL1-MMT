import socket
import threading
import json

# Tracker server configuration
TRACKER_IP = "192.168.56.108"  # Địa chỉ IP của tracker (thay bằng IP thực tế)
TRACKER_PORT = 8080
PEER_LIST = []  # Danh sách các peer đã đăng ký

def handle_peer_connection(conn, addr):
    print(f"[TRACKER] Connected by {addr}")
    try:
        data = conn.recv(1024).decode('utf-8')
        request = json.loads(data)
        
        if request["action"] == "register":
            # Lưu thông tin peer và danh sách file
            peer_info = {
                "ip": addr[0],
                "port": request["port"],
                "files": request["files"]  # Lưu danh sách file
            }
            PEER_LIST.append(peer_info)
            conn.send(json.dumps({"status": "success", "peers": PEER_LIST}).encode('utf-8'))
        
        elif request["action"] == "get_peers":
            # Trả danh sách các peer và file của chúng
            conn.send(json.dumps({"status": "success", "peers": PEER_LIST}).encode('utf-8'))
    except Exception as e:
        print(f"[TRACKER ERROR] {e}")
    finally:
        conn.close()


def start_tracker():
    print(f"[TRACKER] Starting at {TRACKER_IP}:{TRACKER_PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((TRACKER_IP, TRACKER_PORT))
        server.listen(5)
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_peer_connection, args=(conn, addr)).start()

if __name__ == "__main__":
    start_tracker()
