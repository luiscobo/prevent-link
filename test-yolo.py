# Vamos a probar el esquema de predicción de YOLO
from utils import Configuracion
from ultralytics import YOLO

# Programa principal
# ---------------------------------------------
if __name__ == '__main__':
    conf = Configuracion()
    print(conf.ARCHIVO_CONFIGURACION)
    print(conf.modelo)

    if not (conf.modelo is None):
        model = YOLO(conf.modelo)

        results = model.predict(source='./imagenes/foto-epp-01.jpg', save=False, conf=0.5)
        for result in results:
            print(result.boxes)
