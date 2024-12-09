import socket
import threading
import json
import os
from concurrent.futures import ThreadPoolExecutor
import time

# Peer configuration
#PEER_IP = "192.168.56.104"  # Thay bằng IP máy ảo peer
PEER_PORT = 33333
TRACKER_IP = "192.168.56.108"
TRACKER_PORT = 8080
DOWNLOAD_DIR = "./downloads"
UPLOAD_DIR = "./uploads"
AVAILABLE_FILES = os.listdir(UPLOAD_DIR)

downloaded_files = set()  # Tập hợp để lưu trữ các file đã tải

#lấy ip tự động cho mỗi máy
def get_local_ip():
    try:
        # Kết nối giả tới gateway của mạng Host-Only Adapter
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.56.1", 80))  # Địa chỉ gateway mặc định của VirtualBox
            ip = s.getsockname()[0]
        return ip
    except Exception as e:
        print(f"Error retrieving local IP in Host-Only Adapter: {e}")
        return "127.0.0.1"  # fallback nếu không lấy được IP
PEER_IP = get_local_ip()

# Register with tracker
def register_with_tracker():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_conn:
        tracker_conn.connect((TRACKER_IP, TRACKER_PORT))
        message = {"action": "register", "port": PEER_PORT, "files": AVAILABLE_FILES}
        tracker_conn.send(json.dumps(message).encode('utf-8'))
        response = json.loads(tracker_conn.recv(1024).decode('utf-8'))
        print("[PEER] Tracker response:", response)

# Handle incoming requests from peers
def handle_peer_connection(conn, addr):
    try:
        data = conn.recv(1024).decode('utf-8')
        request = json.loads(data)
        
        if request["action"] == "download":
            file_name = request["file_name"]
            file_path = os.path.join(UPLOAD_DIR, file_name)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    chunk = f.read(1024)
                    while chunk:
                        conn.sendall(chunk)
                        chunk = f.read(1024)

            else:
                conn.send(json.dumps({"status": "error", "message": "File not found"}).encode('utf-8'))
    except Exception as e:
        print(f"[PEER ERROR] {e}")
    finally:
        conn.close()

# Start peer server
def start_peer_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((PEER_IP, PEER_PORT))
        server.listen(5)
        print(f"[PEER] Server running on {PEER_IP}:{PEER_PORT}")
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_peer_connection, args=(conn, addr)).start()

# Download files from peers
def download_file(peer, file_name):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((peer["ip"], peer["port"]))
            request = {"action": "download", "file_name": file_name}
            s.send(json.dumps(request).encode("utf-8"))

            # Nhận dữ liệu từ peer và lưu vào file
            with open(f"downloads/{file_name}", "wb") as f:
                while True:
                    data = s.recv(1024)
                    if not data:
                        break
                    f.write(data)
            print(f"[PEER] Successfully downloaded {file_name}")
    except Exception as e:
        print(f"[PEER ERROR] Failed to download {file_name} from {peer['ip']}:{peer['port']} - {e}")

# Upload file to a peer
def upload_file(peer, file_name):
    try:
        file_path = os.path.join(UPLOAD_DIR, file_name)
        if os.path.exists(file_path):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((peer["ip"], peer["port"]))
                request = {"action": "upload", "file_name": file_name}
                s.send(json.dumps(request).encode("utf-8"))

                with open(file_path, "rb") as f:
                    chunk = f.read(1024)
                    while chunk:
                        s.sendall(chunk)
                        chunk = f.read(1024)
                print(f"[PEER] Successfully uploaded {file_name} to {peer['ip']}:{peer['port']}")
        else:
            print(f"[PEER ERROR] File {file_name} not found for upload")
    except Exception as e:
        print(f"[PEER ERROR] Failed to upload {file_name} to {peer['ip']}:{peer['port']} - {e}")

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Register with the tracker
    register_with_tracker()
    
    # Start the peer server
    threading.Thread(target=start_peer_server).start()
    
    print("[PEER] Waiting for 10 seconds to allow other peers to start...")
    time.sleep(10)

    
    # Simulate downloading and uploading files
    with ThreadPoolExecutor(max_workers=5) as executor:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tracker_conn:
            tracker_conn.connect((TRACKER_IP, TRACKER_PORT))
            tracker_conn.send(json.dumps({"action": "get_peers"}).encode('utf-8'))
            response = json.loads(tracker_conn.recv(1024).decode('utf-8'))

            if response["status"] == "success":
                peer_list = response["peers"]
                print("[PEER] Available peers and their files:")
                for peer in peer_list:
                    if peer["ip"] != PEER_IP or peer["port"] != PEER_PORT:
                        print(f"Peer: {peer['ip']}:{peer['port']}, Files: {peer['files']}")

                        # Tải và upload file với peer
                        for file_name in peer["files"]:
                            if file_name not in downloaded_files:
                                print(f"[PEER] Downloading {file_name} from {peer['ip']}:{peer['port']}")
                                executor.submit(download_file, peer, file_name)
                                downloaded_files.add(file_name)
                            if file_name not in peer["files"]:
                                print(f"[PEER] Uploading {file_name} to {peer['ip']}:{peer['port']}")
                                executor.submit(upload_file, peer, file_name)

