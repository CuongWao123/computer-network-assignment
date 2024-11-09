import struct
import pickle
import bencodepy
import maskpass
import hashlib
def recv_msg(sock):
    # Receive the size of the message first
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Now receive the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def send_msg(sock, msg):
    msg = pickle.dumps(msg)
    sock.sendall(struct.pack('>I', len(msg)) + msg)
    
def command_line_interface():
    print("Welcome to the command line interface")
    while True:
        command = input(">>> ")
        if command == "exit":
            break
        else:
            print(f"Unknown command: {command}")

def create_magnet_link(metainfo, HOST, PORT):
        info_hash = bencodepy.encode(metainfo).hex()
        file_name = metainfo['file_name']
        file_size = metainfo['file_size']
        
        
        magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={file_name}&xl={file_size}"
        
        # Add tracker URL to the magnet link
        tracker_url = f"http://{HOST}:{PORT}/announce"
        magnet_link += f"&tr={tracker_url}" 
        
        return magnet_link

# function to ensure pwd hidden
def get_password():
    while True:
        password = input("Enter your password: ")
        confirm_password = input("Confirm your password: ")

        if password == confirm_password:
            print("Password confirmed.")
            return password
        else:
            print("Password does not match. Try again.")

# hash function to hash piece of file into hexa code
def sha1_hash(data):
    sha1 = hashlib.sha1()
    sha1.update(data)
    return sha1.hexdigest()

# split function to split file into equal piece and return list of their hash code
def split_file_into_piece(path,piece_size):
    pieces = []
    with open(path, 'rb') as f:
        while True:
            piece = f.read(piece_size)
            if not piece:
                break
            pieces.append(sha1_hash(piece))


    return pieces

def split_file_into_piece_to_send(path, piece_size, index):
    pieces = []
    with open(path, 'rb') as f:
        idx = 0
        while True:
            piece = f.read(piece_size)
            if not piece:
                break
            temp = {'piece': piece, 'id': idx}
            pieces.append(temp)
            idx += 1
    pieces = [piece for piece in pieces if piece['id'] in index]
    return pieces