import socket
import threading
import time
import os
from concurrent.futures import ThreadPoolExecutor

from helper import *
from torrent import *

SERVER_NAME = socket.gethostname()
SERVER = socket.gethostbyname(SERVER_NAME) # default ip of tracker for test
PORT = 5050


class PeerClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_socket = None
        self.server_socket = None # this socket is used to listen to another peer
        """
        peer_socket is used to connect to tracker
        server_socket is used to listen to another peer
        when we connect to tracker, we will use peer_socket
        when we listen to another peer, we will use server_socket because peer_socket is already connected to tracker, 
        it can't be used to send message to tracker but not to listen to another peer
        """
        # self.peer_socket.connect((SERVER, PORT))
        self.user_name = None
        self.peer_id = None
        self.files: Dict[str, MetaInfoFile] = {} # key: file name, value: MetaInfoFile
        self.pieces: Dict[str, Dict[int, bytes]] = {} # key: file name, value: dict of piece index and piece data
        self.magnet_links: Dict[str, str] = {} # key: file name, value: magnet link
        
        
    def connect_to_tracker(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.peer_socket.connect((SERVER, PORT))
                print(f"Connected to tracker at {SERVER}:{PORT}")
                return
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Failed to connect to tracker after multiple attempts.")
                    raise
                
                
    def register_account_with_tracker(self):
        user_name = input("Enter your username to register: ")

        pwd = get_password()
        message = {'type': REGISTER, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port}
        try:
            print("Sending registration request...")
            message = pickle.dumps({'type': REGISTER, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port})

            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            print("Registration request sent. Waiting for response...")
            
            response_data = recv_msg(self.peer_socket)
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)
            
            if response['type'] == REGISTER_SUCCESSFUL:
                print(f"Account {user_name} registered successfully")
                peer_id = response['peer_id']
                if not os.path.exists(f"repo_{user_name}"):
                    os.makedirs(f"repo_{user_name}")
                    print(f"Created directory for user {user_name}. All files will be stored in this directory.")
                self.user_name = user_name
                return peer_id
            else:
                print(f"Account {user_name} registration failed")
                print(response['message'])
                return None
        except ConnectionResetError:
            print("Connection was reset by the tracker. The tracker might have closed unexpectedly.")
            return None
        except Exception as e:
            print(f"An error occurred during registration: {e}")
            return None
        
    def login_account_with_tracker(self):
        user_name = input("Enter your username to login: ")
        pwd = get_password()
        self.user_name = user_name
        message = {'type': LOGIN, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port}
        try:
            print('Sending login request ...')
            message = pickle.dumps({'type': LOGIN, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port})
            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            print("Login request sent. Waiting for response...")
            response_data = recv_msg(self.peer_socket)
            
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)
            
            if response['type'] == LOGIN_SUCCESSFUL:
                print(f"Login successful for user {user_name}")
                self.peer_id = response['peer_id']
                return self.peer_id
            else:
                print(f"Login failed for user {user_name}")
                print(response['message'])
                if response['type'] == LOGIN_WRONG_PASSWORD:
                    print("Wrong password")
                    print("Please try again.")
                    self.login_account_with_tracker()
                    return None
                elif response['type'] == LOGIN_ACC_NOT_EXIST:
                    print("Account does not exist. You need to register first.")
                    self.register_account_with_tracker()
                    return None
                else:
                    print("Internal server error")
                    return None
        except Exception as e:
            print(f"An error occurred during login: {e}")
        pass
    
    def create_torrent(self, file_path: str):
        print("Creating torrent...")
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        info_hash = hashlib.sha1(file_name.encode()).hexdigest()
        pieces = split_file_into_piece(file_path, PIECE_SIZE)

        tracker_address = f"http://{SERVER}:{PORT}"
        metainfo = {
            'file_name': file_name,
            'file_size': file_size,
            'piece_length': PIECE_SIZE,
            'pieces_count': len(pieces),
            'announce': tracker_address
        }
        self.files[file_name] = metainfo
        self.pieces[file_name] = {i: piece for i, piece in enumerate(pieces)}
        # metainfo_path = os.path.join(f"repo_{self.user_name}", f"{file_name}.torrent")
        # with open(metainfo_path, 'wb') as f:
        #     pickle.dump(metainfo, f)
        return metainfo
    
    def register_file_with_tracker(self):
        if self.peer_id is None:
            print("You need to login first.")
            return
        
        file_path = str(input("Enter file name you want to register: "))
        file_path = 'repo_' + self.user_name + '/' + file_path
        metainfo = self.create_torrent(file_path)

        # print(metainfo.encode())
        try:
            print("Sending register file request...")
            
            message = pickle.dumps({'type': REGISTER_FILE, 'metainfo': metainfo, 'peer_id': self.peer_id})
            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            
            print("Register file request sent. Waiting for response...")
            response_data = recv_msg(self.peer_socket)



            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)

            if response['type'] == REGISTER_FILE_SUCCESSFUL:
                print(f"File {file_path} registered successfully")
                magnet_link = response['magnet_link']
                print(f"Magnet link: {magnet_link}")
                with open(os.path.join(f"repo_{self.user_name}", f"{metainfo['file_name']}_magnet"), 'wb') as f:
                    f.write(magnet_link.encode())
            else:
                print(f"File {file_path} registration failed")
                print(response['message'])
        except Exception as e:
            print(f"An error occurred during register file: {e}")
        
        
    def logout_account_with_tracker(self):
        if not self.peer_id:
            print("You need to login first.")
            return
        message = pickle.dumps({'type': LOGOUT, 'peer_id': self.peer_id})
        self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
        print("Logout request sent. Waiting for response...")
        response_data = recv_msg(self.peer_socket)
        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        if response['type'] == LOGOUT_SUCCESSFUL:
            print("Logout successful")
        else:
            print("Logout failed")
            print(response['message'])
            
    def listen_to_another_peer(self):
        while True:
            try:
                if not self.server_socket:
                    print("Server socket is not initialized")
                    break
                another_peer_socket, addr = self.server_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(target=self.handle_peer, 
                                                args=(another_peer_socket, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if isinstance(e, OSError) and e.winerror == 10038:
                    print("Server socket was closed")
                    break
                print(f"Error accepting connection: {e}")
    
    #show all file regis
    def get_list_files_to_download(self):
        if not self.peer_id:
            print("You need to login first.")
            return
        message = pickle.dumps({'type': GET_LIST_FILES_TO_DOWNLOAD})
        self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
        response_data = recv_msg(self.peer_socket)



        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        if response['type'] == GET_LIST_FILES_TO_DOWNLOAD and response['files']:
            return response['files']
        else:
            print("No available files")
    
    def handle_peer(self, another_peer_socket, addr):
        print(f"Handling connection from {addr}")
        while True:
            try:
                print(f"Waiting for data from {addr}")
                data = recv_msg(another_peer_socket)
                if data is None:
                    print(f"Client {addr} disconnected")
                    break
                print(f"Received {len(data)} bytes from {addr}")
                info = pickle.loads(data)
                print(f"Received message from {addr}: {info['type']}")
                if info['type'] == VERIFY_MAGNET_LINK:
                    self.listen_verify_magnet_link_response(another_peer_socket, info)
                elif info['type'] == REQUEST_PIECE:
                    self.listen_request_piece_response(another_peer_socket, info)
                    
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                traceback.print_exc()
                break
        another_peer_socket.close()
        print(f"Connection closed for {addr}")
    
    def listen_request_piece_response(self, another_peer_socket, info):
        file_name = info['file_name']
        piece_index = info['piece_index']
        file_path = f"repo_{self.user_name}/{file_name}"
        pieces = split_file_into_piece_to_send(file_path, PIECE_SIZE, piece_index)
        send_msg(another_peer_socket, {'type': SEND_PIECE, 'pieces': pieces})
        
        
    def send_request_piece(self, ip, port, info):
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_socket.connect((ip, port))
        message = {'type': REQUEST_PIECE, 'file_name': info['file_name'], 'piece_index': info['piece_index']}
        send_msg(temp_socket, message)
        response_data = recv_msg(temp_socket)
        temp_socket.close()
        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        return response['pieces']


    def download_file(self):
        files = self.get_list_files_to_download()
        if not files or (len(files) == 1 and os.path.exists(f"repo_{self.user_name}/{files[0]}")):
            print('No available files')
            return
        else:
            print('All available files:')
            for file in files:
                if not os.path.exists(f"repo_{self.user_name}/{file}"):
                    print(file)

        file_name = input("Enter file name you want to download: ")

        if file_name not in files:
            print("File not found")
            return
        if os.path.exists(f"repo_{self.user_name}/{file_name}"):
            print("File already exists")
            return

        msg = pickle.dumps({'type': REQUEST_FILE, 'file_name': file_name})
        self.peer_socket.sendall(struct.pack('>I', len(msg)) + msg)
        response_data = recv_msg(self.peer_socket)
        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        if response['type'] == SHOW_PEER_HOLD_FILE:
            print(response['metainfo'])
            metainfo = response['metainfo']
            ip_port_list = response['ip_port_list']
            print(f'Found {len(ip_port_list)} peers')

            # Peer verification
            verify_result = []
            magnet_link = create_magnet_link(metainfo, SERVER, PORT)
            for ip, port in ip_port_list:
                res = self.send_verify_magnet_link(magnet_link=magnet_link, ip=ip, port=port, file_name=file_name)
                if res: verify_result.append((ip, port))

            print('List of peers that have the file:')
            for ip, port in verify_result:
                print(f'{ip}:{port}')

            if verify_result:
                piece_per_peer = metainfo['pieces_count'] // len(verify_result)
                remaining_pieces = metainfo['pieces_count'] % len(verify_result)

                num_of_peer_to_download = len(verify_result)
                file_name = metainfo['file_name']
                peer_and_piece_index: Dict[Tuple[str, int], List[int]] = {}
                for j in range(piece_per_peer):
                    for i in range(num_of_peer_to_download):
                        key = (verify_result[i][0], verify_result[i][1])
                        if key not in peer_and_piece_index:
                            peer_and_piece_index[key] = []
                        peer_and_piece_index[key].append(j * num_of_peer_to_download + i)

                for i in range(remaining_pieces):
                    peer_and_piece_index[(verify_result[i][0], verify_result[i][1])].append(
                        piece_per_peer * num_of_peer_to_download + i)

                print(f"Total peers to download from: {len(peer_and_piece_index)}")

                piece_received = []
                total_piece = 0

                # Function to request and collect pieces from a peer
                def fetch_piece(ip, port, list_piece_index):
                    nonlocal total_piece
                    message = {'file_name': file_name, 'piece_index': list_piece_index}
                    response = self.send_request_piece(ip, port, message)


                    for idx, piece in enumerate(response):
                        # The piece is a dictionary containing the actual data in 'piece'
                        actual_piece = piece['piece']

                        # Ensure 'piece' is a bytes-like object, not a dictionary
                        if isinstance(actual_piece, bytes):
                            piece_received.append({'piece_index': list_piece_index[idx], 'piece': actual_piece})
                        else:
                            print(f"Warning: Piece {idx} is not bytes, it's {type(actual_piece)}")

                    total_piece += len(response)
                    print(f"Received {len(response)} pieces from {ip}:{port}")

                # Create a ThreadPoolExecutor to manage parallel downloads
                with ThreadPoolExecutor() as executor:
                    # Submit tasks to the executor for each peer
                    futures = []
                    for ip, port in peer_and_piece_index:
                        list_piece_index = peer_and_piece_index[(ip, port)]
                        futures.append(executor.submit(fetch_piece, ip, port, list_piece_index))

                    # Wait for all tasks to complete
                    for future in futures:
                        future.result()

                # After receiving all pieces, verify and write them to the file
                if total_piece != metainfo['pieces_count']:
                    print(f"Received {total_piece} pieces, but expected {metainfo['pieces_count']} pieces")
                    return

                # Sort the pieces by 'piece_index' to ensure the correct order
                piece_received.sort(key=lambda x: x['piece_index'])

                # Writing the file
                with open(os.path.join(f"repo_{self.user_name}", file_name), 'wb') as f:
                    for piece in piece_received:
                        if isinstance(piece['piece'], bytes):
                            f.write(piece['piece'])  # Write the actual bytes to the file
                        else:
                            print(f"Error: Piece with index {piece['piece_index']} is not bytes.")
                            return  # Exit the function if an invalid piece is encountered

                print(f"Downloaded file {file_name} successfully")

            else:
                print("Failed to verify magnet link for some peers")
        elif response['type'] == SHOW_PEER_HOLD_FILE_FAILED:
            print(response['message'])
        else:
            print("Internal server error")

    def send_verify_magnet_link(self, magnet_link, ip, port, file_name):
        # Create a new temporary socket for this specific peer connection
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Connect to the target peer's server_socket
            temp_socket.connect((ip, port))
            
            # Send the verify magnet link request
            message = {'type': VERIFY_MAGNET_LINK, 'magnet_link': magnet_link, 'file_name': file_name}
            send_msg(temp_socket, message)
            
            # Receive the response
            response_data = recv_msg(temp_socket)
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            
            response = pickle.loads(response_data)
            return response['type'] == VERIFY_MAGNET_LINK_SUCCESSFUL
        except Exception as e:
            print(f"Error verifying magnet link with peer {ip}:{port}: {e}")
            return False
        finally:
            temp_socket.close()  # Always close the temporary socket

    def listen_verify_magnet_link_response(self, another_peer_socket, info):
        try:
            # Receive the verification request
            magnet_link = info['magnet_link']
            file_name = info['file_name']
            print(f'Received magnet link from {magnet_link}')
            # Verify the magnet link
            with open(f"repo_{self.user_name}/{file_name}_magnet", 'rb') as f:
                magnet_link_to_verify = f.read().decode('utf-8')
                
            print(f'Magnet link to verify: {magnet_link_to_verify}')
            
            if magnet_link == magnet_link_to_verify:
                print(f"Verified magnet link for {file_name}")
                response = {'type': VERIFY_MAGNET_LINK_SUCCESSFUL}
            else:
                print(f"Failed to verify magnet link for {file_name}")
                response = {'type': VERIFY_MAGNET_LINK_FAILED}
            
            # Send the verification response
            send_msg(another_peer_socket, response)
        except Exception as e:
            print(f"Error handling magnet link verification: {e}")
            error_response = pickle.dumps({'type': 'ERROR', 'message': str(e)})
            send_msg(another_peer_socket, error_response)
    
    def ininitialize_server_socket(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(5) # assume that we only listen from 5 peers at the same time
            print(f"Listening for incoming connections on {self.ip}:{self.port}")
        except Exception as e:
            print(f"Error initializing server socket: {e}")
            traceback.print_exc()
    def clean_up(self):
        try:
            if self.peer_socket:
                self.peer_socket.close()
            if self.server_socket:
                self.server_socket.close()
        except Exception as e:
            print(f"Error cleaning up: {e}")
            traceback.print_exc()
            
    def peer_service(self):
        try:
        # Start listener thread
            self.ininitialize_server_socket()
            self.listen_thread = threading.Thread(target=self.listen_to_another_peer)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            while True:
                print("\n--- Peer Client Menu ---")
                print("1. Register a file")
                print("2. Download a file")
                print("3. Exit")
                
                choice = input("Enter your choice (1-3): ")
                
                if choice == '1':
                    self.register_file_with_tracker()

                elif choice == '2':
                    self.download_file()
                elif choice == '3':
                    self.logout_account_with_tracker()
                    self.clean_up()
                    print("Exiting...")
                    break
                else:
                    print("Invalid choice. Please try again.")
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback.print_exc()
    
    
if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    peer_port = int(input("Enter peer port: "))
    peer = None
    try:
        peer = PeerClient(local_ip, peer_port)
        peer.connect_to_tracker()
        print('\nYou can register a new account or login to your account')
        print('1. Register a new account')
        print('2. Login to your account')
        while True:
            choice = int(input('Enter your choice: '))
            if choice == 1:
                peer_id = peer.register_account_with_tracker()
                if peer_id:
                    print(f'Your peer id is {peer_id}')
            elif choice == 2:
                peer_id = peer.login_account_with_tracker()
                if peer_id:
                    print(f'Your peer id is {peer_id}')
                    break
            else:
                print('Invalid choice')
        peer.peer_service()
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        if peer and peer.peer_socket:
            peer.peer_socket.close()
        print("Closing connection and exiting program.")
        input("Press Enter to exit...")
