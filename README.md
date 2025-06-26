# 🌿 BioSignal – Web Service

**BioSignal** es un sistema de monitoreo en tiempo real para cultivos inteligentes, basado en sensores conectados a Arduino. Permite visualizar humedad del suelo, temperatura ambiental, estado del sistema de riego y estadísticas a través de una moderna interfaz web construida con Flask, Socket.IO y ApexCharts.

---

## 🚀 Características Principales

- 📡 **Recolección en tiempo real** de datos desde Arduino (vía puerto serie)
- 🌡️ **Monitoreo continuo** de humedad y temperatura
- 💧 **Detección automática** de eventos de riego (inicio y fin)
- 📊 **Estadísticas detalladas**: promedios, mínimos, máximos y activaciones
- 📈 **Gráficas dinámicas** con ApexCharts (humedad, temperatura y resumen general)
- 🕓 **Registro histórico** de eventos y sensores
- 🇪🇨 **Soporte completo** para zona horaria de Ecuador (`America/Guayaquil`)

---

## 🧰 Tecnologías Utilizadas

- **Backend:** Python 3.8+, Flask 2.3.3, Flask-SocketIO
- **Frontend:** HTML5, CSS3, JavaScript, ApexCharts
- **Base de datos:** SQLite
- **Serial:** PySerial
- **Tiempo real:** WebSockets (Socket.IO)

---

## ⚙️ Instalación y Ejecución

### 🔧 Requisitos Previos

- Python 3.8 o superior
- Git (opcional)
- Arduino conectado al puerto USB (con envío de datos por serial)

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

### 🌐 Acceder desde Navegador

Abre tu navegador en **http://localhost:5000**

---

## 🗂️ Estructura del Proyecto

```
biosignal-web/
├── app.py                # Servidor principal Flask + SocketIO
├── requirements.txt      # Dependencias del proyecto
├── README.md            # Documentación del proyecto
└── templates/
    └── index.html        # Interfaz web principal
```

---

## 🖼️ Capturas de Pantalla

*📌 Agregar aquí imágenes de la interfaz web, gráficos y eventos.*

---

## ✅ Comparación con Versión de Escritorio (.exe)

| Característica | Web (este proyecto) | Escritorio (versión `.exe`) |
|---|---|---|
| **Interfaz** | Moderna y responsive | Estilo tradicional (PyQt5) |
| **Gráficos** | Dinámicos (ApexCharts) | Estáticos (Matplotlib) |
| **Acceso remoto** | ✅ | ❌ |
| **Requiere Python** | ✅ | ❌ (solo dar doble clic) |
| **Ideal para** | Paneles y dashboards | Uso local, sin conocimientos técnicos |

---

## 📋 Requirements.txt

```txt
Flask==2.3.3
Flask-SocketIO==5.3.6
pyserial==3.5
```

---

## 🔧 Configuración Adicional

### Puerto Serial
Por defecto, la aplicación busca Arduino en los puertos COM más comunes. Si necesitas especificar un puerto específico, modifica la variable `SERIAL_PORT` en `app.py`.

### Zona Horaria
El sistema está configurado para Ecuador (`America/Guayaquil`). Para cambiar la zona horaria, modifica la configuración en el archivo principal.

---

## 🚨 Solución de Problemas

### Arduino no detectado
- Verifica que el Arduino esté conectado correctamente
- Asegúrate de que el puerto serie no esté siendo usado por otra aplicación
- Revisa que los drivers del Arduino estén instalados

### Error de puerto ocupado
```bash
# Si el puerto 5000 está ocupado, puedes cambiarlo en app.py
app.run(host='0.0.0.0', port=5001, debug=True)
```

---

## 🛡️ Licencia

Este proyecto está bajo la licencia y derechos del Autor.

---

## 👨‍💻 Autor

**Desarrollado por:** [Ronny Arellano]  
**Proyecto académico** – Ingeniería en Software  
**Universidad Estatal de Milagro** – 2025


## 📞 Soporte

Si tienes alguna pregunta o problema, puedes:

- Abrir un **Issue** en GitHub
- Contactar al desarrollador: [rarellanou@unemi.edu.ec]

---

*Desarrollado con ❤️ para el monitoreo inteligente de cultivos*
