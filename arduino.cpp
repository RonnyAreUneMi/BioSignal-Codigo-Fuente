#include <LiquidCrystal_I2C.h>
#include <DHT.h>

#define DHTPIN 9
#define DHTTYPE DHT11
#define RELE_PIN 8
#define UMBRAL_RIEGO 30
#define UMBRAL_SATISFECHO 45
#define TIEMPO_RIEGO_MAX 500  // 1 segundo para simular goteo
#define TEMP_MAX_RIEGO 30     // Temperatura máxima para permitir riego

#define SENSOR_SECO 1023
#define SENSOR_MOJADO 300

LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHTPIN, DHTTYPE);

unsigned long ultimoRiego = 0;
unsigned long tiempoMinEntreriegos = 10000;
unsigned long tiempoAnalisis = 15000;
bool bombaActiva = false;
bool plantaQuiereAgua = false;
bool analizandoHumedad = false;
bool temperaturaAlta = false;
unsigned long inicioRiego = 0;
unsigned long inicioAnalisis = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(RELE_PIN, OUTPUT);
  digitalWrite(RELE_PIN, HIGH);
  bombaActiva = false;
  
  lcd.init();
  delay(200);
  lcd.backlight();
  
  dht.begin();
  
  lcd.setCursor(0, 0);
  lcd.print("Sistema de Riego");
  lcd.setCursor(0, 1);
  lcd.print("Iniciando...    ");
  delay(2000);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Bomba: OFF      ");
  lcd.setCursor(0, 1);
  lcd.print("Sistema listo   ");
  delay(2000);
  lcd.clear();
  
  Serial.println("=== Sistema de riego iniciado ===");
  Serial.println("Estado inicial: Bomba OFF - Sistema listo");
  ultimoRiego = 0;
}

void loop() {
  int sensorValue = analogRead(A0);
  
  int humedad = map(sensorValue, SENSOR_SECO, SENSOR_MOJADO, 0, 100);
  humedad = constrain(humedad, 0, 100);
  
  float temperatura = dht.readTemperature();
  
  // Verificar si la temperatura es muy alta
  temperaturaAlta = (!isnan(temperatura) && temperatura > TEMP_MAX_RIEGO);
  
  verificarDeseoAgua(humedad);
  controlarRiego(humedad);
  
  // Si la temperatura es muy alta, mostrar pantalla especial
  if (temperaturaAlta) {
    mostrarTemperaturaAlta(temperatura);
    delay(8000); // Mostrar por más tiempo cuando hay problema
  } else {
    // Mostrar estado principal
    mostrarEstadoPrincipal(humedad);
    delay(3000);
    
    // Mostrar datos de sensores
    mostrarDatosSensores(temperatura, humedad);
    delay(5000);
    
    // Mostrar estado del sistema
    mostrarEstadoSistema();
  }
  
  Serial.print("Raw sensor: ");
  Serial.print(sensorValue);
  Serial.print(" -> Humedad: ");
  Serial.print(humedad);
  Serial.print("% | Temp: ");
  Serial.print(temperatura);
  Serial.print("C | Estado: ");
  if (temperaturaAlta) {
    Serial.print("TEMP ALTA - NO RIEGO");
  } else if (bombaActiva) {
    Serial.print("RIEGO ACTIVO");
  } else if (analizandoHumedad) {
    Serial.print("ANALIZANDO");
  } else {
    Serial.print("ESPERANDO");
  }
  Serial.print(" | Planta necesita agua: ");
  Serial.println(plantaQuiereAgua ? "SI" : "NO");
  
  delay(3000);
}

void mostrarTemperaturaAlta(float temperatura) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("TEMP MUY ALTA!  ");
  lcd.setCursor(0, 1);
  lcd.print("No riego: ");
  if (!isnan(temperatura)) {
    lcd.print(temperatura, 1);
    lcd.print("C");
  } else {
    lcd.print("--C");
  }
}

void mostrarEstadoPrincipal(int humedad) {
  lcd.clear();
  lcd.setCursor(0, 0);
  
  if (analizandoHumedad) {
    // Durante el análisis, mostrar mensaje especial
    lcd.print("Agua absorbiendo");
    lcd.setCursor(0, 1);
    lcd.print("Espere analisis");
  } else {
    // Mensaje normal de la planta
    lcd.print("Tu planta dice:");
    lcd.setCursor(0, 1);
    if (humedad > 80) {
      lcd.print("Me ahogo :O     ");
    } else if (humedad > 75) {
      lcd.print("Muy mojada :|   ");
    } else if (humedad > 40) {
      lcd.print("Estoy feliz :)  ");
    } else if (humedad > 30) {
      lcd.print("Tengo sed :/    ");
    } else if (humedad > 15) {
      lcd.print("Agua urgente :( ");
    } else {
      lcd.print("Me muero D:     ");
    }
  }
}

void mostrarDatosSensores(float temperatura, int humedad) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Temp: ");
  if (isnan(temperatura)) {
    lcd.print("Error   ");
  } else {
    lcd.print(temperatura, 1);
    lcd.print("C      ");
  }
  
  lcd.setCursor(0, 1);
  if (analizandoHumedad) {
    // Durante análisis, mostrar que el sensor está estabilizando
    lcd.print("Estabilizando...");
  } else {
    lcd.print("Humedad: ");
    lcd.print(humedad);
    lcd.print("%   ");
  }
}

void mostrarEstadoSistema() {
  lcd.clear();
  lcd.setCursor(0, 0);
  
  if (bombaActiva) {
    lcd.print("Bomba: ON       ");
    lcd.setCursor(0, 1);
    // Mostrar tiempo transcurrido de riego
    unsigned long tiempoRiego = (millis() - inicioRiego) / 1000;
    lcd.print("Goteo ");
    lcd.print(tiempoRiego);
    lcd.print("s    ");
  } else if (analizandoHumedad) {
    lcd.print("Bomba: OFF      ");
    lcd.setCursor(0, 1);
    // Calcular tiempo restante correctamente
    unsigned long tiempoTranscurrido = millis() - inicioAnalisis;
    if (tiempoTranscurrido < tiempoAnalisis) {
      unsigned long tiempoRestante = (tiempoAnalisis - tiempoTranscurrido) / 1000;
      lcd.print("Esperando ");
      lcd.print(tiempoRestante + 1); // +1 para evitar mostrar 0 antes de tiempo
      lcd.print("s  ");
    } else {
      lcd.print("Finalizando...  ");
    }
  } else {
    lcd.print("Bomba: OFF      ");
    lcd.setCursor(0, 1);
    if (plantaQuiereAgua && !temperaturaAlta) {
      // Verificar si está en tiempo de espera entre riegos
      if (ultimoRiego > 0) {
        unsigned long tiempoTranscurrido = millis() - ultimoRiego;
        if (tiempoTranscurrido < tiempoMinEntreriegos) {
          unsigned long tiempoEspera = (tiempoMinEntreriegos - tiempoTranscurrido) / 1000;
          lcd.print("Espera ");
          lcd.print(tiempoEspera + 1);
          lcd.print("s    ");
        } else {
          lcd.print("Preparando riego");
        }
      } else {
        lcd.print("Preparando riego");
      }
    } else if (temperaturaAlta) {
      lcd.print("Temp muy alta   ");
    } else {
      lcd.print("Sin necesidad   ");
    }
  }
}

void verificarDeseoAgua(int humedad) {
  if (humedad <= UMBRAL_RIEGO) {
    plantaQuiereAgua = true;
  } else if (humedad >= UMBRAL_SATISFECHO) {
    plantaQuiereAgua = false;
  }
}

void controlarRiego(int humedad) {
  unsigned long tiempoActual = millis();
  
  // Si la temperatura es muy alta y está regando, detener inmediatamente
  if (temperaturaAlta && bombaActiva) {
    digitalWrite(RELE_PIN, HIGH);
    bombaActiva = false;
    ultimoRiego = tiempoActual;
    Serial.println("Riego detenido por temperatura alta");
    return;
  }
  
  if (analizandoHumedad) {
    if (tiempoActual - inicioAnalisis >= tiempoAnalisis) {
      analizandoHumedad = false;
      Serial.println("Análisis completado - Agua absorbida por la planta");
      
      if (humedad <= UMBRAL_RIEGO) {
        plantaQuiereAgua = true;
        Serial.println("Resultado: Aún necesita más riego");
      } else {
        plantaQuiereAgua = false;
        Serial.println("Resultado: Riego suficiente - Planta satisfecha");
      }
    }
    return;
  }
  
  if (bombaActiva) {
    if (!plantaQuiereAgua || humedad >= UMBRAL_SATISFECHO || 
        (tiempoActual - inicioRiego >= TIEMPO_RIEGO_MAX)) {
      
      digitalWrite(RELE_PIN, HIGH);
      bombaActiva = false;
      ultimoRiego = tiempoActual;
      
      analizandoHumedad = true;
      inicioAnalisis = tiempoActual;
      
      if (humedad >= UMBRAL_SATISFECHO) {
        Serial.println("Planta satisfecha - Bomba OFF - Iniciando período de absorción");
      } else {
        Serial.println("Goteo completado - Bomba OFF - Iniciando análisis de absorción");
      }
    }
    return;
  }
  
  // Solo iniciar riego si la temperatura no es muy alta
  if (plantaQuiereAgua && humedad <= UMBRAL_RIEGO && !temperaturaAlta) {
    if (tiempoActual - ultimoRiego >= tiempoMinEntreriegos) {
      Serial.println("Riego necesario - Activando bomba de agua");
      
      delay(100);
      digitalWrite(RELE_PIN, LOW);
      bombaActiva = true;
      inicioRiego = tiempoActual;
      
      Serial.print("Goteo iniciado - Humedad actual: ");
      Serial.print(humedad);
      Serial.println("% - Comenzando goteo de 1 segundo...");
    } else {
      Serial.println("Riego necesario pero respetando tiempo mínimo entre riegos");
    }
  } else if (plantaQuiereAgua && temperaturaAlta) {
    Serial.println("Riego necesario pero temperatura muy alta - Esperando...");
  }
}