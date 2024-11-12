from typing import Dict, Set, List, Tuple
import bencodepy
import traceback
import struct
import pickle

HEADER = 10
QUEUE_SIZE = 5
PIECE_SIZE = 512 * 1024 
FORMAT = 'utf-8'

DISCONNECT_MSG = '!DISCONNECT'
REGISTER = 'register'
REGISTER_FAILED = 'register_failed'
REGISTER_SUCCESSFUL = 'register_successful'
REQUEST = 'request_file'
LOGIN = 'login'
LOGIN_SUCCESSFUL = 'login_successful'
LOGIN_FAILED = 'login_failed'
LOGIN_WRONG_PASSWORD = 'login_wrong_password'
LOGOUT = 'logout'
LOGOUT_SUCCESSFUL = 'logout_successful'
LOGIN_ACC_NOT_EXIST = 'login_acc_not_exist'
REGISTER_FILE = 'register_file'
REGISTER_FILE_SUCCESSFUL = 'register_file_successful'
REGISTER_FILE_FAILED = 'register_file_failed'
GET_LIST_FILES_TO_DOWNLOAD = 'get_list_files_to_download'
DOWNLOAD_FILE = 'download_file'
REQUEST_FILE = 'request_file'
SHOW_PEER_HOLD_FILE = 'show_peer_hold_file'
SHOW_PEER_HOLD_FILE_FAILED = 'show_peer_hold_file_failed'
VERIFY_MAGNET_LINK = 'verify_magnet_link'
VERIFY_MAGNET_LINK_SUCCESSFUL = 'verify_magnet_link_successful'
VERIFY_MAGNET_LINK_FAILED = 'verify_magnet_link_failed'
REQUEST_PIECE = 'request_piece'
SEND_PIECE = 'send_piece'
VERIFY_FILE = 'check_file_in_peer'

