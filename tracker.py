import socket
import threading
import os
from helper import *
from torrent import *
import psycopg2

HOST_NAME = socket.gethostname()
HOST = socket.gethostbyname(HOST_NAME)
PORT = 5050


class TrackerServer:
    def __init__(self):
        self.conn = psycopg2.connect(dbname="socket", user="postgres", password="cuongdola231", host="", port="5432")
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((HOST, PORT))
        self.tracker_socket.listen(QUEUE_SIZE)
        self.create_tables()
        self.files: Set[str] = set()  # storage file keep in tracker
        self.peers_with_file: Dict[str, Set[int]] = {}  # peers_with_file[file_name] = list peer

    def create_tables(self):
        with self.lock:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                    id SERIAL PRIMARY KEY,
                                    username TEXT UNIQUE,
                                    password TEXT,
                                    ip TEXT,
                                    port INTEGER,
                                    status INTEGER
                                    )''')
            self.conn.commit()

    def handle_peer(self, client_socket, addr):
        print(f"Handling connection from {addr}")
        while True:
            try:
                print(f"Waiting for data from {addr}")
                data = recv_msg(client_socket)
                if data is None:
                    print(f"Client {addr} disconnected")
                    break
                print(f"Received {len(data)} bytes from {addr}")
                info = pickle.loads(data)
                print(f"Received message from {addr}: {info['type']}")
                if info['type'] == REGISTER:
                    self.register_service(client_socket, info)
                elif info['type'] == LOGIN:
                    self.login_service(client_socket, info)
                elif info['type'] == REGISTER_FILE:
                    peer_id = info['peer_id']
                    self.register_file_service(client_socket, info, peer_id)
                elif info['type'] == LOGOUT:
                    self.logout_service(client_socket, info)
                elif info['type'] == GET_LIST_FILES_TO_DOWNLOAD:
                    self.show_available_files(client_socket)
                elif info['type'] == REQUEST_FILE:
                    self.show_peer_hold_file_service(client_socket, info['file_name'])

                # ... handle other message types ...
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                traceback.print_exc()
                break
        client_socket.close()
        print(f"Connection closed for {addr}")

    def register_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Registering user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                print(f"User {user} already exists")
                self.sendMsg(client_socket, {'type': REGISTER_FAILED, 'message': 'Account has already been used'})
            else:
                self.insertUser(user, passwd, ip, port)
                peer_id = self.getPeerId(user)
                print(f"User {user} registered successfully with peer_id {peer_id}")

                self.sendMsg(client_socket, {'type': REGISTER_SUCCESSFUL, 'message': 'Account created successfully',
                                             'peer_id': peer_id})
        except Exception as e:
            print(f"Error in register_service: {e}")
            traceback.print_exc()
            self.sendMsg(client_socket, {'type': REGISTER_FAILED, 'message': 'Internal server error'})

    def login_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Logging in user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                if record[2] == passwd:
                    peer_id = self.getPeerId(user)
                    self.sendMsg(client_socket,
                                 {'type': LOGIN_SUCCESSFUL, 'message': 'Login successful', 'peer_id': peer_id})
                    self.updateLogin(user, ip, port)
                else:
                    self.sendMsg(client_socket, {'type': LOGIN_FAILED, 'message': 'Incorrect password'})
            else:
                self.sendMsg(client_socket, {'type': LOGIN_FAILED, 'message': 'Account does not exist'})
        except Exception as e:
            print(f"Error in login_service: {e}")
            traceback.print_exc()
            self.sendMsg(client_socket, {'type': LOGIN_FAILED, 'message': 'Internal server error'})

    def register_file_service(self, client_socket, info, peer_id):
        metainfo = info['metainfo']
        print(f"Registering file: {metainfo['file_name']}")
        self.files.add(metainfo['file_name'])
        file_name = metainfo['file_name']
        # Initialize the list for this file if it doesn't exist
        if file_name not in self.peers_with_file:
            self.peers_with_file[file_name] = set()

        self.peers_with_file[file_name].add(peer_id)
        # Create magnet link
        magnet_link = create_magnet_link(metainfo, HOST, PORT)

        # save torrent file to repo_tracker
        if not os.path.exists('repo_tracker' + metainfo['file_name'] + '.torrent'):
            with open(os.path.join('repo_tracker', f"{metainfo['file_name']}.torrent"), 'wb') as f:
                pickle.dump(metainfo, f)
        # Send response back to client
        print('All files been registered:')
        for file in self.files:
            print(file)

        print('File name with peer_id:')
        for file in self.peers_with_file:
            print(file, self.peers_with_file[file])

        self.sendMsg(client_socket, {
            'type': REGISTER_FILE_SUCCESSFUL,
            'message': 'File registered successfully',
            'magnet_link': magnet_link
        })

    def show_peer_hold_file_service(self, client_socket, file_name: str):
        list_peers = self.peers_with_file[file_name]
        ip_port_list = []
        for peer_id in list_peers:
            record = self.getIpandPortByPeerID(peer_id)
            if record:
                ip_port_list.append(record)

        if not len(ip_port_list):
            self.sendMsg(client_socket,
                         {'type': SHOW_PEER_HOLD_FILE_FAILED, 'message': 'No peer holds this file is online'})
            return

        with open(os.path.join('repo_tracker', f"{file_name}.torrent"), 'rb') as f:
            metainfo = pickle.load(f)

        self.sendMsg(client_socket, {'type': SHOW_PEER_HOLD_FILE,
                                     'metainfo': metainfo,
                                     'ip_port_list': ip_port_list})

    def logout_service(self, client_socket, info):
        peer_id = info['peer_id']
        self.updateUserStatus(peer_id, 0)
        record = self.getUserOnline()
        print('Online users:')
        for user in record:
            print(user[1])
        self.sendMsg(client_socket, {'type': LOGOUT_SUCCESSFUL, 'message': 'Logout successful'})

    def show_available_files(self, client_socket):
        self.sendMsg(client_socket, {'type': GET_LIST_FILES_TO_DOWNLOAD, 'files': list(self.files)})

    def sendMsg(self, client_socket, msg):
        try:
            send_msg(client_socket, msg)
            print(f"Sent message: {msg['type']}")
        except Exception as e:
            print(f"Error sending message: {e}")
            traceback.print_exc()

    def getPeerId(self, user):
        self.cursor.execute("SELECT id FROM users WHERE username = %s", (user,))
        result = self.cursor.fetchone()
        return result[0] if result else None  # Safely return None if user is not found

    def getAccountByUsername(self, user):
        self.cursor.execute("SELECT * FROM users WHERE username = %s", (user,))
        return self.cursor.fetchone()

    def getIpandPortByPeerID(self, peer_id):
        self.cursor.execute("SELECT ip, port FROM users WHERE id = %s AND status = 1", (peer_id,))
        return self.cursor.fetchone()

        # Update login information

    def updateLogin(self, user, ip, port):
        with self.lock:
            self.cursor.execute("UPDATE users SET ip = %s, port = %s, status = 1 WHERE username = %s", (ip, port, user))
            self.conn.commit()

    def updateUserStatus(self, peer_id, status):
        with self.lock:
            self.cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, peer_id))
            self.conn.commit()

    def insertUser(self, user, passwd, ip, port):
        with self.lock:
            self.cursor.execute("INSERT INTO users (username, password, ip, port, status) VALUES (%s, %s, %s, %s, 0)",
                                (user, passwd, ip, port))
            self.conn.commit()

    def getUserOnline(self):
        with self.lock:
            self.cursor.execute("SELECT * FROM users WHERE status = 1")
            return self.cursor.fetchall()

    def run(self):
        print(f"Tracker server is listening on {HOST}:{PORT}")
        while True:
            try:
                client_socket, addr = self.tracker_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(target=self.handle_peer, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                traceback.print_exc()
            except KeyboardInterrupt:
                print("Program interrupted by user.")
                break


if __name__ == '__main__':
    tracker = TrackerServer()

    tracker.run()
