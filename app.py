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
    
    # Récupérer la VRAIE adresse IP derrière le proxy de Render
    if request.headers.getlist("X-Forwarded-For"):
        real_ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        real_ip = request.remote_addr
    
    new_visit = Visit(
        ip_address=real_ip,
        # On garde l'action et on s'assure qu'elle ne dépasse pas les 50 caractères de la BDD
        action=data.get('action', 'pageview')[:50],
        user_agent=data.get('userAgent', '')[:500]
    )
    db.session.add(new_visit)
    db.session.commit()
    
    return jsonify({'status': 'success'}), 201

# 6. Route Privée : Tableau de bord
@app.route('/admin')
@requires_auth
def admin():
    # Récupérer les 200 dernières actions
    visits = Visit.query.order_by(Visit.timestamp.desc()).limit(200).all()
    
    # Logique Python : Regrouper les visites par adresse IP
    grouped_visits = {}
    for v in visits:
        if v.ip_address not in grouped_visits:
            grouped_visits[v.ip_address] = {
                'actions': [],
                'user_agent': v.user_agent # On garde l'info du navigateur
            }
        grouped_visits[v.ip_address]['actions'].append(v)
    
    # Template HTML mis à jour (100% Responsive Mobile)
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <!-- Balise indispensable pour le responsive mobile -->
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard Admin | Portfolio</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-dark text-light p-2 p-md-4">
        <div class="container-fluid container-md">
            <h2 class="text-success mb-4 fs-3 fs-md-2">Parcours des Visiteurs</h2>
            
            {% for ip, data in grouped_visits.items() %}
            <div class="card bg-black border-secondary mb-4 shadow-sm">
                <!-- En-tête de la carte (s'adapte si l'IP est longue) -->
                <div class="card-header border-secondary d-flex flex-wrap justify-content-between align-items-center bg-dark gap-2">
                    <span class="text-warning fw-bold text-break">🌍 IP : {{ ip }}</span>
                    <span class="badge bg-secondary">{{ data.actions|length }} événements</span>
                </div>
                
                <div class="card-body py-3">
                    <!-- Info navigateur avec text-break pour éviter de casser l'écran -->
                    <p class="small text-white-50 mb-3 border-bottom border-secondary pb-2 text-break">
                        💻 {{ data.user_agent[:100] }}...
                    </p>
                    
                    <!-- Liste des actions en Flexbox (remplace le tableau) -->
                    <div class="d-flex flex-column gap-2">
                        {% for v in data.actions %}
                        <div class="d-flex flex-column flex-sm-row justify-content-start align-items-sm-center gap-1 gap-sm-3">
                            <span class="text-muted small" style="min-width: 170px;">
                                {{ v.timestamp.strftime('%H:%M:%S (%Y-%m-%d)') }}
                            </span>
                            <span>
                                <span class="badge 
                                    {% if v.action == 'cv_download' %}bg-warning text-dark
                                    {% elif 'lu_' in v.action %}bg-info text-dark
                                    {% elif 'tps_' in v.action %}bg-secondary
                                    {% else %}bg-success{% endif %}">
                                    {{ v.action }}
                                </span>
                            </span>
                        </div>
                        {% endfor %}
                    </div>
                    
                </div>
            </div>
            {% endfor %}
            
        </div>
    </body>
    </html>
    """
    return render_template_string(html, grouped_visits=grouped_visits)
    
if __name__ == '__main__':
    app.run(debug=True)
