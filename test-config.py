from utils import Configuracion, DispositivoAlarma, Maquina
import time

# --------------------------------------------------
# Programa Principal

if __name__ == '__main__':
    conf = Configuracion()
    print(f'Tiene relés? {conf.tiene_reles}')

    maq = Maquina(config=conf)
    print(f'Puerto de los relés: {maq.puerto()}')
    print(f'Apagando OFF={maq.OFF}')
    maq.apagar()
    time.sleep(5)

    print('Encendiendo')
    maq.encender()
    print(f'Estado máquina: {maq.estado}')
    time.sleep(5)

    print('Apagando')
    maq.apagar()
    print(f'Estado máquina: {maq.estado}')
 