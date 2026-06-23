# Libraries
import logging
from logging.handlers import RotatingFileHandler
import socket
import paramiko
import threading
import uuid
from send_to_api import send_to_api


# Constants
logging_format = logging.Formatter('%(message)s')
SSH_BANNER = "SSH-2.0-OpenSSH_7.9p1"

host_key = paramiko.RSAKey(filename='server.key')

# Loggers
funnel_logger = logging.getLogger('funnelLogger')
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler('audits.log', maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

creds_logger = logging.getLogger('credsLogger')
creds_logger.setLevel(logging.INFO)
creds_handler = RotatingFileHandler('cmd_audits.log', maxBytes=2000, backupCount=5)
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(creds_handler)


# Emulated Shell
def emulated_shell(session_id: str, channel, client_ip: str):
    channel.send(b'corporate-jumpbox2$ ')
    command = b""

    while True:
        char = channel.recv(1)
        if not char:
            break

        channel.send(char)
        command += char

        if char == b'\r':
            cmd = command.strip()
            cmd_str = cmd.decode('utf-8', errors='replace')

            if cmd == b'exit':
                channel.send(b'\n Goodbye!\n')
                channel.close()
                break

            elif cmd == b'pwd':
                response = b'\n/user/local\r\n'
            elif cmd == b'whoami':
                response = b'\ncorpuser1\r\n'
            elif cmd == b'ls':
                response = b'\nOpenMe.conf\r\n'
            elif cmd == b'cat OpenMe.conf':
                response = b'\nThis is a simple honeypot.\r\n'
            else:
                response = b'\n' + cmd + b'\r\n'

            # Logging & API
            creds_logger.info(f"SSH Command '{cmd_str}' executed by {client_ip}")
            try:
                send_to_api({
                    "event": "command",
                    "protocol": "SSH",
                    "ip": client_ip,
                    "command": cmd_str,
                    "session_id": session_id
                })
            except Exception as e:
                logging.error(f"Failed to send command to API: {e}")

            channel.send(response)
            channel.send(b'corporate-jumpbox2$ ')
            command = b""


# SSH Server Class
class SSHServer(paramiko.ServerInterface):          
    def __init__(self, client_ip, input_username=None, input_password=None):
        self.event = threading.Event()
        self.session_id = str(uuid.uuid4())
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password

    def check_channel_request(self, kind: str, chanid: int) -> int:
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED

    def get_allowed_auth(self):
        return "password"

    def check_auth_password(self, username, password):
        send_to_api({
            "event": "login",
            "protocol": "SSH",
            "ip": self.client_ip,
            "username": username,
            "password": password,
            "session_id": self.session_id
        })

        funnel_logger.info(f"SSH Login Attempt - IP: {self.client_ip} | Username: {username} | Password: {password}")
        creds_logger.info(f"SSH Login Attempt - IP: {self.client_ip} | Username: {username} | Password: {password}")

        if self.input_username and self.input_password:
            return paramiko.AUTH_SUCCESSFUL if (username == self.input_username and password == self.input_password) else paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True


def client_handle(client, addr, username=None, password=None):
    client_ip = addr[0]
    print(f"[+] {client_ip} connected to honeypot.")

    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        ssh_server = SSHServer(client_ip=client_ip, input_username=username, input_password=password)

        transport.add_server_key(host_key)
        transport.start_server(server=ssh_server)

        channel = transport.accept(120)
        if channel is None:
            print("No channel opened.")
            return

        channel.send(b"Welcome to the corporate jumpbox. All activities are monitored and logged.\n")
        emulated_shell(ssh_server.session_id, channel, client_ip)

    except Exception as e:
        print(f"Error handling client {client_ip}: {e}")
    finally:
        try:
            transport.close()
        except:
            pass
        client.close()


def honeypot(address='0.0.0.0', port=2223, username=None, password=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((address, port))
    sock.listen(100)

    print(f"[*] SSH Honeypot listening on {address}:{port}")

    while True:
        try:
            client, addr = sock.accept()
            thread = threading.Thread(target=client_handle, args=(client, addr, username, password))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Accept error: {e}")


if __name__ == "__main__":
    honeypot('0.0.0.0', 2223)