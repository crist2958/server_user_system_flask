import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuración del correo
remitente = 'cristhian.cabrera31@unach.mx'
destinatario = 'cristia2958@gmail.com'
asunto = 'Resumen semanal de actividad'
password = 'kzol sycl engr vfte'

# Crear mensaje
mensaje = MIMEMultipart('alternative')
mensaje['From'] = remitente
mensaje['To'] = destinatario
mensaje['Subject'] = asunto

# HTML con estilo profesional
html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CompuSur - Credenciales de Acceso</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Times New Roman', serif;
            background-color: #ffffff;
            line-height: 1.6;
            color: #333333;
        }

        .document-container {
            max-width: 700px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 60px 50px;
            border: 1px solid #e6e6e6;
        }

        .header {
            border-bottom: 3px solid #2c5aa0;
            padding-bottom: 30px;
            margin-bottom: 40px;
        }

        .company-logo {
            font-size: 2.8rem;
            font-weight: 700;
            color: #2c5aa0;
            margin-bottom: 5px;
            letter-spacing: 2px;
        }

        .company-subtitle {
            font-size: 1rem;
            color: #666666;
            font-weight: 400;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .document-title {
            font-size: 1.8rem;
            font-weight: 600;
            color: #2c5aa0;
            text-align: center;
            margin: 40px 0 30px 0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .document-date {
            text-align: right;
            color: #666666;
            font-size: 0.95rem;
            margin-bottom: 30px;
            font-style: italic;
        }

        .content-section {
            margin-bottom: 35px;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #2c5aa0;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #e6e6e6;
        }

        .paragraph {
            font-size: 1rem;
            color: #333333;
            margin-bottom: 15px;
            text-align: justify;
        }

        .credentials-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            background-color: #fafafa;
            border: 1px solid #e6e6e6;
            border-radius: 8px;
            overflow: hidden;
        }

        .credentials-table th {
            background-color: #2c5aa0;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 1rem;
        }

        .credentials-table td {
            padding: 15px;
            border-bottom: 1px solid #e6e6e6;
            font-size: 0.95rem;
        }

        .credential-label {
            font-weight: 600;
            color: #333333;
            width: 40%;
        }

        .credential-value {
            font-family: 'Courier New', monospace;
            background-color: #f8f9fa;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #e6e6e6;
            color: #2c5aa0;
            font-weight: 500;
        }

        .access-section {
            text-align: center;
            margin: 40px 0;
            padding: 30px;
            background-color: #f8f9fa;
            border-left: 4px solid #2c5aa0;
            border-radius: 8px;
        }

        .access-button {
            display: inline-block;
            background-color: #2c5aa0;
            color: white;
            text-decoration: none;
            padding: 14px 35px;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 2px solid #2c5aa0;
        }

        .important-notice {
            background-color: #f8f9fa;
            border: 1px solid #e6e6e6;
            border-left: 4px solid #2c5aa0;
            border-radius: 8px;
            padding: 25px;
            margin: 30px 0;
        }

        .important-notice h4 {
            color: #2c5aa0;
            margin-bottom: 15px;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .notice-list {
            list-style: none;
            padding-left: 0;
        }

        .notice-list li {
            margin-bottom: 10px;
            padding-left: 20px;
            position: relative;
        }

        .notice-list li:before {
            content: "•";
            color: #2c5aa0;
            font-weight: bold;
            position: absolute;
            left: 0;
        }

        .signature-section {
            margin-top: 50px;
            padding-top: 30px;
            border-top: 1px solid #e6e6e6;
        }

        .signature-line {
            text-align: center;
            margin-bottom: 50px;
        }

        .signature-name {
            font-weight: 600;
            color: #2c5aa0;
            font-size: 1.1rem;
        }

        .signature-title {
            color: #666666;
            font-size: 0.9rem;
            margin-top: 5px;
        }

        .footer {
            text-align: center;
            padding-top: 30px;
            border-top: 1px solid #e6e6e6;
            color: #666666;
            font-size: 0.85rem;
            line-height: 1.4;
        }

        .highlight {
            color: #2c5aa0;
            font-weight: 600;
        }

        /* Responsive */
        @media only screen and (max-width: 600px) {
            .document-container {
                padding: 40px 25px !important;
                margin: 0 !important;
            }

            .company-logo {
                font-size: 2.2rem !important;
            }

            .document-title {
                font-size: 1.4rem !important;
            }

            .credentials-table th,
            .credentials-table td {
                padding: 12px 8px !important;
                font-size: 0.85rem !important;
            }

            .credential-label {
                width: 35% !important;
            }
        }
    </style>
</head>
<body>
    <div class="document-container">
        <!-- Header -->
        <div class="header">
            <div class="company-logo">COMPUSUR</div>
            <div class="company-subtitle">Sistema Empresarial</div>
        </div>

        <!-- Document Title -->
        <h1 class="document-title">Notificación de Credenciales de Acceso</h1>

        <!-- Date -->
        <div class="document-date">
            Fecha: {{fecha}}
        </div>

        <!-- Welcome Section -->
        <div class="content-section">
            <h2 class="section-title">Estimado Usuario</h2>
            <p class="paragraph">
                Por medio del presente documento, le informamos que su cuenta de usuario ha sido 
                <span class="highlight">creada exitosamente</span> en el Sistema Empresarial CompuSur.
            </p>
            <p class="paragraph">
                A continuación se detallan las credenciales de acceso que le permitirán ingresar 
                a la plataforma y utilizar todos los servicios disponibles del sistema.
            </p>
        </div>

        <!-- Credentials Section -->
        <div class="content-section">
            <h2 class="section-title">Credenciales de Acceso</h2>

            <table class="credentials-table">
                <thead>
                    <tr>
                        <th colspan="2">Información de Acceso al Sistema</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="credential-label">Correo Electrónico:</td>
                        <td><span class="credential-value">{{email}}</span></td>
                    </tr>
                    <tr>
                        <td class="credential-label">Contraseña:</td>
                        <td><span class="credential-value">{{password}}</span></td>
                    </tr>
                    <tr>
                        <td class="credential-label">URL de Acceso:</td>
                        <td><span class="credential-value">{{login_url}}</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Access Section -->
        <div class="access-section">
            <p style="margin-bottom: 20px; color: #666666;">
                Para acceder al sistema, utilice el siguiente enlace:
            </p>
            <a href="{{login_url}}" class="access-button">
                Acceder al Sistema
            </a>
        </div>

        <!-- Important Notice -->
        <div class="important-notice">
            <h4>Disposiciones Importantes</h4>
            <ul class="notice-list">
                <li>Las credenciales proporcionadas son de carácter <strong>confidencial</strong> y de uso exclusivo del usuario asignado.</li>
                <li>Se recomienda encarecidamente cambiar la contraseña temporal en el primer acceso al sistema.</li>
                <li>No comparta sus credenciales con terceros bajo ninguna circunstancia.</li>
                <li>En caso de inconvenientes técnicos, contacte al departamento de soporte técnico.</li>
                <li>Este documento debe ser conservado en lugar seguro para futuras referencias.</li>
            </ul>
        </div>

        <!-- Instructions Section -->
        <div class="content-section">
            <h2 class="section-title">Instrucciones de Uso</h2>
            <p class="paragraph">
                Para acceder al sistema, ingrese a la URL proporcionada e introduzca las credenciales 
                especificadas en este documento. Una vez dentro del sistema, podrá acceder a todas 
                las funcionalidades según los permisos asignados a su perfil de usuario.
            </p>
        </div>

        <!-- Signature Section -->
        <div class="signature-section">
            <div class="signature-line">
                <div class="signature-name">Departamento de Sistemas</div>
                <div class="signature-title">CompuSur - Sistema Empresarial</div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p><strong>COMPUSUR - Sistema Empresarial</strong></p>
            <p>Este es un documento generado automáticamente. No responda a este correo.</p>
            <p>Para soporte técnico, contacte al administrador del sistema.</p>
        </div>
    </div>
</body>
</html>
"""

# Adjuntar el contenido HTML al mensaje
parte_html = MIMEText(html, 'html')
mensaje.attach(parte_html)

# Enviar el correo
try:
    servidor = smtplib.SMTP('smtp.gmail.com', 587)
    servidor.starttls()
    servidor.login(remitente, password)
    servidor.send_message(mensaje)
    servidor.quit()
    print("Correo profesional enviado con éxito.")
except Exception as e:
    print("Error al enviar el correo:", e)
