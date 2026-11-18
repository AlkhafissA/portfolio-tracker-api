from flask import Flask, request, jsonify, render_template_string, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from functools import wraps

app = Flask(__name__)

# 1. Autorise uniquement le portfolio GitHub Pages à envoyer des requêtes
CORS(app, resources={r"/api/*": {"origins": "https://alkhafissa.github.io"}})

# 2. Configuration de la base de données SQLite
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tracker.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///tracker.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 3. Sécurité : Configuration de l'accès Admin
ADMIN_USER = os.environ.get("ADMIN_USER")
ADMIN_PASS = os.environ.get("ADMIN_PASS")

def check_auth(username, password):
    return username == ADMIN_USER and password == ADMIN_PASS

def authenticate():
    return Response(
        'Accès refusé. Identifiants requis.\n', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# 4. Modèle de données
class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50))
    action = db.Column(db.String(50)) # ex: 'pageview', 'cv_download'
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# 5. Route Publique : Réception des données
@app.route('/api/track', methods=['POST'])
def track():
    data = request.json
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400
    
    new_visit = Visit(
        ip_address=request.remote_addr,
        action=data.get('action', 'pageview'),
        user_agent=data.get('userAgent', '')
    )
    db.session.add(new_visit)
    db.session.commit()
    
    return jsonify({'status': 'success'}), 201

# 6. Route Privée : Tableau de bord
@app.route('/admin')
@requires_auth
def admin():
    # Récupérer les 100 dernières actions
    visits = Visit.query.order_by(Visit.timestamp.desc()).limit(100).all()
    
    # Template HTML minimaliste intégré pour éviter d'avoir un dossier templates/
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard Admin | Portfolio</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-light p-5">
        <div class="container">
            <h2 class="text-success mb-4">Statistiques du Portfolio</h2>
            <table class="table table-dark table-striped">
                <thead>
                    <tr>
                        <th>Date & Heure (UTC)</th>
                        <th>Action</th>
                        <th>IP</th>
                        <th>Navigateur / OS</th>
                    </tr>
                </thead>
                <tbody>
                    {% for v in visits %}
                    <tr>
                        <td>{{ v.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                        <td><span class="badge {% if v.action == 'cv_download' %}bg-warning{% else %}bg-success{% endif %}">{{ v.action }}</span></td>
                        <td>{{ v.ip_address }}</td>
                        <td class="small text-white-50">{{ v.user_agent[:60] }}...</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, visits=visits)

if __name__ == '__main__':
    app.run(debug=True)
