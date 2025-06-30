from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
import sqlite3
import re
import pyperclip
import subprocess
import threading
from datetime import datetime, timezone, timedelta
import threading
import time
from colorama import init, Fore, Style
import serial
import serial.tools.list_ports
import os
import sys
import pytz
import subprocess
from colorama import init, Fore, Style
import re

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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO sensor_data (timestamp, humidity, temperature, pump_status, system_status)
            VALUES (?, ?, ?, ?, ?)
        ''', (get_local_time(), humidity, temperature, pump_status, system_status))

        conn.commit()
        conn.close()
        print(f"✅ Datos guardados en BD: H:{humidity}% T:{temperature}°C")
    except Exception as e:
        print(f"❌ Error guardando en BD: {e}")

def save_irrigation_event(event_type, duration=None, humidity_before=None, humidity_after=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO irrigation_events (timestamp, event_type, duration, humidity_before, humidity_after)
            VALUES (?, ?, ?, ?, ?)
        ''', (get_local_time(), event_type, duration, humidity_before, humidity_after))

        conn.commit()
        conn.close()
        print(f"✅ Evento guardado: {event_type}")
    except Exception as e:
        print(f"❌ Error guardando evento: {e}")

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
last_save_time = 0  # Para controlar el guardado cada 30 segundos

# LECTURA DE DATOS ARDUINO - CORREGIDA
def read_arduino_data():
    global latest_data, irrigation_start_time, last_pump_status, last_save_time

    ser = connect_arduino()

    if not ser:
        latest_data['connection_status'] = 'Error: Arduino no detectado'
        print("❌ Arduino no detectado")
        return

    latest_data['connection_status'] = 'Conectado'
    print("✅ Arduino conectado exitosamente")

    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Imprimir línea para debug
                print(f"Arduino dice: {line}")

                # Buscar líneas que contengan los datos del sensor
                if "Raw sensor:" in line and "Humedad:" in line and "Temp:" in line and "Estado:" in line:
                    try:
                        # Parsear la línea completa del serial
                        # Formato: "Raw sensor: 567 -> Humedad: 45% | Temp: 25.2C | Estado: ESPERANDO | Planta necesita agua: NO"
                        
                        # Extraer humedad
                        humidity_match = re.search(r'Humedad: (\d+)%', line)
                        humidity = int(humidity_match.group(1)) if humidity_match else 0
                        
                        # Extraer temperatura
                        temp_match = re.search(r'Temp: ([\d\.-]+)C', line)
                        if temp_match:
                            temp_str = temp_match.group(1)
                            temperature = float(temp_str) if temp_str != "nan" else 0.0
                        else:
                            temperature = 0.0
                        
                        # Extraer estado
                        estado_match = re.search(r'Estado: ([^|]+)', line)
                        estado = estado_match.group(1).strip() if estado_match else "DESCONOCIDO"
                        
                        # CORECCIÓN PRINCIPAL: Determinar estado de la bomba correctamente
                        # En Arduino: bombaActiva es true cuando está regando
                        pump_status = "RIEGO ACTIVO" in estado.upper()
                        
                        # Actualizar datos
                        latest_data.update({
                            'humidity': humidity,
                            'temperature': temperature,
                            'pump_status': pump_status,
                            'system_status': estado,
                            'timestamp': get_local_time_iso()
                        })

                        # Detectar cambios en el estado de la bomba
                        if pump_status and not last_pump_status:
                            print(f"🚿 BOMBA ENCENDIDA - Humedad: {humidity}%")
                            irrigation_start_time = time.time()
                            save_irrigation_event("INICIO_RIEGO", humidity_before=humidity)

                        elif not pump_status and last_pump_status:
                            print(f"⏹️ BOMBA APAGADA - Humedad: {humidity}%")
                            if irrigation_start_time:
                                duration_seconds = int(time.time() - irrigation_start_time)
                                save_irrigation_event("FIN_RIEGO", duration=duration_seconds, humidity_after=humidity)
                                irrigation_start_time = None
                            else:
                                save_irrigation_event("FIN_RIEGO", humidity_after=humidity)

                        last_pump_status = pump_status

                        # *** CORECCIÓN PRINCIPAL: Guardar datos cada 30 segundos ***
                        current_time = time.time()
                        if current_time - last_save_time >= 30:  # 30 segundos han pasado
                            save_sensor_data(humidity, temperature, pump_status, estado)
                            last_save_time = current_time

                        # Enviar datos por WebSocket
                        socketio.emit('sensor_data', latest_data)
                        
                        # Debug info
                        print(f"💧 H:{humidity}% T:{temperature}°C Bomba:{'ON' if pump_status else 'OFF'} Estado:{estado}")

                    except Exception as e:
                        print(f"❌ Error parseando datos: {e}")
                        print(f"Línea problemática: {line}")

            time.sleep(0.5)  # Reducir un poco el delay para mejor respuesta

        except Exception as e:
            print(f"❌ Error en lectura Arduino: {e}")
            time.sleep(2)  # Esperar antes de reintentar
            # Intentar reconectar
            ser = connect_arduino()
            if not ser:
                latest_data['connection_status'] = 'Error: Arduino desconectado'
                break

    if ser:
        ser.close()

# FUNCIÓN PARA INSERTAR DATOS DE PRUEBA (OPCIONAL)
def insert_test_data():
    """Función para insertar datos de prueba si no hay datos en la BD"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si hay datos
    cursor.execute('SELECT COUNT(*) FROM sensor_data')
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("📊 Insertando datos de prueba...")
        # Insertar algunos datos de prueba
        for i in range(10):
            timestamp = datetime.now(ECUADOR_TZ) - timedelta(minutes=i*5)
            cursor.execute('''
                INSERT INTO sensor_data (timestamp, humidity, temperature, pump_status, system_status)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp.strftime('%Y-%m-%d %H:%M:%S'), 45+i, 25.0+i*0.5, False, 'ESPERANDO'))
        
        conn.commit()
        print("✅ Datos de prueba insertados")
    
    conn.close()

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

    try:
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
        print(f"📊 Enviando {len(data)} registros históricos")
        return jsonify(data)
    
    except Exception as e:
        print(f"❌ Error obteniendo datos históricos: {e}")
        return jsonify([])

@app.route('/api/irrigation-events')
def get_irrigation_events():
    days = request.args.get('days', 7, type=int)

    try:
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
    
    except Exception as e:
        print(f"❌ Error obteniendo eventos: {e}")
        return jsonify([])

@app.route('/api/statistics')
def get_statistics():
    try:
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
    
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({
            'avg_humidity': 0,
            'min_humidity': 0,
            'max_humidity': 0,
            'avg_temperature': 0,
            'pump_activations_24h': 0
        })

# WEBSOCKET EVENTS
@socketio.on('connect')
def handle_connect():
    emit('sensor_data', latest_data)

@socketio.on('disconnect')
def handle_disconnect():
    pass

# FUNCIÓN PARA INICIAR CLOUDFLARE
def start_cloudflare_tunnel():
    init(autoreset=True)

    def run_tunnel():
        try:
            print(Fore.CYAN + "\n🌀 Iniciando túnel Cloudflare...")
            process = subprocess.Popen(
                ['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                print(line.strip())

                # Buscar la URL pública de trycloudflare
                url_match = re.search(r"https://.*?trycloudflare\.com", line)
                if url_match:
                    public_url = url_match.group(0)

                    # Mostrar en consola con diseño resaltado
                    print(Fore.GREEN + Style.BRIGHT + "\n╔════════════════════════════════════╗")
                    print(Fore.GREEN + Style.BRIGHT + "║     🌍 URL PÚBLICA DE ACCESO       ║")
                    print(Fore.YELLOW + Style.BRIGHT + f"║     {public_url:<30}║")
                    print(Fore.GREEN + Style.BRIGHT + "╚════════════════════════════════════╝\n")

                    # Copiar al portapapeles
                    pyperclip.copy(public_url)
                    print(Fore.MAGENTA + "📋 URL copiada automáticamente al portapapeles.")
        except Exception as e:
            print(Fore.RED + f"⚠️ Error al iniciar túnel Cloudflare: {e}")

    threading.Thread(target=run_tunnel, daemon=True).start()

# INICIO DEL SISTEMA
if __name__ == '__main__':
    print("🚀 Iniciando sistema de riego inteligente...")
    
    # Inicializar base de datos
    init_db()
    print("✅ Base de datos inicializada")
    
    # Insertar datos de prueba si es necesario
    insert_test_data()

    # Iniciar hilo de Arduino
    arduino_thread = threading.Thread(target=read_arduino_data, daemon=True)
    arduino_thread.start()
    print("✅ Hilo de Arduino iniciado")

    # Iniciar túnel Cloudflare
    tunnel_thread = threading.Thread(target=start_cloudflare_tunnel, daemon=True)
    tunnel_thread.start()
    print("✅ Túnel Cloudflare iniciado")

    try:
        print("🚀 Servidor ejecutándose en http://localhost:5000")
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Cerrando servidor...")
        sys.exit(0)