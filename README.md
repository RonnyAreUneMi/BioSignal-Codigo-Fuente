# 🌿 BioSignal – Web Service
**BioSignal** es un sistema de monitoreo en tiempo real para cultivos inteligentes, basado en sensores conectados a Arduino. Permite visualizar humedad del suelo, temperatura ambiental, estado del sistema de riego y estadísticas a través de una moderna interfaz web construida con Flask, Socket.IO y ApexCharts.

---

## 🎥 Video Presentacion

<div align="center">
  
### 📹 **¡Unete al lado Automatico!!**
  
[![Video Demostración BioSignal](https://img.youtube.com/vi/VdRgOYqLFSA/maxresdefault.jpg)](https://youtu.be/VdRgOYqLFSA?si=LmCVEpfzb_5LctZB)

**🎬 [▶️ Ver Demo Completa en YouTube](https://youtu.be/VdRgOYqLFSA?si=LmCVEpfzb_5LctZB)**

*Descubre cómo funciona el sistema de monitoreo en tiempo real, las gráficas dinámicas y el acceso remoto desde cualquier dispositivo.*

</div>

---

## 🚀 Características Principales

- 📡 **Recolección en tiempo real** de datos desde Arduino (vía puerto serie)
- 🌡️ **Monitoreo continuo** de humedad del suelo y temperatura ambiental
- 💧 **Control automático de riego** con detección inteligente de eventos
- 🗄️ **Base de datos SQLite** integrada para almacenamiento persistente
- 📊 **Estadísticas avanzadas**: promedios, mínimos, máximos y contador de activaciones
- 📈 **Gráficas dinámicas** con ApexCharts (humedad, temperatura y resumen general)
- 🕓 **Historial completo** de eventos de riego y datos de sensores
- ⏰ **Seguimiento de duración** de eventos de riego con formato legible
- 🌐 **Túnel Cloudflare** integrado para acceso público remoto
- 📱 **Monitoreo móvil** - Acceso desde celular y cualquier lugar del mundo
- 🇪🇨 **Soporte completo** para zona horaria de Ecuador (`America/Guayaquil`)
- 🔌 **Detección automática** de puerto Arduino
- 📱 **WebSockets** para actualizaciones en tiempo real sin refrescar página

---

## 🧰 Tecnologías Utilizadas

- **Backend:** Python 3.8+, Flask 2.3.3, Flask-SocketIO
- **Frontend:** HTML5, CSS3, JavaScript, ApexCharts
- **Base de datos:** SQLite con esquemas optimizados
- **Serial:** PySerial para comunicación con Arduino
- **Tiempo real:** WebSockets (Socket.IO)
- **Acceso remoto:** Cloudflare Tunnel
- **Zona horaria:** PyTZ para manejo de tiempo local
- **Interfaz:** Colorama para terminal mejorada

---

## ⚙️ Instalación y Ejecución

### 🔧 Requisitos Previos
- Python 3.8 o superior
- Git (opcional)
- Arduino conectado al puerto USB (con envío de datos por serial)
- Cloudflared instalado (opcional, para acceso remoto)

### 📥 Clonar el Repositorio
```bash
git clone https://github.com/usuario/biosignal-web.git
cd biosignal-web
```

### 📦 Instalar Dependencias
Se recomienda usar entorno virtual:
```bash
python -m venv venv
venv\Scripts\activate    # En Windows
# o
source venv/bin/activate # En Linux/Mac
pip install -r requirements.txt
```

### ▶️ Ejecutar el Servidor
```bash
python app.py
```

### 🌐 Acceder al Sistema
- **Local:** http://localhost:5000
- **Remoto (desde cualquier dispositivo):** La URL pública se generará automáticamente y se copiará al portapapeles
- **📱 Desde celular:** Usa la URL pública para monitorear desde cualquier lugar mientras el Arduino esté conectado

---

## 🗂️ Estructura del Proyecto
```
biosignal-web/
├── app.py                # Servidor principal Flask + SocketIO + Arduino + DB
├── requirements.txt      # Dependencias del proyecto
├── README.md            # Documentación del proyecto
├── cloudflared.exe       # Ejecutable de Cloudflare (incluido en el repo)
├── templates/
│   └── index.html        # Interfaz web principal
└── irrigation_data.db    # Base de datos SQLite (se crea automáticamente)
```

---

## 📊 API Endpoints

### 🔗 Rutas Principales
- `GET /` - Interfaz web principal
- `GET /api/current-data` - Datos actuales de sensores
- `GET /api/historical-data?hours=24` - Datos históricos (últimas X horas)
- `GET /api/irrigation-events?days=7` - Eventos de riego (últimos X días)
- `GET /api/statistics` - Estadísticas de las últimas 24 horas

### 📡 WebSocket Events
- `sensor_data` - Emisión automática de datos en tiempo real
- `connect` - Conexión de cliente
- `disconnect` - Desconexión de cliente

---

## 🗃️ Esquema de Base de Datos

### Tabla: sensor_data
```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    humidity INTEGER,
    temperature REAL,
    pump_status BOOLEAN,
    system_status TEXT
);
```

### Tabla: irrigation_events
```sql
CREATE TABLE irrigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT,
    duration INTEGER,
    humidity_before INTEGER,
    humidity_after INTEGER
);
```

## ✅ Comparación con Versión de Escritorio (.exe)
| Característica | Web (este proyecto) | Escritorio (versión `.exe`) |
|---|---|---|
| **Interfaz** | Moderna y responsive | Estilo tradicional (PyQt5) |
| **Gráficos** | Dinámicos (ApexCharts) | Estáticos (Matplotlib) |
| **Acceso remoto** | ✅ (Cloudflare + móvil) | ❌ |
| **Base de datos** | ✅ SQLite persistente | ❌ Solo memoria |
| **Eventos de riego** | ✅ Historial completo | ❌ Limitado |
| **WebSockets** | ✅ Tiempo real | ❌ Polling |
| **API REST** | ✅ Disponible | ❌ |
| **Requiere Python** | ✅ | ❌ (solo dar doble clic) |
| **Ideal para** | Dashboards, IoT, monitoreo remoto y móvil | Uso local, sin conocimientos técnicos |

---

## 📋 Requirements.txt
```txt
Flask==2.3.3
Flask-SocketIO==5.3.6
pyserial==3.5
pytz==2023.3
colorama==0.4.6
pyperclip==1.8.2
```

---

## 🔧 Configuración Adicional

### Puerto Serial
La aplicación detecta automáticamente el Arduino buscando palabras clave como 'arduino', 'ch340', 'ch341', 'usb'. Si necesitas forzar un puerto específico, modifica la función `find_arduino_port()` en `app.py`.

### Zona Horaria
El sistema está configurado para Ecuador (`America/Guayaquil`). Para cambiar la zona horaria, modifica la variable `ECUADOR_TZ` en `app.py`.

### Cloudflare Tunnel
El túnel se inicia automáticamente. El ejecutable de `cloudflared` está incluido en este repositorio de GitHub para facilitar la instalación. Esto permite **monitorear desde el celular y cualquier lugar del mundo** mientras el Arduino esté conectado a la computadora local.

### Frecuencia de Guardado
Los datos se guardan en la base de datos cada 30 segundos automáticamente.

---

## 🚨 Solución de Problemas

### Arduino no detectado
- Verifica que el Arduino esté conectado correctamente
- Asegúrate de que el puerto serie no esté siendo usado por otra aplicación
- Revisa que los drivers del Arduino estén instalados
- Comprueba que el Arduino esté enviando datos en el formato esperado

### Error de puerto ocupado
```bash
# Si el puerto 5000 está ocupado, puedes cambiarlo en app.py
socketio.run(app, debug=False, host='0.0.0.0', port=5001)
```

### Base de datos corrupta
```bash
# Eliminar la base de datos para regenerarla
rm irrigation_data.db
# Luego ejecutar app.py nuevamente
```

### Cloudflare Tunnel no funciona
- El ejecutable `cloudflared.exe` está incluido en este repositorio
- Si tienes problemas, verifica que el puerto 5000 no esté bloqueado por el firewall
- O comentar la línea del túnel en `app.py` para usar solo localmente

---

## 🛡️ Licencia
Este proyecto está bajo la licencia y derechos del Autor.

---

## 👨‍💻 Autor
**Desarrollado por:** Ronny Arellano  
**Proyecto académico** – Ingeniería en Software  
**Universidad Estatal de Milagro** – 2025

## 📞 Soporte
Si tienes alguna pregunta o problema, puedes:
- Abrir un **Issue** en GitHub
- Contactar al desarrollador: rarellanou@unemi.edu.ec

---

*Desarrollado con ❤️ para el monitoreo inteligente de cultivos*