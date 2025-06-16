from flask import Flask
from flask_cors import CORS #para realizar las solicitudes entre el FRONT y el BACK
from user_system.login import auth_bp #Importamos el blueprint es una forma de organizar el código de Flask en módulos reutilizables y separados.
from user_system.user.registro_usuario import registro_bp
from user_system.asign_Permissions import asign_bp
from routes.upload import upload_bp
from utils.visor_archivo import visor_bp
app = Flask(__name__)
CORS(app)  # peticiones desde el frontend (Vue)

# Registro de blueprints
# #cada nuevo modulo requiere irse agregando aqui
app.register_blueprint(auth_bp)
app.register_blueprint(registro_bp)
app.register_blueprint(asign_bp)#asignar permisos
# guardar fotos
app.register_blueprint(upload_bp)
# consultar fotos
app.register_blueprint(visor_bp)




if __name__ == '__main__':
    app.run(debug=True, port=5000)

