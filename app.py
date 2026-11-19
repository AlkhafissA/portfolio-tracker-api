from flask import Flask, request, jsonify, render_template_string, Response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
from functools import wraps


app = Flask(__name__)

@app.route('/')
@app.route('/ping')
def health_check():
    return "OK", 200

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

# 6. Route Privée : Tableau de bord (Design Moderne - UI/UX Premium)
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
                'user_agent': v.user_agent
            }
        grouped_visits[v.ip_address]['actions'].append(v)
    
    # Template HTML (Timeline, Glassmorphism, Premium Dark Mode)
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analytics | Portfolio</title>
        <!-- Bootstrap 5 -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Police Google Inter -->
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <!-- FontAwesome -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        
        <style>
            :root {
                --bg-main: #0f172a;       /* Slate 900 */
                --bg-card: #1e293b;       /* Slate 800 */
                --border-color: #334155;  /* Slate 700 */
                --text-main: #f8fafc;     /* Slate 50 */
                --text-muted: #94a3b8;    /* Slate 400 */
            }
            
            body {
                background-color: var(--bg-main);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                -webkit-font-smoothing: antialiased;
            }
            
            /* Titre avec gradient */
            .dashboard-title {
                background: linear-gradient(90deg, #34d399, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700;
                letter-spacing: -0.5px;
            }
            
            /* Cartes Utilisateurs */
            .visitor-card {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: transform 0.2s ease, border-color 0.2s ease;
            }
            .visitor-card:hover {
                transform: translateY(-2px);
                border-color: #475569;
            }
            
            .card-header-custom {
                background-color: rgba(15, 23, 42, 0.4);
                border-bottom: 1px solid var(--border-color);
                border-radius: 16px 16px 0 0;
                padding: 1rem 1.5rem;
            }

            .user-agent-text {
                font-size: 0.85rem;
                color: var(--text-muted);
                background: rgba(15, 23, 42, 0.3);
                padding: 10px 15px;
                border-radius: 8px;
                border: 1px solid var(--border-color);
            }

            /* Design de la Timeline (Ligne de temps) */
            .timeline-container {
                padding: 1rem 1.5rem;
            }
            .timeline {
                border-left: 2px solid var(--border-color);
                margin-left: 10px;
                padding-left: 25px;
                position: relative;
            }
            .timeline-item {
                position: relative;
                margin-bottom: 1.25rem;
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 10px;
            }
            .timeline-item:last-child {
                margin-bottom: 0;
            }
            /* Point sur la ligne */
            .timeline-icon {
                position: absolute;
                left: -32px;
                top: 50%;
                transform: translateY(-50%);
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background-color: var(--bg-card);
                border: 2px solid #64748b;
                z-index: 2;
            }
            /* Point de couleur spécifique selon l'action */
            .timeline-item.type-cv .timeline-icon { border-color: #fbbf24; box-shadow: 0 0 8px rgba(251, 191, 36, 0.4); }
            .timeline-item.type-read .timeline-icon { border-color: #38bdf8; box-shadow: 0 0 8px rgba(56, 189, 248, 0.4); }
            .timeline-item.type-time .timeline-icon { border-color: #a855f7; box-shadow: 0 0 8px rgba(168, 85, 247, 0.4); }
            .timeline-item.type-page .timeline-icon { border-color: #34d399; box-shadow: 0 0 8px rgba(52, 211, 153, 0.4); }

            .time-label {
                font-size: 0.85rem;
                color: var(--text-muted);
                min-width: 140px;
                font-variant-numeric: tabular-nums;
            }

            /* Badges Translucides Premium */
            .badge-custom {
                font-size: 0.75rem;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: 600;
                letter-spacing: 0.5px;
                text-transform: uppercase;
            }
            .bg-cv { background-color: rgba(251, 191, 36, 0.15); color: #fcd34d; border: 1px solid rgba(251, 191, 36, 0.3); }
            .bg-page { background-color: rgba(52, 211, 153, 0.15); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.3); }
            .bg-read { background-color: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.3); }
            .bg-time { background-color: rgba(168, 85, 247, 0.15); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.3); }
        </style>
    </head>
    <body class="p-3 p-md-5">
        <div class="container-fluid container-md max-w-4xl">
            
            <div class="d-flex justify-content-between align-items-center mb-5">
                <h2 class="dashboard-title fs-2 m-0"><i class="fas fa-chart-network me-2"></i>Live Analytics</h2>
                <span class="badge bg-primary rounded-pill px-3 py-2 bg-opacity-25 border border-primary text-primary">
                    {{ grouped_visits|length }} Visiteurs Uniques
                </span>
            </div>
            
            {% for ip, data in grouped_visits.items() %}
            <div class="visitor-card mb-4">
                
                <!-- En-tête -->
                <div class="card-header-custom d-flex flex-wrap justify-content-between align-items-center gap-3">
                    <div class="d-flex align-items-center gap-2">
                        <div class="bg-dark rounded-circle d-flex justify-content-center align-items-center" style="width: 35px; height: 35px; border: 1px solid #334155;">
                            <i class="fas fa-globe text-info"></i>
                        </div>
                        <span class="fs-5 fw-bold text-white tracking-wide">{{ ip }}</span>
                    </div>
                    <span class="badge bg-secondary bg-opacity-25 text-light border border-secondary rounded-pill px-3">
                        <i class="fas fa-bolt me-1 text-warning"></i> {{ data.actions|length }} actions
                    </span>
                </div>
                
                <!-- Contenu : User Agent & Timeline -->
                <div class="timeline-container">
                    
                    <div class="user-agent-text mb-4 text-break">
                        <i class="fas fa-laptop-code me-2 text-primary"></i> 
                        {{ data.user_agent }}
                    </div>
                    
                    <div class="timeline">
                        {% for v in data.actions %}
                        
                        <!-- Détermination du type pour la couleur CSS -->
                        {% set type_class = 'type-page' %}
                        {% set badge_class = 'bg-page' %}
                        {% set icon = 'fa-eye' %}
                        
                        {% if v.action == 'cv_download' %}
                            {% set type_class = 'type-cv' %}
                            {% set badge_class = 'bg-cv' %}
                            {% set icon = 'fa-file-pdf' %}
                        {% elif 'lu_' in v.action %}
                            {% set type_class = 'type-read' %}
                            {% set badge_class = 'bg-read' %}
                            {% set icon = 'fa-book-open' %}
                        {% elif 'tps_' in v.action %}
                            {% set type_class = 'type-time' %}
                            {% set badge_class = 'bg-time' %}
                            {% set icon = 'fa-clock' %}
                        {% endif %}

                        <div class="timeline-item {{ type_class }}">
                            <div class="timeline-icon"></div>
                            <span class="time-label">
                                {{ v.timestamp.strftime('%H:%M:%S') }} <span class="text-muted small ms-1">{{ v.timestamp.strftime('%d/%m') }}</span>
                            </span>
                            <span class="badge-custom {{ badge_class }}">
                                <i class="fas {{ icon }} me-1"></i> {{ v.action|replace('_', ' ') }}
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
