<div align="center">

# 🍯 THREATOPS — Honeypot + Global Threat Intelligence Dashboard

### *A Multi-Protocol Honeypot Framework with Real-Time Attack Visualization*

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0%2B-black?style=flat&logo=flask)
![Paramiko](https://img.shields.io/badge/Paramiko-3.0%2B-green?style=flat)
![Three.js](https://img.shields.io/badge/Globe-3D_Globe-ff69b4?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat)

**Author: [Ashbeel-Zai](https://github.com/Ashbeel-Zai)**

---

</div>

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [SSH Key Setup](#-ssh-key-setup)
- [How to Run](#-how-to-run)
- [Bot Network (Attack Simulation)](#-bot-network-attack-simulation)
- [API Endpoints](#-api-endpoints)
- [Dashboards](#-dashboards)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧠 Overview

**THREATOPS** is a comprehensive honeypot framework that deploys **SSH and HTTP** honeypots to capture attacker behavior, logs credentials, commands, and geolocates attacks in real-time. Captured data is visualized through a **3D interactive globe dashboard** with live threat intelligence, attack arcs, country rankings, and alerting.

> **Use Case:** Deception-based threat intelligence, attacker profiling, credential harvesting analysis, and cybersecurity research.

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Attacker / Bot Network                   │
└──────────┬──────────────────────────────┬──────────────────┘
           │ SSH (2223)                   │ HTTP (5000)
           ▼                              ▼
┌───────────────────┐        ┌─────────────────────────┐
│  SSH Honeypot     │        │  Web Honeypot (Flask)   │
│  (ssh_honeypot.py)│        │  (web_honeypot.py)      │
│  • Fake jumpbox   │        │  • Fake admin login     │
│  • Emulated shell │        │  • Captures creds       │
│  • Logs commands  │        │                         │
└────────┬──────────┘        └───────────┬─────────────┘
         │                               │
         └───────────┬───────────────────┘
                     ▼
         ┌──────────────────────┐
         │   send_to_api.py     │
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────────────────┐
         │     DataCatcher_API.py           │
         │     (Flask — Port 8000)          │
         │  • Stores events in SQLite      │
         │  • Geolocates IPs (ip-api.com)  │
         │  • Serves dashboard data        │
         └──────────┬───────────────────┬──┘
                    ▼                   ▼
         ┌──────────────────────┐  ┌──────────────────────────┐
         │ ThreatOps Dashboard  │  │ Aesthetic Globe (decor)  │
         │ (Data Visualization) │  │ (No data — just cool)    │
         │ threatops_dashboard  │  │ glob.html                │
         │ .html                │  │ Inspired by Kaspersky    │
         └──────────────────────┘  │ CyberMap                 │
                                   └──────────────────────────┘
```

---

## ✨ Features

### 🛡 Honeypots
| Protocol | Port (Default) | Capabilities |
|----------|---------------|--------------|
| **SSH** | `2223` | Emulated corporate jumpbox shell, credential logging, command logging, real Paramiko server |
| **HTTP** | `5000` | Fake admin login portal, credential harvesting, phishing-style interface |

### 🌐 Threat Intelligence
- **Real-time geolocation** — Every attacker IP is resolved via `ip-api.com`
- **Attack vectors** — Login attempts & command execution tracked separately
- **Threat scoring** — Dynamic threat level (LOW / MEDIUM / HIGH / CRITICAL) based on events/min
- **Live feed** — Scrollable table of incoming attacks

### 🌍 3D Globe Visualization (`/advanced-dashboard`)
- **Interactive 3D globe** — Rotatable, zoomable Earth with Three.js
- **Attack arcs** — Bezier-curved rays from attacker locations to server
- **Collision rings** — Animated radar rings at attack origins
- **Point markers** — Color-coded attack hotspots with country labels
- **Threat intensity meter** — Real-time bar showing events per second
- **Service monitoring** — SSH/HTTP service health indicators

### 📊 Statistics Panel
- **Live counters** — Total events, unique IPs, active sessions, today's events
- **Sparkline charts** — 24-hour event trend visualization
- **Top 15 countries** — Ranked with flag emoji and progress bars
- **Top usernames/IPs/commands** — Breakdown tables in the overlay
- **Event distribution** — Login vs Command pie/bar breakdown

### 🤖 Bot Network (Attack Simulation)
- **SSH Direct mode** — Real Paramiko connections to the honeypot
- **API Inject mode** — HTTP POST flood with randomized IPs
- **20+ attacker IPs** — Realistic randomized source addresses
- **30+ usernames / 20+ passwords** — Common brute-force dictionary
- **50+ reconnaissance commands** — Real attacker TTPs (whoami, id, cat /etc/passwd, etc.)

---

## 📁 Project Structure

```
HONYPOT+DASHBOARD/
├── honeypy.py                  # Main launcher (CLI entry point)
├── ssh_honeypot.py             # SSH honeypot implementation
├── web_honeypot.py             # HTTP web honeypot (Flask app)
├── DataCatcher_API.py          # Central API + Dashboard server
├── send_to_api.py              # HTTP client to push events to API
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
│
├── BOT's/
│   ├── Master_bot.py           # Bot network controller
│   └── ssh_bot.py              # SSH bot simulation engine
│
├── templates/
│   ├── glob.html               # Purely aesthetic 3D globe (no data, just visual flair — inspired by Kaspersky CyberMap)
│   ├── threatops_dashboard.html # Advanced threat intelligence dashboard (1290 lines)
│   └── web_login.html          # Fake admin login page
│
├── static/
│   ├── css/
│   │   └── dashboard.css       # Dashboard styles (276 lines)
│   └── js/
│       └── dashboard.js        # Dashboard logic (665 lines)
│
└── instance/
    └── honeypot.db             # SQLite database (auto-created)
```

---

## 🔧 Installation

### Prerequisites
- Python 3.8+
- pip
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/Ashbeel-Zai/HoneyPot-CyberSecurity---Project.git
cd "HoneyPot-CyberSecurity---Project"
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# OR
venv\Scripts\activate      # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Dependencies:**
> - `flask>=3.0` — Web framework for API and web honeypot
> - `flask-sqlalchemy>=3.0` — ORM for SQLite database
> - `paramiko>=3.0` — SSH protocol implementation
> - `requests>=2.0` — HTTP client for API calls

---

## 🔑 SSH Key Setup

The SSH honeypot requires an **RSA host key** (`server.key`) to establish SSH connections. Without this, the honeypot will crash on startup.

### Generate the SSH Host Key

```bash
# Method 1: Using ssh-keygen (recommended)
ssh-keygen -t rsa -b 2048 -f server.key -N ""
```

> This creates `server.key` (private key) and `server.key.pub` (public key).  
> Only `server.key` is needed — place it in the project root directory.

### Method 2: Using Python (Paramiko)

```python
import paramiko

key = paramiko.RSAKey.generate(2048)
key.write_private_key_file("server.key")
print("✅ server.key generated successfully")
```

```bash
# Run the script
python3 -c "
import paramiko
key = paramiko.RSAKey.generate(2048)
key.write_private_key_file('server.key')
print('✅ server.key generated')
"
```

### Method 3: Using OpenSSL

```bash
openssl genpkey -algorithm RSA -out server.key -pkeyopt rsa_keygen_bits:2048
```

### Verify the Key

```bash
ls -la server.key
# Expected output: -rw------- 1 user user 1679 ... server.key
```

> **Note:** `server.key` is in `.gitignore` — it will not be committed.

---

## 🚀 How to Run

### 1. Start the API / Dashboard Server

```bash
python3 DataCatcher_API.py
```

> The API server starts on **http://0.0.0.0:8000**

### 2. Start SSH Honeypot

```bash
python3 honeypy.py --ssh --address 0.0.0.0 --port 2223
```

Or with custom credentials (only matching creds get shell access):

```bash
python3 honeypy.py --ssh --address 0.0.0.0 --port 2223 --username admin --password secret
```

### 3. Start HTTP Web Honeypot

```bash
python3 honeypy.py --http --port 5000 --username admin --password admin
```

### 4. Access the Dashboards

| URL | Description |
|-----|-------------|
| `http://localhost:8000/` | Aesthetic 3D globe (decorative, no data — inspired by Kaspersky CyberMap) |
| `http://localhost:8000/advanced-dashboard` | **Full ThreatOps dashboard** 🚀 |
| `http://localhost:8000/old-dashboard` | Redirect (placeholder) |

---

## 🤖 Bot Network (Attack Simulation)

Test the honeypot with realistic attack traffic.

### Run the Bot Network

```bash
cd "HONYPOT+DASHBOARD/BOT's"
python3 Master_bot.py
```

### Interactive Setup

```
1. Target IP [127.0.0.1]:          # Press Enter for localhost
2. Attack Mode:
   [1] SSH Direct (real SSH connections)
   [2] API Inject (HTTP flood to dashboard)
3. Bot instances [10]:              # Number of parallel bots
```

### SSH Direct Mode
- Opens real Paramiko SSH sessions to the honeypot
- Random credentials from built-in dictionaries
- Executes reconnaissance commands in the emulated shell
- All traffic appears in the dashboard in real-time

### API Inject Mode
- Sends POST requests directly to the API
- Uses 20+ randomized source IPs (global distribution)
- Mix of login and command events
- Faster than SSH mode (no TCP handshake overhead)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| **POST** | `/api/event` | Ingest a new event (login/command) |
| **GET** | `/api/events` | List last 100 raw events |
| **GET** | `/api/dashboard/stats` | Aggregate statistics |
| **GET** | `/api/dashboard/timeline` | 24-hour hourly event counts |
| **GET** | `/api/dashboard/top-ips` | Top 10 attacking IPs |
| **GET** | `/api/dashboard/event-types` | Login vs Command breakdown |
| **GET** | `/api/dashboard/top-users` | Top 10 usernames attempted |
| **GET** | `/api/dashboard/top-commands` | Top 15 commands executed |
| **GET** | `/api/dashboard/recent-events` | Last N events (default 30) |
| **GET** | `/api/dashboard/threat-level` | Current threat severity |
| **GET** | `/api/dashboard/attack-locations` | Geo-mapped attack coordinates |
| **GET** | `/api/dashboard/live-attacks` | Live attack feed |
| **GET** | `/api/dashboard/heatmap` | Heatmap intensity data |
| **GET** | `/api/dashboard/country-stats` | Per-country breakdown |

### Ingesting an Event

```bash
curl -X POST http://localhost:8000/api/event \
  -H "Content-Type: application/json" \
  -d '{
    "event": "login",
    "protocol": "SSH",
    "ip": "185.220.101.1",
    "username": "root",
    "password": "admin123",
    "session_id": "abc-123"
  }'
```

---

## 📊 Dashboards

### 🚀 ThreatOps Advanced Dashboard (`/advanced-dashboard`)

A full-screen, cyberpunk-styled threat intelligence command center featuring:

- **3D Globe** with auto-rotation, attack arcs, and collision rings
- **Threat Overview** cards: Total Events, Unique IPs, Active Sessions, Today's Events
- **Attack Intensity Meter** — real-time events/second gauge
- **Live Feed** — scrolling list of incoming attacks with country flags & timestamps
- **Top Countries** — ranked leaderboard with progress bars
- **Alerts Panel** — dynamic threat alerts (critical waves, geographic spread)
- **Service Monitor** — SSH/HTTP service health status
- **Statistics Overlay** — deep-dive tables for users, IPs, commands, countries, events
- **Ticker** — scrolling threat intelligence banner

### 🌐 Aesthetic Landing Globe (`/`)

A purely decorative **3D Earth** (no data visualization) — inspired by [Kaspersky CyberMap](https://cybermap.kaspersky.com/). Just smooth auto-rotation with a night-sky background. Designed to make the dashboard look cool on first load.

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/Ashbeel-Zai/HoneyPot-CyberSecurity---Project.git`
3. **Create a feature branch**: `git checkout -b feature/amazing-feature`
4. **Commit** your changes: `git commit -m 'Add amazing feature'`
5. **Push** to the branch: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Ideas for Contributions
- Add Telnet honeypot support
- MySQL/Honeytoken database integration
- Docker deployment with docker-compose
- Slack/Discord/Telegram alert webhooks
- Export attack data as CSV/JSON reports
- Add more complex emulated shell commands
- Implement IP blacklisting/threat intel feeds

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2024 Ashbeel-Zai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Made with 🔥 by [Ashbeel-Zai](https://github.com/Ashbeel-Zai)**

*Deploy. Observe. Defend.*

</div>
