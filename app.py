# app.py - Versión compatible con Render y pruebas locales
import os
import sys
import json
import time
import serial
import sqlite3
import pytz
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import serial.tools.list_ports

# ======== CONFIGURACION BASE ========
import eventlet
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DATABASE = 'irrigation_data.db'
ECUADOR_TZ = pytz.timezone('America/Guayaquil')

# ======== FUNCIONES DE TIEMPO ========
def get_local_time():
    now = datetime.now(ECUADOR_TZ)
    return now.strftime('%Y-%m-%d %H:%M:%S')

def get_local_time_iso():
    now = datetime.now(ECUADOR_TZ)
    return now.isoformat()

# ======== BASE DE DATOS ========
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
    conn.execute('''
        INSERT INTO sensor_data (timestamp, humidity, temperature, pump_status, system_status)
        VALUES (?, ?, ?, ?, ?)''',
        (get_local_time(), humidity, temperature, pump_status, system_status))
    conn.commit()
    conn.close()

def save_irrigation_event(event_type, duration=None, humidity_before=None, humidity_after=None):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO irrigation_events (timestamp, event_type, duration, humidity_before, humidity_after)
        VALUES (?, ?, ?, ?, ?)''',
        (get_local_time(), event_type, duration, humidity_before, humidity_after))
    conn.commit()
    conn.close()

# ======== VARIABLES GLOBALES ========
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

# ======== FUNCIONES ARDUINO (SOLO LOCAL) ========
def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description.lower() for keyword in ['arduino', 'ch340', 'ch341', 'usb']):
            return port.device
    return 'COM7'

def connect_arduino():
    port = find_arduino_port()
    try:
        ser = serial.Serial(port=port, baudrate=115200, timeout=2)
        time.sleep(2)
        ser.flushInput()
        ser.flushOutput()
        return ser
    except:
        return None

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
                    parts = line.split(" | ")
                    humedad = int(parts[0].split("Humedad: ")[1].split("%")[0])
                    temp_str = parts[1].split("Temp: ")[1].split("C")[0]
                    temperatura = float(temp_str) if temp_str != "nan" else 0.0
                    estado = parts[2].split("Estado: ")[1] if len(parts) > 2 else "ESPERANDO"
                    pump_status = "RIEGO" in estado

                    latest_data.update({
                        'humidity': humedad,
                        'temperature': temperatura,
                        'pump_status': pump_status,
                        'system_status': estado,
                        'timestamp': get_local_time_iso()
                    })

                    if pump_status and not last_pump_status:
                        irrigation_start_time = time.time()
                        save_irrigation_event("INICIO_RIEGO", humidity_before=humedad)
                    elif not pump_status and last_pump_status:
                        duracion = int(time.time() - irrigation_start_time) if irrigation_start_time else None
                        save_irrigation_event("FIN_RIEGO", duration=duracion, humidity_after=humedad)
                        irrigation_start_time = None

                    last_pump_status = pump_status

                    if int(time.time()) % 30 == 0:
                        save_sensor_data(humedad, temperatura, pump_status, estado)

                    socketio.emit('sensor_data', latest_data)

            time.sleep(1)
        except Exception:
            break
    ser.close()

# ======== RUTAS WEB ========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/current-data')
def get_current_data():
    return jsonify(latest_data)

@app.route('/api/statistics')
def get_statistics():
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now(ECUADOR_TZ) - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute('''
        SELECT AVG(humidity), MIN(humidity), MAX(humidity), AVG(temperature)
        FROM sensor_data WHERE timestamp >= ?''', (cutoff,))
    stats = cursor.fetchone()

    cursor.execute('''
        SELECT COUNT(*) FROM irrigation_events 
        WHERE event_type = 'INICIO_RIEGO' AND timestamp >= ?''', (cutoff,))
    count = cursor.fetchone()[0]

    conn.close()
    return jsonify({
        'avg_humidity': round(stats[0] or 0, 1),
        'min_humidity': stats[1] or 0,
        'max_humidity': stats[2] or 0,
        'avg_temperature': round(stats[3] or 0, 1),
        'pump_activations_24h': count
    })

# ======== SOCKET IO ========
@socketio.on('connect')
def on_connect():
    emit('sensor_data', latest_data)

@socketio.on('disconnect')
def on_disconnect():
    pass

# ======== EJECUCION SEGURA ========
if __name__ == '__main__':
    init_db()

    # Ejecutar lectura Arduino solo si estamos en local
    if os.environ.get("RUNNING_IN_RENDER") != "1":
        hilo = threading.Thread(target=read_arduino_data, daemon=True)
        hilo.start()

    socketio.run(app, debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), allow_unsafe_werkzeug=True)

