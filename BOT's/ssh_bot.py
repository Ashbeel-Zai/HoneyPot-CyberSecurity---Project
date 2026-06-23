import paramiko
import random
import time
import threading
import socket

#these is an Script to simulate RealTIme SSH login's and attacks

ATTACKER_IPS = [
    '185.220.101.1', '91.121.87.45', '45.33.32.156', '103.235.46.9',
    '167.99.89.105', '192.168.1.200', '10.10.10.50', '172.16.0.100',
    '203.0.113.42', '198.51.100.7', '185.130.5.10', '78.46.89.22',
    '144.76.200.15', '5.9.100.200', '88.99.150.75', '95.216.0.150',
    '116.202.120.30', '49.12.200.45', '138.201.80.90', '23.88.120.60',
]

USERNAMES = [
    'root', 'admin', 'user', 'test', 'ubuntu', 'pi', 'deploy',
    'vagrant', 'centos', 'oracle', 'postgres', 'mysql', 'gitlab',
    'jenkins', 'docker', 'nginx', 'www-data', 'nobody', 'backup',
    'support', 'info', 'sales', 'manager', 'admin1', 'administrator',
    'demo', 'guest', 'temp', 'dev', 'webmaster', 'sysadmin',
    'root2', 'adm', 'sa', 'master', 'sshuser',
]

PASSWORDS = [
    'admin', 'root', '123456', 'password', 'admin123', 'root123',
    'toor', 'admin1234', 'pass123', 'changeme', 'letmein', '1234',
    'P@ssw0rd', 'qwerty', '12345', 'Passw0rd', 'admin@123', 'root@123',
    'Welcome1', '1q2w3e4r', 'test123', 'ubuntu', 'deploy123',
    'cisco', 'router', 'default', 'secret', 'Pa$$w0rd',
]

COMMANDS = [
    'whoami', 'id', 'uname -a', 'pwd', 'ls -la',
    'cat /etc/passwd', 'cat /etc/shadow', 'cat /etc/hostname',
    'df -h', 'free -m', 'top -b -n1 | head -20', 'ps aux',
    'netstat -tlnp', 'ss -tlnp', 'ip addr', 'ifconfig',
    'wget --version', 'curl --version', 'python3 --version', 'python --version',
    'which nc', 'which python3', 'which perl', 'which bash',
    'ls /home/', 'ls /root/', 'ls /tmp/', 'ls /var/log/',
    'cat /etc/os-release', 'hostname', 'uptime', 'last -5',
    'env', 'set', 'echo $PATH', 'ls /etc/ssh/',
    'cat /etc/ssh/sshd_config | head -30',
    'systemctl status sshd 2>/dev/null | head -10',
    'iptables -L -n 2>/dev/null | head -20',
    'find / -perm -4000 2>/dev/null | head -10',
    'cat ~/.bash_history 2>/dev/null | tail -10',
    'ls -la /etc/ | head -20',
    'cat /etc/crontab 2>/dev/null',
    'arp -a 2>/dev/null', 'route -n 2>/dev/null',
    'dig google.com 2>/dev/null | head -10',
]

MAX_RETRIES = 2
RETRY_DELAY = 1.5

def check_port(ip, port, timeout=3):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        r = s.connect_ex((ip, port))
        s.close()
        return r == 0
    except:
        return False

class SSHBot(threading.Thread):
    def __init__(self, target_ip, target_port=2223, bot_id=0):
        super().__init__()
        self.target_ip = target_ip
        self.target_port = target_port
        self.bot_id = bot_id
        self.src_ip = random.choice(ATTACKER_IPS)
        self.daemon = True
        self.commands_run = 0
        self.logins = 0
        self.error = None

    def run(self):
        for attempt in range(1, MAX_RETRIES + 2):
            try:
                self._attempt_login()
                return
            except (socket.timeout, socket.error, OSError) as e:
                self.error = str(e)
                if attempt <= MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    print(f"  [Bot #{self.bot_id}] -down ({self.src_ip} → {self.target_ip}:{self.target_port})")
            except paramiko.AuthenticationException:
                return
            except Exception as e:
                self.error = str(e)
                if attempt > MAX_RETRIES:
                    print(f"  [Bot #{self.bot_id}] -error ({self.src_ip}): {e}")
                    return
                time.sleep(RETRY_DELAY)

    def _attempt_login(self):
        username = random.choice(USERNAMES)
        password = random.choice(PASSWORDS)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.target_ip, port=self.target_port,
            username=username, password=password,
            banner_timeout=8, auth_timeout=8, timeout=12,
            allow_agent=False, look_for_keys=False
        )
        self.logins += 1
        print(f"  [Bot #{self.bot_id}] +login ({self.src_ip}) {username}:{password}")
        self._run_commands(client)
        client.close()

    def _run_commands(self, client):
        n_cmds = random.randint(2, 6)
        cmds = random.sample(COMMANDS, min(n_cmds, len(COMMANDS)))
        try:
            channel = client.invoke_shell()
            time.sleep(random.uniform(0.3, 0.8))
            if channel.recv_ready():
                channel.recv(4096)
            for cmd in cmds:
                time.sleep(random.uniform(0.2, 0.8))
                channel.send(cmd + '\r')
                time.sleep(random.uniform(0.3, 0.8))
                if channel.recv_ready():
                    channel.recv(8192)
                self.commands_run += 1
            channel.send('exit\r')
            channel.close()
        except:
            pass
        print(f"  [Bot #{self.bot_id}] done ({self.commands_run} cmds)")
