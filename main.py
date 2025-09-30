from flask import Flask
from flask_cors import CORS
from user_system.login import auth_bp
from user_system.user.registro_usuario import registro_bp, usuarios_bp, procedures_bp, archivos_bp
from user_system.asign_Permissions import asign_bp
from routes.upload import upload_bp
from utils.visor_archivo import visor_bp
from user_system.role_controller import roles_bp
from client.clientes_empresas import empresas_bp
from client.clientes_personas import personas_bp
from product_system.productos import (
    categorias_bp, 
    proveedores_bp,
    contactos_bp,
    productos_bp,
    archivos_productos_bp  # Importar el nuevo blueprint
)
from product_system.sales.cotizaciones import cotizaciones_bp
from agendCalendar.agenda_evidencias import agenda_bp, archivos_agenda_bp


app = Flask(__name__)
CORS(app)

# Si tu app usa prefijo '/api' para rutas REST:
app.register_blueprint(agenda_bp, url_prefix='/api')
# Para mantener las rutas de archivos sin prefijo (igual que /archivo/usuarios/...):
app.register_blueprint(archivos_agenda_bp)  # expone /archivo/agenda/<id_item>/<id_archivo>
app.register_blueprint(cotizaciones_bp, url_prefix='/api')
app.register_blueprint(categorias_bp, url_prefix='/api')
app.register_blueprint(proveedores_bp, url_prefix='/api')
app.register_blueprint(contactos_bp, url_prefix='/api')
app.register_blueprint(productos_bp, url_prefix='/api')
app.register_blueprint(archivos_productos_bp)  # Registrar sin prefijo para mantener la ruta /archivo/...

# Registrar todos los blueprints con prefijo /api
app.register_blueprint(procedures_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(registro_bp, url_prefix='/api')
app.register_blueprint(usuarios_bp, url_prefix='/api')
app.register_blueprint(asign_bp, url_prefix='/api')
app.register_blueprint(upload_bp, url_prefix='/api')
app.register_blueprint(visor_bp, url_prefix='/api')
app.register_blueprint(archivos_bp, url_prefix='/api')
app.register_blueprint(roles_bp, url_prefix='/api')
app.register_blueprint(empresas_bp, url_prefix='/api')
app.register_blueprint(personas_bp, url_prefix='/api')

'''
if __name__ == '__main__':
    app.run(debug=True, port=5000)
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
