# -------------------------------------------------------
# En este módulo vamos a desarrollar la tarea de detectar
# los EPPs asociados a una imagen tomado desde un archivo
#
# Autor: Luis Cobo
# Proyecto: PreventLink
# -------------------------------------------------------

from utils import Configuracion, Maquina, DispositivoAlarma
from ultralytics import YOLO
from enum import Enum

# Camaras
from picamera2 import Picamera2, Preview
import cv2

import time

# -------------------------------------------------------
# Constantes
# -------------------------------------------------------

CAMERA_FRAME_WIDTH  = 3
CAMERA_FRAME_HEIGHT = 4


# -------------------------------------------------------
# Constantes: Posibles estados de la maquina
# -------------------------------------------------------

class Estado(Enum):
    EN_PROCESO = -1
    INICIAL = 0
    HABILITADO = 1
    ALARMA = 2
    ERROR = 3


# -------------------------------------------------------
# Constantes: Los diversos tipos de EPPs para este modelo
# -------------------------------------------------------

class EPP(Enum):
    NOTHING = -1
    HELMET = 0
    SHIELD = 1
    JACKET = 2
    DUST_MASK = 3
    EYE_WEAR = 4
    GLOVE = 5
    BOOTS = 6

    def nombre(self) -> str:
        """
        Permite obtener el nombre del EPP
        """
        diccionario = {0: 'Protective Helmet', 1: 'Shield', 2: 'Jacket', 3: 'Dust Mask', 4: 'Eye Wear', 5: 'Glove', 6: 'Protective Boots'}
        if self.value >= 0:
            return diccionario[self.value]
        
        return None


# -------------------------------------------------------
# Esta clase realiza la captura de imágenes a través de
# la cámara conectada al GPIO
# -------------------------------------------------------

class Camara:

    def __init__(self, configuracion: Configuracion) -> None:
        self.camara = None
        self.configuracion = configuracion
        if configuracion.camara_valida:
            if configuracion.camara == 'picamera':
                self.camara = Picamera2(camera_num=configuracion.numero_camara)
                cam_config = self.camara.create_still_configuration(main={"size": (configuracion.ancho_imagen, configuracion.alto_imagen)})
                self.camara.configure(camera_config=cam_config)
                self.camara.start_preview(Preview.NULL)
                self.camara.start()
                time.sleep(2)
            elif configuracion.camara == 'usbcamera':
                self.camara = cv2.VideoCapture(configuracion.numero_camara)
                self.camara.set(CAMERA_FRAME_HEIGHT, configuracion.alto_imagen)
                self.camara.set(CAMERA_FRAME_WIDTH, configuracion.ancho_imagen)


    def es_valida(self) -> bool:
        return not (self.camara is None)
    

    def camara_usb(self) -> bool:
        return self.es_valida() and self.configuracion.camara == 'usbcamera'
    
    def camara_pi(self) -> bool:
        return self.es_valida() and self.configuracion.camara == 'picamera'

    def tomar_foto(self) -> str:
        """
        Toma una foto y la guarda en un archivo de acuerdo a la configuracion establecida
        Retorna el nombre del archivo donde se almacenó el archivo
        """
        if not self.es_valida():
            return None
        
        n = 0
        if self.configuracion.guardar_imagenes:
            n = int(time.time()*100)
        nombre_archivo = f'{self.configuracion.carpeta_imagenes}/{self.configuracion.prefijo_imagenes}-{n}.jpg'

        if self.camara_usb():
            resultado, imagen = self.camara.read()
            if resultado:
                cv2.imwrite(nombre_archivo, imagen)
                return nombre_archivo
            else:
                return None
        else:
            self.camara.capture_file(nombre_archivo)
            return nombre_archivo
        
    
    def finalizar(self) -> None:
        if self.es_valida():
            if self.camara_usb():
                self.camara.release()
            else:
                self.camara.close()

# -------------------------------------------------------
# Esta clase realiza la detección de EPPs asociados a una
# máquina dada.
# -------------------------------------------------------

class DetectorEPPs:

    def __init__(self, configuracion: Configuracion) -> None:
        self.configuracion = configuracion
        self.maquina = None
        self.dispositivo_alarma = None
        self.estado = Estado.EN_PROCESO
        self.epps_configurados = []
        self.modelo = None
        self.tiempo_ultima_deteccion = time.time()
        self.tiempo = time.time()
        self.camara = None

        if self.configuracion.es_valido:
            for epp in self.configuracion.epps:
                self.epps_configurados.append(EPP(epp))

            # Obtener la configuracion de la máquina
            if self.configuracion.tiene_reles:
                self.maquina = Maquina(config=self.configuracion)

            # Obtener la configuracion del dispositivo de alarma
            if self.configuracion.tiene_alarmas:
                self.dispositivo_alarma = DispositivoAlarma(configuracion=self.configuracion)

            # Ahora vamos a configurar la camara
            if self.configuracion.tiene_camara:
                self.camara = Camara(configuracion=self.configuracion)

            # Crear el predictor del modelo
            if not (self.configuracion.modelo is None):
                self.modelo = YOLO(self.configuracion.modelo)


    def tomar_foto(self) -> str:
        if self.camara is None:
            return None 
        
        return self.camara.tomar_foto()

    
    def detectar_epp(self, imagen: str) -> list[EPP]:
        """
        Permite obtener una lista con los diversos EPPs detectados
        """
        if self.modelo is None:
            return None
        
        # Procedemos a realizar la detección
        resultados = self.modelo.predict(source=imagen, save=self.configuracion.guardar_imagenes, conf=self.configuracion.confianza_minima, save_txt=self.configuracion.guardar_texto)
        respuesta = list()
        for res in resultados:
            clases = res.boxes.cls
            for c in clases:
                # Aquí pueden haber muchas clases
                epp = EPP(int(c))
                respuesta.append(epp)
        
        # Retornar la respuesta
        self.tiempo_ultima_deteccion = time.time()
        return respuesta
        

    def es_valido(self) -> bool:
        """
        Permite saber si este detector es valido o no
        """
        return not(self.modelo is None)
        

    def detecto_todos_los_epps_configurados(self, epps_detectados: list[EPP]) -> bool:
        if (epps_detectados is None) or (len(epps_detectados) == 0) or (len(epps_detectados) < len(self.epps_configurados)):
            return False
        
        for epp in self.epps_configurados:
            if not(epp in epps_detectados):
                return False
            
        return True
    

    def encender_maquina(self) -> None:
        if not (self.maquina is None):
            self.maquina.encender()


    def apagar_maquina(self) -> None:
        if not (self.maquina is None):
            self.maquina.apagar()

    
    def apagar_alarma(self) -> None:
        if not (self.dispositivo_alarma is None):
            self.dispositivo_alarma.alerta_azul()

    def alarma_ok(self) -> None:
        if not (self.dispositivo_alarma is None):
            self.dispositivo_alarma.alerta_verde()

    def alarma_advertencia(self) -> None:
        if not (self.dispositivo_alarma is None):
            self.dispositivo_alarma.alerta_naranja()

    def alarma_error(self) -> None:
        if not (self.dispositivo_alarma is None):
            self.dispositivo_alarma.alerta_roja(alarma_sonora=True)

    def han_pasado_quince_segundos(self) -> bool:
        return time.time() - self.tiempo >= 15.0
    

    def maquina_apagada(self) -> bool:
        if self.maquina is None:
            return None
        return self.maquina.estado == "APAGADA"
    
    def maquina_encendida(self) -> bool:
        if self.maquina is None:
            return None
        return self.maquina.estado == "ENCENDIDA"
    

    def alarma_apagada(self) -> bool:
        if self.dispositivo_alarma is None:
            return None
        return self.dispositivo_alarma.estado == "APAGADA"
    
    def alarma_esta_ok(self) -> bool:
        if self.dispositivo_alarma is None:
            return None
        return self.dispositivo_alarma.estado == "ALERTA_VERDE"


    def proceso(self) -> None:
        """
        Realiza todo el proceso de trabajo de PreventLink
        """
        if not self.es_valido():
            return

        # Iniciamos la comunicación con las máquinas y el dispositivo de alarma
        self.apagar_alarma()
        self.apagar_maquina()
        self.estado = Estado.INICIAL

        # Ahora viene todo el diagrama de flujo
        while True:
            print('Tomando foto')
            imagen = self.tomar_foto()
            print(f'Foto {imagen}')
            if not (imagen is None):
                print('Detectando')
                epps_detectados = self.detectar_epp(imagen)
                if not (epps_detectados is None):
                    print(f'EPPs detectado = {epps_detectados}')
                    if self.estado == Estado.INICIAL:
                        if self.detecto_todos_los_epps_configurados(epps_detectados):
                            print(f"Estado: {self.estado} Todos EPPS Detectado.->Habilitando maquina")
                            self.estado = Estado.HABILITADO
                            self.encender_maquina()
                            self.alarma_ok()
                            print("Maquina habilitada!")
                        else:
                            self.apagar_maquina()
                            self.apagar_alarma()
                    elif self.estado == Estado.HABILITADO:
                        if self.detecto_todos_los_epps_configurados(epps_detectados):
                            print('TODO OK!')
                            if self.maquina_apagada():
                                self.encender_maquina()
                            if self.alarma_apagada():
                                self.alarma_ok()
                        else:
                            print("Alarma!")
                            self.estado = Estado.ALARMA
                            self.tiempo = time.time()
                            if self.alarma_esta_ok():
                                self.alarma_advertencia()
                    elif self.estado == Estado.ALARMA:
                        if self.detecto_todos_los_epps_configurados(epps_detectados):
                            print("TODO OK -> Pasando a Normal otra vez")
                            self.estado = Estado.HABILITADO
                            self.encender_maquina()
                            self.alarma_ok()
                        else:
                            if self.han_pasado_quince_segundos():
                                self.estado = Estado.ERROR
                                self.tiempo = time.time()
                                self.alarma_error()
                            else:
                                self.alarma_advertencia()
                    elif self.estado == Estado.ERROR:
                        print("Estado: ERROR")
                        if self.detecto_todos_los_epps_configurados(epps_detectados):
                            print("TODO OK -> Pasando a Normal otra vez")
                            self.estado = Estado.HABILITADO
                            self.encender_maquina()
                            self.alarma_ok()
                        else:
                            if self.han_pasado_quince_segundos():
                                print("Apagando máquina!")
                                self.estado = Estado.INICIAL
                                self.tiempo = time.time()
                                self.apagar_maquina()
                                self.alarma_apagada()
                            else:
                                self.alarma_error()



if __name__ == '__main__':
    conf = Configuracion()
    detector = DetectorEPPs(configuracion=conf)
    detector.proceso()
        