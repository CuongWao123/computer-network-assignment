# BitTorrent P2P File Sharing System

This project simulates a BitTorrent-like peer-to-peer (P2P) file-sharing system. It includes a tracker and multiple peers that can register and download files by sharing pieces in a multi-threaded environment.

## Features
- **Tracker**: Manages file registration and keeps track of which peers have specific file pieces.
- **Peers**: Can log in/register, share files by splitting them into pieces, and download files from multiple peers simultaneously.
- **Multi-threading**: Enhances performance for file registration and downloading by handling multiple connections in parallel.

## Prerequisites
Make sure you have Python installed and the following libraries available:
- `socket`
- `pickle`
- `threading`
- `os`

Most of these are part of Python’s standard library. To ensure everything is set up, use the following command:
```bash
pip install socket pickle threading os
```
**Database Configuration Guide**

Make sure to install PostgreSQL and configure it correctly to work with the provided code:

```python
self.conn = psycopg2.connect(
    dbname="socket",  # Reaplace with your database name
    user="postgres",
    password="cuongdola231",# Replace with your user and passsword
    host="",  # Replace with "localhost" or your database server's IP
    port="5432"  # Default PostgreSQL port
)

```
### Usage Instructions
**Step 1: Start the Tracker**

The tracker is essential for managing the list of shared files and the peers holding file pieces. Start it first:
```bash
python tracker.py
```
**Step 2: Start Multiple Peers**

Each peer acts as a node in the network. Open multiple terminal windows and run:
```bash
python peer.py
```
You can start as many peers as you want to simulate a real P2P environment.
**Step 3: Using the Peer Interface**

Once a peer is started, follow the on-screen prompts to interact with the system:

    Login or Register: Sign into the file-sharing system or create a new account.
    After Logging In, you have three options:
        Register File:
            Register a file with the tracker.
            The file is split into pieces and shared among peers using multi-threading.
        Download File:
            Request a file from the network.
            The peer retrieves all file pieces from different peers and assembles them using multi-threading.
        Exit: Leave the file-sharing system.

## How It Works

    Tracker: Maintains a registry of files and knows which peers hold which pieces.
    Peers: Use the tracker to find files and communicate directly with other peers to share pieces.
    File Splitting: Files are divided into pieces for distribution. This allows efficient, parallel downloads.
    Multi-threading: Optimizes file registration and downloading by handling multiple operations simultaneously.

