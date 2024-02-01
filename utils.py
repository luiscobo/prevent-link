# -------------------------------------------------------
# En este módulo se encuentran las clases que permite
# la comunicación con el arduino que gestiona el 
# sistema de alarma y los relés conectados a las máquinas
# Autor: Luis Cobo
# Proyecto: PrevenLink
# -------------------------------------------------------

import configparser
from Arduino import Arduino
import cv2
import argparse
import time

# -------------------------------------------------------
# Constantes
# -------------------------------------------------------

OUTPUT = "OUTPUT"
LOW = "LOW"
HIGH = "HIGH"
BAUD_RATE = "115200"


# -------------------------------------------------------
# Clase para manejar la configuración de la conexión con
# los arduinos de este servidor
# -------------------------------------------------------

class Configuracion:

    def __init__(self, archivo_configuracion: str = './preventlink.ini'):
        # Inicializacion de atributos
        self.reles: list[int] = []
        self.leds: dict = {}
        self.rele_normalmente_abierto: bool = False
        self.ARCHIVO_CONFIGURACION: str = archivo_configuracion
        self.es_valido: bool = False
        self.tiene_reles: bool = False
        self.tiene_alarmas: bool = False
        self.puerto_arduino_reles: str = None
        self.puerto_arduino_alarmas: str = None
        self.tiene_camara: bool = False
        self.camara_valida: bool = False
        self.camara: str = None
        self.ancho_imagen: int = 640
        self.alto_imagen: int = 480
        self.numero_camara: int = 0
        self.rotacion_camara: int = None
        self.tiempo_alarma: float = 15
        self.tiempo_error: float = 15
        self.emitir_sonido_alarma: bool = False
        self.emitir_sonido_error: bool = False

        # Datos para el lector de tags rfid
        self.tiene_lector_rfids: bool = False
        self.dir_ip_lector_rfids: str = '0.0.0.0'
        self.potencia_transmision_lector_rfids = 81
        self.tags: list[int] = []

        # Datos para el predictor
        self.modelo = None
        self.confianza_minima = 0.5
        self.carpeta_imagenes = './imagenes'
        self.guardar_imagenes = False
        self.guardar_texto = False
        self.prefijo_imagenes = ''

        # Configuración de los EPPs para esta maquina
        self.epps: list[int] = []

        # Configuracion
        self.config = configparser.ConfigParser()
        self.config.read(self.ARCHIVO_CONFIGURACION)

        # Elementos de protección personal configurado en esta maquina
        self.epps: list[int] = []

        if self.config.has_section('conexion'):
            self.es_valido = True

            # Configuración de los reles
            puerto = self.config.get('conexion', 'puerto-reles')
            if puerto is None or puerto.upper() == 'NO':
                self.tiene_reles = False
            else:
                self.tiene_reles = True
                self.puerto_arduino_reles = puerto
                for i in range(1, 5):
                    self.reles.append(int(self.config.getint('reles', f'pin-rele-{i}')))

                na = self.config.get('reles', 'normalmente-abierto')
                if na is None or na.upper() == 'SI':
                    self.rele_normalmente_abierto = True

            # Configuracion de la alarma
            puerto = self.config.get('conexion', 'puerto-alarma')
            if puerto is None or puerto.upper() == 'NO':
                self.tiene_alarmas = False
            else:                
                self.puerto_arduino_alarmas = puerto
                if self.config.has_section('alarma'):
                    self.tiene_alarmas = True
                    self.leds['rojo'] = int(self.config.getint('alarma', 'pin-rojo'))
                    self.leds['verde'] = int(self.config.getint('alarma', 'pin-verde'))
                    self.leds['azul'] = int(self.config.getint('alarma', 'pin-azul'))
                    self.leds['zumbador'] = int(self.config.getint('alarma', 'pin-zumbador'))
                    if self.config.has_option('alarma', 'tiempo-alarma'):
                        self.tiempo_alarma = self.config.getfloat('alarma', 'tiempo-alarma')
                    if self.config.has_option('alarma', 'tiempo-error'):
                        self.tiempo_alarma = self.config.getfloat('alarma', 'tiempo-alarma')
                    if self.config.has_option('alarma', 'emitir-sonido-alarma'):
                        self.emitir_sonido_alarma = self.config.get('alarma', 'emitir-sonido-alarma').tolower() == "SI"
                    if self.config.has_option('alarma', 'emitir-sonido-error'):
                        self.emitir_sonido_alarma = self.config.get('alarma', 'emitir-sonido-error').tolower() == "SI"
                    
            # Configuración del lector de rfids
            if self.config.has_option('conexion', 'usar-rfid-tags'):
                self.tiene_lector_rfids = self.config.get('conexion', 'usar-rfid-tags').lower() == 'si'
                if self.tiene_lector_rfids:
                    if self.config.has_option('conexion', 'lector-rfid-direccion-ip'):
                        self.dir_ip_lector_rfids = self.config.get('conexion', 'lector-rfid-direccion-ip')
                        if self.config.has_option('conexion', 'lector-rfid-potencia-transmision'):
                            self.potencia_transmision_lector_rfids = self.config.getint('conexion', 'lector-rfid-potencia-transmision')

        # Trabajo con el modelo de YOLO
        if self.config.has_section('detector'):
            self.modelo = self.config.get('detector', 'modelo')
            if self.config.has_option('detector', 'confianza-minima'):
                self.confianza_minima = self.config.getfloat('detector', 'confianza-minima')
            if self.config.has_option('detector', 'carpeta-imagenes'):
                self.carpeta_imagenes = self.config.get('detector', 'carpeta-imagenes')
            if self.config.has_option('detector', 'guardar-imagenes'):
                self.guardar_imagenes = self.config.get('detector', 'guardar-imagenes').upper() == 'SI'
            if self.config.has_option('detector', 'guardar-texto'):
                self.guardar_texto = self.config.get('detector', 'guardar-texto').upper() == 'SI'
            if self.config.has_option('detector', 'prefijo-imagenes'):
                self.prefijo_imagenes = self.config.get('detector', 'prefijo-imagenes')
                
        # Epps configurados para este GPIO
        if self.config.has_section('epps'):
            if self.config.has_option('epps', 'numero-de-epps'):
                n = self.config.getint('epps', 'numero-de-epps')
                for i in range(1, n+1):
                    self.epps.append(self.config.getint('epps', f'epp-{i}'))

        # Tags configurados para este GPIO
        if self.tiene_lector_rfids:
            if self.config.has_section('tags'):
                if self.config.has_option('tags', 'numero-de-tags'):
                    n = self.config.getint('tags', 'numero-de-tags')
                    for i in range(1, n+1):
                        self.tags.append(self.config.getint('tags', f'tag={i}'))

        # Configuración de la camara
        if self.config.has_section('camara'):
            self.tiene_camara = True
            if self.config.has_option('camara', 'dispositivo'):
                dato = self.config.get('camara', 'dispositivo').lower()
                if (dato == 'picamera') or (dato == 'usbcamera'):
                    self.camara = dato
                    self.camara_valida = True

            if self.config.has_option('camara', 'numero-camara'):
                self.numero_camara = self.config.getint('camara', 'numero-camara')

            if self.config.has_option('camara', 'ancho-imagen'):
                self.ancho_imagen = self.config.getint('camara', 'ancho-imagen')

            if self.config.has_option('camara', 'alto-imagen'):
                self.alto_imagen = self.config.getint('camara', 'alto-imagen')

            if self.config.has_option('camara', 'rotacion'):
                dato = self.config.get('camara', 'rotacion').lower()
                if dato == 'no':
                    self.rotacion_camara = None
                elif dato == 'voltear':
                    self.rotacion_camara = cv2.ROTATE_180
                elif dato == 'izquierda':
                    self.rotacion_camara = cv2.ROTATE_90_COUNTERCLOCKWISE
                elif dato == 'derecha':
                    self.rotacion_camara = cv2.ROTATE_90_CLOCKWISE

                
            
    def pin(self, nombre: str) -> int:
        if nombre.lower() in ['rojo', 'verde', 'azul', 'zumbador']:
            return self.leds[nombre]
        elif nombre.lower() in ['rele-1', 'rele1']:
            return self.reles[0]
        elif nombre.lower() in ['rele-2', 'rele2']:
                return self.reles[1]
        elif nombre.lower() in ['rele-3', 'rele3']:
            return self.reles[2]
        elif nombre.lower() in ['rele-4', 'rele4']:
            return self.reles[3]
        else:
            return -1


# -------------------------------------------------------
# Clase para manejar la comunicación con el dispositivo
# de relés, de acuerdo a la configuración que se tiene
# en la aplicación.
# -------------------------------------------------------

class Maquina:
    def __init__(self, config: Configuracion, normalmente_abierto: bool = None):
        self.estado: str = "APAGADA"
        self.arduino: Arduino = None
        self.configuracion: Configuracion = None
        
        if not config.es_valido or not config.tiene_reles:
            self.estado = "NO CONFIGURACION"
        else:
            # Nos conectamos a la maquina por lo que indica la configuración
            self.arduino = Arduino(BAUD_RATE, port=config.puerto_arduino_reles)

            # Configuracion del tipo de reles
            
            if normalmente_abierto is None:
                normalmente_abierto = config.rele_normalmente_abierto

            if normalmente_abierto:
                self.ON = LOW  # Encender la maquina toca enviar un LOW
                self.OFF = HIGH  # Apagar la maquina toca enviar un HIGH
            else:
                self.ON = HIGH  # Para encender, se envia un HIGH
                self.OFF = LOW  # Para apagar se envía un LOW

            # Ahora apagamos la máquina
            for pin in config.reles:
                self.arduino.pinMode(pin, OUTPUT)
                self.arduino.digitalWrite(pin, self.OFF)  # Vamos a apagar la máquina

            # Guardamos la configuracion internamente
            self.configuracion = config

    def apagar(self):
        """Permite apagar la maquina conectada al arduino"""
        if self.estado != "NO CONFIGURACION":
            for pin in self.configuracion.reles:
                self.arduino.digitalWrite(pin, self.OFF)
            self.estado = "APAGADA"

    def encender(self):
        """Realiza la tarea de encender la maquina conectada al arduino"""
        if self.estado != "NO CONFIGURACION":
            for pin in self.configuracion.reles:
                self.arduino.digitalWrite(pin, self.ON)
            self.estado = "ENCENDIDA"

    def puerto(self) -> str:
        """
        Obtiene el puerto al cual está conectado la máquina de relés
        """
        if self.configuracion.es_valido and self.configuracion.tiene_reles:
            return self.configuracion.puerto_arduino_reles
        
        return "NO PUERTO"


# -------------------------------------------------------
# Clase para manejar la comunicación con el dispositivo
# arduino que gestiona las alarmas sonoras y visuales
# ----------------------------------------------------------------

class DispositivoAlarma:
    configuracion: Configuracion = None
    arduino: Arduino = None
    estado: str = "APAGADA"

    def __init__(self, configuracion: Configuracion):
        self.configuracion = configuracion
        if not self.configuracion.es_valido or not self.configuracion.tiene_alarmas:
            self.estado = "NO CONFIGURACION"
        else:
            # Conectarse al arduino de las alarmas
            self.arduino = Arduino(BAUD_RATE, port=self.configuracion.puerto_arduino_alarmas)
            self.estado = "APAGADA"

            # Apagamos todos los leds
            for nombre, pin in self.configuracion.leds.items():
                self.arduino.pinMode(pin, OUTPUT)
                self.arduino.digitalWrite(pin, LOW)

    def apagar(self):
        """Realiza la tarea de apagar el dispositivo de alarma"""
        if self.estado != "NO CONFIGURACION":
            for _, pin in self.configuracion.leds.items():
                self.arduino.digitalWrite(pin, LOW)
            self.estado = "APAGADA"

    def alerta_azul(self) -> None:
        if self.estado != "NO CONFIGURACION":
            self.apagar()

            # Ahora encendemos el azul
            azul = self.configuracion.pin("azul")
            self.arduino.digitalWrite(azul, HIGH)
            self.estado = "APAGADA"

    def alerta_verde(self):
        """Apaga los leds, dejando solo el led verde"""
        if self.estado != "NO CONFIGURACION":
            # Apagamos los diversos elementos
            self.apagar()

            # Ahora encendemos el verde
            verde = self.configuracion.pin("verde")
            self.arduino.digitalWrite(verde, HIGH)

            # Cambiamos la configuración
            self.estado = "ALERTA_VERDE"

    def alerta_naranja(self, alarma_sonora: bool = False):
        """
        Enciende el led naranja del arduino, y enciende la alarma sonora de
        acuerdo con el valor del parámetro
        """
        if self.estado != "NO CONFIGURACION":

            self.apagar()
            # Encendemos el led naranja
            rojo = self.configuracion.pin('rojo')
            verde = self.configuracion.pin('verde')
            azul = self.configuracion.pin('azul')
            zumbador = self.configuracion.pin('zumbador')

            self.arduino.analogWrite(rojo, 255)
            self.arduino.analogWrite(verde, 80)
            self.arduino.analogWrite(azul, 0)

            # Encendemos la alarma sonora
            if alarma_sonora:
                self.arduino.digitalWrite(zumbador, HIGH)
            else:
                self.arduino.digitalWrite(zumbador, LOW)

            self.estado = "ALERTA_NARANJA"

    def alerta_roja(self, alarma_sonora: bool = False):
        """
        Enciende el led naranja del arduino, y enciende la alarma sonora de
        acuerdo con el valor del parámetro
        """
        if self.estado != "NO CONFIGURACION":

            self.apagar()
            # Encendemos el led naranja
            rojo = self.configuracion.pin('rojo')
            zumbador = self.configuracion.pin('zumbador')

            self.arduino.digitalWrite(rojo, HIGH)

            if alarma_sonora:
                self.arduino.digitalWrite(zumbador, HIGH)
            else:
                self.arduino.digitalWrite(zumbador, LOW)

            self.estado = "ALERTA_ROJA"

    def puerto(self) -> str:
        """
        Obtiene el puerto donde está conectado el dispositivo
        """
        if self.estado != "NO CONFIGURACION":
            return self.configuracion.puerto_arduino_alarmas
        
        return "NO PUERTO!"

# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------
# Clase para obtener los elementos de los argumentos en
# la línea de comandos.
# -------------------------------------------------------

class Argumentos:

    def __init__(self) -> None:
        # Objeto para parsear los argumentos
        parser = argparse.ArgumentParser()

        # Configurar las opciones de la linea de comando
        parser.add_argument('--configuracion', required=False,
                            help='Ruta al archivo de configuración de la aplicación',
                            default='./preventlink.ini')
        
        parser.add_argument('--tomar-foto', required=False,
                            help='La aplicación solo tomará la foto y finalizará',
                            action='store_true')
        
        parser.add_argument('--archivo-salida', required=False,
                            help='Nombre del archivo donde se almacenará la foto tomada',
                            default='./imagenes/foto.jpg')
        
        parser.add_argument('--detectar-epps', required=False,
                            help='Permite tomar una foto y mostrar los EPPs detectados',
                            action='store_true')
        
        # Obtener los valores de la línea de comandos
        self.argumentos = parser.parse_args()

    
    def archivo_configuracion(self) -> str:
        return self.argumentos.configuracion
    
    def archivo_salida_foto(self) -> str:
        return self.argumentos.archivo_salida
    
    def tomar_foto(self) -> bool:
        return self.argumentos.tomar_foto
        
    def detectar_epps(self) -> bool:
        return self.argumentos.detectar_epps
    

