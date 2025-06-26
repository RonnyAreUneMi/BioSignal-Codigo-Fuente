from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import sqlite3
from datetime import datetime, timezone, timedelta
import threading
import time
import serial
import serial.tools.list_ports
import os
import sys
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

DATABASE = 'irrigation_data.db'
ECUADOR_TZ = pytz.timezone('America/Guayaquil')

# FUNCIONES DE TIEMPO
def get_local_time():
    now = datetime.now(ECUADOR_TZ)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_local_time_iso():
    now = datetime.now(ECUADOR_TZ)
    return now.isoformat()

# CONFIGURACIÓN DE BASE DE DATOS
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            humidity INTEGER,
            temperature REAL,
            pump_status BOOLEAN,
            system_status TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS irrigation_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT,
            duration INTEGER,
            humidity_before INTEGER,
            humidity_after INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def save_sensor_data(humidity, temperature, pump_status, system_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sensor_data (timestamp, humidity, temperature, pump_status, system_status)
        VALUES (?, ?, ?, ?, ?)
    ''', (get_local_time(), humidity, temperature, pump_status, system_status))
    
    conn.commit()
    conn.close()

def save_irrigation_event(event_type, duration=None, humidity_before=None, humidity_after=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO irrigation_events (timestamp, event_type, duration, humidity_before, humidity_after)
        VALUES (?, ?, ?, ?, ?)
    ''', (get_local_time(), event_type, duration, humidity_before, humidity_after))
    
    conn.commit()
    conn.close()

# CONFIGURACIÓN ARDUINO
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ch341', 'usb']):
            return port.device
    
    return 'COM7'

def connect_arduino():
    port = find_arduino_port()
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=2
        )
        time.sleep(2)
        ser.flushInput()
        ser.flushOutput()
        return ser
    except:
        return None

# VARIABLES GLOBALES
latest_data = {
    'humidity': 0,
    'temperature': 0,
    'pump_status': False,
    'system_status': 'Iniciando...',
    'timestamp': get_local_time_iso(),
    'connection_status': 'Desconectado'
}

irrigation_start_time = None
last_pump_status = False

# LECTURA DE DATOS ARDUINO
def read_arduino_data():
    global latest_data, irrigation_start_time, last_pump_status
    
    ser = connect_arduino()
    
    if not ser:
        latest_data['connection_status'] = 'Error: Arduino no detectado'
        return
    
    latest_data['connection_status'] = 'Conectado'
    
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if "Humedad:" in line and "Temp:" in line:
                    try:
                        parts = line.split(" | ")
                        
                        humidity_part = parts[0]
                        humidity = int(humidity_part.split("Humedad: ")[1].split("%")[0])
                        
                        temp_part = parts[1]
                        temp_str = temp_part.split("Temp: ")[1].split("C")[0]
                        temperature = float(temp_str) if temp_str != "nan" else 0.0
                        
                        estado_part = parts[2] if len(parts) > 2 else "Estado: ESPERANDO"
                        estado = estado_part.split("Estado: ")[1]
                        pump_status = "RIEGO" in estado
                        
                        latest_data.update({
                            'humidity': humidity,
                            'temperature': temperature,
                            'pump_status': pump_status,
                            'system_status': estado,
                            'timestamp': get_local_time_iso()
                        })
                        
                        # CONTROL DE EVENTOS DE RIEGO
                        if pump_status and not last_pump_status:
                            irrigation_start_time = time.time()
                            save_irrigation_event("INICIO_RIEGO", humidity_before=humidity)
                            
                        elif not pump_status and last_pump_status:
                            if irrigation_start_time:
                                duration_seconds = int(time.time() - irrigation_start_time)
                                save_irrigation_event("FIN_RIEGO", duration=duration_seconds, humidity_after=humidity)
                                irrigation_start_time = None
                            else:
                                save_irrigation_event("FIN_RIEGO", humidity_after=humidity)
                        
                        last_pump_status = pump_status
                        
                        if int(time.time()) % 30 == 0:
                            save_sensor_data(humidity, temperature, pump_status, estado)
                        
                        socketio.emit('sensor_data', latest_data)
                        
                    except Exception as e:
                        pass
            
            time.sleep(1)
            
        except Exception as e:
            break
    
    if ser:
        ser.close()

# RUTAS WEB
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current-data')
def get_current_data():
    return jsonify(latest_data)

@app.route('/api/historical-data')
def get_historical_data():
    hours = request.args.get('hours', 24, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hours_ago = datetime.now(ECUADOR_TZ) - timedelta(hours=hours)
    hours_ago_str = hours_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT * FROM sensor_data 
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 100
    ''', (hours_ago_str,))
    
    data = []
    for row in cursor.fetchall():
        try:
            dt_naive = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            dt_local = ECUADOR_TZ.localize(dt_naive)
            iso_timestamp = dt_local.isoformat()
        except:
            iso_timestamp = row['timestamp']
        
        data.append({
            'timestamp': iso_timestamp,
            'humidity': row['humidity'],
            'temperature': row['temperature'],
            'pump_status': row['pump_status'],
            'system_status': row['system_status']
        })
    
    conn.close()
    return jsonify(data)

@app.route('/api/irrigation-events')
def get_irrigation_events():
    days = request.args.get('days', 7, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    days_ago = datetime.now(ECUADOR_TZ) - timedelta(days=days)
    days_ago_str = days_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT * FROM irrigation_events 
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 50
    ''', (days_ago_str,))
    
    events = []
    for row in cursor.fetchall():
        duration_text = ""
        if row['duration']:
            if row['duration'] < 60:
                duration_text = f"{row['duration']}s"
            elif row['duration'] < 3600:
                minutes = row['duration'] // 60
                seconds = row['duration'] % 60
                duration_text = f"{minutes}m {seconds}s"
            else:
                hours = row['duration'] // 3600
                minutes = (row['duration'] % 3600) // 60
                duration_text = f"{hours}h {minutes}m"
        
        events.append({
            'timestamp': row['timestamp'],
            'event_type': row['event_type'],
            'duration': row['duration'],
            'duration_text': duration_text,
            'humidity_before': row['humidity_before'],
            'humidity_after': row['humidity_after']
        })
    
    conn.close()
    return jsonify(events)

@app.route('/api/statistics')
def get_statistics():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hours_ago = datetime.now(ECUADOR_TZ) - timedelta(hours=24)
    hours_ago_str = hours_ago.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT 
            AVG(humidity) as avg_humidity,
            MIN(humidity) as min_humidity,
            MAX(humidity) as max_humidity,
            AVG(temperature) as avg_temperature
        FROM sensor_data 
        WHERE timestamp >= ?
    ''', (hours_ago_str,))
    
    stats = cursor.fetchone()
    
    cursor.execute('''
        SELECT COUNT(*) as pump_activations
        FROM irrigation_events 
        WHERE event_type = 'INICIO_RIEGO' 
        AND timestamp >= ?
    ''', (hours_ago_str,))
    
    pump_stats = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'avg_humidity': round(stats['avg_humidity'] or 0, 1),
        'min_humidity': stats['min_humidity'] or 0,
        'max_humidity': stats['max_humidity'] or 0,
        'avg_temperature': round(stats['avg_temperature'] or 0, 1),
        'pump_activations_24h': pump_stats['pump_activations'] or 0
    })

# WEBSOCKET EVENTS
@socketio.on('connect')
def handle_connect():
    emit('sensor_data', latest_data)

@socketio.on('disconnect')
def handle_disconnect():
    pass

# INICIO DEL SISTEMA
if __name__ == '__main__':
    init_db()
    
    arduino_thread = threading.Thread(target=read_arduino_data, daemon=True)
    arduino_thread.start()
    
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        sys.exit(0)