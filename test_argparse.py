import argparse

# Construct the argument parser
ap = argparse.ArgumentParser()

# Add the arguments to the parser
ap.add_argument("-a", "--foperand", required=False,
   help="first operand")
ap.add_argument("-b", "--soperand", required=False,
   help="second operand")
ap.add_argument("-f", "--configuracion", required=False,
                help='Ruta del archivo de configuracion',
                default='./preventlink.ini')

ap.add_argument('-o', '--archivo-salida', required=False,
                help='Ruta al archivo de salida para la foto',
                default='./imagenes/foto.jpg')

ap.add_argument('-y', '--tomar-foto', required=False,
                help='La aplicación tomará una foto de acuerdo con la configuración',
                action='store_true')

res = ap.parse_args()

print(vars(res))
