#!/usr/bin/env python3
import sys
import os
import time
import threading
import random
import socket
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh_bot import SSHBot, check_port

BANNER = """
  ╔══════════════════════════════════════════════════╗
  ║            THREATOPS — BOT NETWORK              ║
  ║     Multi-IP Attack Simulation Framework        ║
  ╚══════════════════════════════════════════════════╝
"""

ATTACK_MODES = {
    '1': ('ssh_direct', 'SSH Direct — real connections to honeypot'),
    '2': ('api_inject', 'API Inject — flood dashboard with varied IPs'),
}

def clear():
    os.system('clear' if os.name == 'posix' else 'cls')

def preflight_check(ip, port):
    print(f"  [?] Checking {ip}:{port}... ", end='', flush=True)
    ok = check_port(ip, port, timeout=3)
    print('OPEN' if ok else 'CLOSED')
    return ok

def api_injector(api_url, bot_id, results):
    users = ['root', 'admin', 'ubuntu', 'postgres', 'deploy', 'pi', 'oracle', 'git', 'jenkins', 'test']
    passwords = ['admin', 'root', '123456', 'password', 'P@ssw0rd', 'changeme', 'letmein', 'Welcome1']
    commands = ['whoami', 'id', 'ls -la', 'cat /etc/passwd', 'uname -a', 'pwd', 'ps aux', 'netstat -tlnp']
    ips = [
        '185.220.101.1', '91.121.87.45', '45.33.32.156', '103.235.46.9',
        '167.99.89.105', '203.0.113.42', '198.51.100.7', '185.130.5.10',
        '78.46.89.22', '144.76.200.15', '5.9.100.200', '88.99.150.75',
        '95.216.0.150', '116.202.120.30', '49.12.200.45', '138.201.80.90',
        '23.88.120.60', '192.168.1.50', '10.10.10.25', '172.16.0.50',
    ]
    login_count = random.randint(1, 3)
    for _ in range(login_count):
        ip = random.choice(ips)
        user = random.choice(users)
        pwd = random.choice(passwords)
        try:
            requests.post(f"{api_url}/api/event", json={
                "event": "login", "protocol": "SSH",
                "ip": ip, "username": user, "password": pwd,
                "session_id": f"sim-{random.randint(1000,9999)}"
            }, timeout=2)
            with results['lock']:
                results['logins'] += 1
        except:
            pass
        time.sleep(random.uniform(0.05, 0.15))
    cmd_count = random.randint(2, 5)
    for _ in range(cmd_count):
        ip = random.choice(ips)
        cmd = random.choice(commands)
        try:
            requests.post(f"{api_url}/api/event", json={
                "event": "command", "protocol": "SSH",
                "ip": ip, "command": cmd,
                "session_id": f"sim-{random.randint(1000,9999)}"
            }, timeout=2)
            with results['lock']:
                results['cmds'] += 1
        except:
            pass
        time.sleep(random.uniform(0.05, 0.15))

def main():
    clear()
    print(BANNER)

    target_ip = input("  Target IP [{default}]: ".format(default='127.0.0.1')).strip() or '127.0.0.1'

    print("\n  ── ATTACK MODE ──")
    for k, v in ATTACK_MODES.items():
        print(f"  [{k}] {v[1]}")

    mode = input("\n  Select mode [{default}]: ".format(default='1')).strip() or '1'
    if mode not in ATTACK_MODES:
        print("  [!] Invalid. Defaulting to SSH Direct.")
        mode = '1'

    mode_key, mode_desc = ATTACK_MODES[mode]

    port_input = 2223
    if mode_key == 'ssh_direct':
        port_input = input("  Target Port [{default}]: ".format(default='2223')).strip()
        port_input = int(port_input) if port_input else 2223
        clear()
        print(BANNER)
        print(f"  ── PRE-FLIGHT CHECK ──")
        alive = preflight_check(target_ip, port_input)
        if not alive:
            print(f"\n  [!] Port {port_input} is CLOSED on {target_ip}.")
            print("  [!] Make sure the honeypot is running:")
            print(f"      python3 ssh_honeypot.py &\n")
            retry = input("  Retry? [Y/n]: ").strip().lower()
            if retry != 'n':
                alive = preflight_check(target_ip, port_input)
                if not alive:
                    print("\n  [!] Still unreachable. Try API Inject mode instead.\n")
                    input("  Press Enter to continue anyway, or Ctrl+C to abort...")
        print()

    num_input = input("  Number of bot instances [{default}]: ".format(default='10')).strip()
    num_bots = int(num_input) if num_input else 10

    print(f"\n  [+] Launching {num_bots} bots in [{mode_key.upper()}] mode...")
    if mode_key == 'ssh_direct':
        print(f"  [+] Target: {target_ip}:{port_input}")
    print()
    time.sleep(1)

    results = {'logins': 0, 'cmds': 0, 'errors': 0, 'lock': threading.Lock()}
    bot_threads = []

    if mode_key == 'ssh_direct':
        class TrackedBot(SSHBot):
            def run(self):
                super().run()
                with results['lock']:
                    results['logins'] += self.logins
                    results['cmds'] += self.commands_run
                    if self.error:
                        results['errors'] += 1

        for i in range(num_bots):
            bot = TrackedBot(target_ip, port_input, bot_id=i + 1)
            bot.start()
            bot_threads.append(bot)
            time.sleep(random.uniform(0.02, 0.08))
    else:
        api_url = f"http://{target_ip}:8000"
        for i in range(num_bots):
            t = threading.Thread(
                target=api_injector,
                args=(api_url, i + 1, results),
                daemon=True
            )
            t.start()
            bot_threads.append(t)
            time.sleep(random.uniform(0.05, 0.15))

    try:
        while any(t.is_alive() for t in bot_threads):
            running = sum(1 for t in bot_threads if t.is_alive())
            clear()
            print(BANNER)
            print(f"  Target: {target_ip}  |  Mode: {mode_key.upper()}")
            print(f"\n  Active:  {running}/{num_bots}")
            print(f"  Logins:  {results['logins']}")
            print(f"  Commands: {results['cmds']}")
            if results['errors'] > 0:
                print(f"  Errors:  {results['errors']}")
            print("  " + "─" * 48)
            lines = 0
            for t in bot_threads:
                if lines >= 12:
                    print(f"  ... and {num_bots - 12} more")
                    break
                alive = t.is_alive() if hasattr(t, 'is_alive') else False
                status = '●' if alive else '○'
                label = 'ACTIVE' if alive else 'DONE'
                bid = bot_threads.index(t) + 1
                print(f"  Bot #{bid:<3} {status} {label}")
                lines += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n  [!] Interrupted. Waiting for active bots to finish...")

    for t in bot_threads:
        t.join(timeout=3)

    clear()
    print(BANNER)
    print(f"  ── RESULTS ──")
    print(f"  Bots:        {num_bots}")
    print(f"  Logins:      {results['logins']}")
    print(f"  Commands:    {results['cmds']}")
    if results['errors']:
        print(f"  Errors:      {results['errors']}")
    print(f"\n  Dashboard: http://{target_ip}:8000")
    if mode_key == 'ssh_direct':
        print(f"  Honeypot:  {target_ip}:{port_input}")
    print("\n  Done.\n")

if __name__ == '__main__':
    main()
