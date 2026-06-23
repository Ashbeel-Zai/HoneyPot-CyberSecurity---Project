from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
import requests
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///honeypot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
logging.basicConfig(level=logging.INFO)

GEO_CACHE = {}
EVENT_COLORS = {'login': '#ff1744', 'command': '#00e5ff'}

# ----------------------------- MODELS -----------------------------
class IPLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), unique=True, index=True)
    country = db.Column(db.String(100))
    country_code = db.Column(db.String(10))
    city = db.Column(db.String(100))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    isp = db.Column(db.String(200))
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50))
    protocol = db.Column(db.String(20))
    ip = db.Column(db.String(50))
    username = db.Column(db.String(100), nullable=True)
    password = db.Column(db.String(100), nullable=True)
    command = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    country = db.Column(db.String(100), nullable=True)
    country_code = db.Column(db.String(10), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

with app.app_context():
    db.create_all()

# ----------------------------- GEOLOCATION -----------------------------
PRIVATE_PREFIXES = ('10.', '172.', '192.168.', '127.', '0.', '169.254.')

def is_private_ip(ip):
    return ip.startswith(PRIVATE_PREFIXES) or ip == '::1' or ip == 'localhost'

def get_ip_location(ip_address):
    if is_private_ip(ip_address):
        return {'country': 'Private', 'country_code': 'XX', 'city': 'Local', 'latitude': 0, 'longitude': 0, 'isp': 'Local Network'}

    if ip_address in GEO_CACHE:
        return GEO_CACHE[ip_address]

    cached = IPLocation.query.filter_by(ip=ip_address).first()
    if cached:
        loc = {
            'country': cached.country, 'country_code': cached.country_code,
            'city': cached.city, 'latitude': cached.latitude,
            'longitude': cached.longitude, 'isp': cached.isp
        }
        GEO_CACHE[ip_address] = loc
        return loc

    try:
        r = requests.get(f'http://ip-api.com/json/{ip_address}?fields=status,country,countryCode,city,lat,lon,isp', timeout=3)
        if r.status_code == 200:
            d = r.json()
            if d.get('status') == 'success':
                loc = {
                    'country': d.get('country', 'Unknown'), 'country_code': d.get('countryCode', 'XX'),
                    'city': d.get('city', 'Unknown'), 'latitude': d.get('lat', 0),
                    'longitude': d.get('lon', 0), 'isp': d.get('isp', 'Unknown')
                }
                try:
                    db.session.add(IPLocation(
                        ip=ip_address, country=loc['country'], country_code=loc['country_code'],
                        city=loc['city'], latitude=loc['latitude'], longitude=loc['longitude'], isp=loc['isp']
                    ))
                    db.session.commit()
                except:
                    pass
                GEO_CACHE[ip_address] = loc
                return loc
    except Exception as e:
        logging.error(f"Geo error for {ip_address}: {e}")

    return {'country': 'Unknown', 'country_code': 'XX', 'city': 'Unknown', 'latitude': 0, 'longitude': 0, 'isp': 'Unknown'}

# ----------------------------- ROUTES -----------------------------
@app.route("/")
def index():
    return render_template("/glob.html")

@app.route("/advanced-dashboard")
def advanced_dashboard():
    return render_template("threatops_dashboard.html")

@app.route("/old-dashboard")
def old_dashboard():
    return render_template("advanced_dashboard.html")

@app.route("/api/event", methods=["POST"])
def receive_event():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON provided"}), 400

        location = get_ip_location(data.get("ip"))
        event = Event(
            event_type=data.get("event"), protocol=data.get("protocol"), ip=data.get("ip"),
            username=data.get("username"), password=data.get("password"),
            command=data.get("command"), session_id=data.get("session_id"),
            country=location.get('country'), country_code=location.get('country_code'),
            city=location.get('city'),
            latitude=location.get('latitude'), longitude=location.get('longitude')
        )
        db.session.add(event)
        db.session.commit()
        return jsonify({"status": "stored"}), 200
    except Exception as e:
        logging.error(f"receive_event error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/events", methods=["GET"])
def get_events():
    events = Event.query.order_by(Event.timestamp.desc()).limit(100).all()
    return jsonify([{
        "id": e.id, "event": e.event_type, "protocol": e.protocol, "ip": e.ip,
        "username": e.username, "password": e.password, "command": e.command,
        "session_id": e.session_id, "timestamp": e.timestamp
    } for e in events])

# ----------------------------- DASHBOARD API -----------------------------
@app.route("/api/dashboard/stats")
def dashboard_stats():
    try:
        total = Event.query.count()
        ips = db.session.query(Event.ip).distinct().count()
        logins = Event.query.filter_by(event_type="login").count()
        cmds = Event.query.filter_by(event_type="command").count()
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_events = Event.query.filter(Event.timestamp >= today_start).count()
        countries = db.session.query(Event.country).filter(Event.country.isnot(None), Event.country != 'Private').distinct().count()
        types_count = db.session.query(Event.event_type).distinct().count()
        sessions = db.session.query(Event.session_id).filter(Event.session_id.isnot(None)).distinct().count()
        return jsonify({
            "total_events": total, "unique_ips": ips,
            "login_attempts": logins, "commands_executed": cmds,
            "today_events": today_events, "unique_countries": countries,
            "unique_attack_types": types_count, "active_sessions": sessions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/timeline")
def dashboard_timeline():
    try:
        now = datetime.utcnow()
        past = now - timedelta(hours=24)
        timeline = db.session.query(
            func.strftime('%Y-%m-%d %H:00:00', Event.timestamp).label('hour'),
            func.count(Event.id).label('count')
        ).filter(Event.timestamp >= past).group_by('hour').all()
        return jsonify({'labels': [str(t[0]) for t in timeline], 'data': [t[1] for t in timeline]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/top-ips")
def top_ips():
    try:
        rows = db.session.query(Event.ip, func.count(Event.id).label('count')) \
            .group_by(Event.ip).order_by(func.count(Event.id).desc()).limit(10).all()
        return jsonify({'labels': [r[0] for r in rows], 'data': [r[1] for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/event-types")
def event_types():
    try:
        rows = db.session.query(Event.event_type, func.count(Event.id).label('count')) \
            .group_by(Event.event_type).all()
        return jsonify({'labels': [r[0] for r in rows], 'data': [r[1] for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/top-users")
def top_users():
    try:
        rows = db.session.query(Event.username, func.count(Event.id).label('count')) \
            .filter(Event.username.isnot(None)).group_by(Event.username) \
            .order_by(func.count(Event.id).desc()).limit(10).all()
        return jsonify({'labels': [r[0] or 'Unknown' for r in rows], 'data': [r[1] for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/top-commands")
def top_commands():
    try:
        rows = db.session.query(Event.command, func.count(Event.id).label('count')) \
            .filter(Event.command.isnot(None)).group_by(Event.command) \
            .order_by(func.count(Event.id).desc()).limit(15).all()
        return jsonify({'labels': [r[0] or 'Unknown' for r in rows], 'data': [r[1] for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/recent-events")
def recent_events():
    try:
        limit = request.args.get('limit', 30, type=int)
        events = Event.query.order_by(Event.timestamp.desc()).limit(limit).all()
        return jsonify([{
            "id": e.id, "event": e.event_type, "protocol": e.protocol, "ip": e.ip,
            "username": e.username, "password": e.password, "command": e.command,
            "session_id": e.session_id, "timestamp": e.timestamp.isoformat(),
            "country": e.country or 'Unknown', "country_code": (e.country_code or '').lower(),
            "city": e.city or 'Unknown'
        } for e in events])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/threat-level")
def threat_level():
    try:
        now = datetime.utcnow()
        past_hour = now - timedelta(hours=1)
        epm = Event.query.filter(Event.timestamp >= past_hour).count() / 60

        if epm > 10:
            level, score = "CRITICAL", 90
        elif epm > 5:
            level, score = "HIGH", 75
        elif epm > 2:
            level, score = "MEDIUM", 50
        else:
            level, score = "LOW", 25

        return jsonify({"level": level, "score": score, "events_per_minute": round(epm, 2)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/attack-locations")
def attack_locations():
    try:
        rows = db.session.query(
            Event.latitude, Event.longitude, Event.country, Event.country_code,
            Event.city, Event.event_type, func.count(Event.id).label('count')
        ).filter(Event.latitude.isnot(None), Event.longitude.isnot(None)) \
            .group_by(Event.latitude, Event.longitude, Event.event_type).all()
        return jsonify([{
            'lat': float(r[0]), 'lon': float(r[1]), 'country': r[2],
            'country_code': (r[3] or '').lower(), 'city': r[4],
            'type': r[5], 'count': r[6], 'color': EVENT_COLORS.get(r[5], '#00e5ff')
        } for r in rows])
    except Exception as e:
        logging.error(f"attack_locations error: {e}")
        return jsonify([])

@app.route("/api/dashboard/live-attacks")
def live_attacks():
    try:
        limit = request.args.get('limit', 30, type=int)
        events = Event.query.order_by(Event.timestamp.desc()).limit(limit).all()
        return jsonify([{
            'id': e.id, 'ip': e.ip, 'country': e.country or 'Unknown', 'country_code': (e.country_code or '').lower(),
            'city': e.city or 'Unknown',
            'event_type': e.event_type, 'username': e.username or '-',
            'command': e.command or 'N/A', 'timestamp': e.timestamp.isoformat(),
            'protocol': e.protocol or '',
            'session_id': e.session_id or '',
            'color': EVENT_COLORS.get(e.event_type, '#00e5ff'),
            'latitude': e.latitude, 'longitude': e.longitude
        } for e in events])
    except Exception as e:
        logging.error(f"live_attacks error: {e}")
        return jsonify([])

@app.route("/api/dashboard/heatmap")
def heatmap():
    try:
        rows = db.session.query(
            Event.country, Event.latitude, Event.longitude, func.count(Event.id).label('count')
        ).filter(Event.latitude.isnot(None), Event.longitude.isnot(None)) \
            .group_by(Event.country, Event.latitude, Event.longitude).all()
        return jsonify([{'lat': float(r[1]), 'lon': float(r[2]), 'count': r[3], 'value': min(r[3] * 100, 1000)} for r in rows])
    except Exception as e:
        return jsonify([])

@app.route("/api/dashboard/country-stats")
def country_stats():
    try:
        rows = db.session.query(
            Event.country, func.count(Event.id).label('count'), Event.event_type
        ).filter(Event.country.isnot(None)).group_by(Event.country, Event.event_type).all()

        cc_rows = db.session.query(
            Event.country, Event.country_code
        ).filter(Event.country.isnot(None), Event.country_code.isnot(None)).distinct().all()
        country_codes = {}
        for c, cc in cc_rows:
            if c not in country_codes and cc:
                country_codes[c] = cc.lower()

        cm = {}
        for country, count, etype in rows:
            if country not in cm:
                cm[country] = {'login': 0, 'command': 0}
            cm[country][etype] = count

        sorted_c = sorted(cm.items(), key=lambda x: x[1]['login'] + x[1]['command'], reverse=True)
        return jsonify({
            'countries': [c[0] for c in sorted_c[:15]],
            'country_codes': [country_codes.get(c[0], '') for c in sorted_c[:15]],
            'login_attacks': [c[1]['login'] for c in sorted_c[:15]],
            'command_attacks': [c[1]['command'] for c in sorted_c[:15]]
        })
    except Exception as e:
        return jsonify({})

# ----------------------------- RUN -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
