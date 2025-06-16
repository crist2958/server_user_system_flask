from flask import Flask
from flask_cors import CORS #para realizar las solicitudes entre el FRONT y el BACK
from user_system.login import auth_bp #Importamos el blueprint es una forma de organizar el código de Flask en módulos reutilizables y separados.
from user_system.user.registro_usuario import registro_bp
from user_system.asign_Permissions import asign_bp

app = Flask(__name__)
CORS(app)  # peticiones desde el frontend (Vue)

# Registro de blueprints
# #cada nuevo modulo requiere irse agregando aqui
app.register_blueprint(auth_bp)
app.register_blueprint(registro_bp)
app.register_blueprint(asign_bp)#asignar permisos


if __name__ == '__main__':
    app.run(debug=True, port=5000)

