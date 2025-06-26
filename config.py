# Configuración del Sistema de Riego Inteligente

# Puerto Serial del Arduino
SERIAL_PORT = "COM7"  # En Windows: 'COM3', 'COM4', etc.
SERIAL_BAUDRATE = 9600

# Base de datos
DATABASE = "irrigation_data.db"

# Configuración del servidor
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# Umbrales del sistema (deben coincidir con Arduino)
UMBRAL_RIEGO = 30
UMBRAL_SATISFECHO = 45
TIEMPO_MIN_ENTRE_RIEGOS = 10000  # milisegundos
