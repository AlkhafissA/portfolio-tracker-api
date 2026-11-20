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
    
    # Template HTML (Dashboard 2-panes, Sidebar/Hamburger, JS Toggle)
    html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Analytics | Portfolio</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        
        <style>
            :root {
                --bg-main: #0f172a;       
                --bg-card: #1e293b;       
                --border-color: #334155;  
                --text-main: #f8fafc;     
                --text-muted: #94a3b8;    
            }
            
            body {
                background-color: var(--bg-main);
                color: var(--text-main);
                font-family: 'Inter', sans-serif;
                -webkit-font-smoothing: antialiased;
                overflow-x: hidden;
            }
            
            /* Sidebar Styles */
            .sidebar {
                background-color: var(--bg-card);
                border-right: 1px solid var(--border-color);
                height: 100vh;
                overflow-y: auto;
            }
            .ip-menu-item {
                cursor: pointer;
                padding: 12px 16px;
                border-bottom: 1px solid var(--border-color);
                transition: background 0.2s, color 0.2s;
                color: var(--text-muted);
            }
            .ip-menu-item:hover {
                background-color: rgba(255,255,255,0.05);
            }
            .ip-menu-item.active {
                background: linear-gradient(90deg, rgba(52, 211, 153, 0.1), rgba(59, 130, 246, 0.1));
                border-left: 4px solid #3b82f6;
                color: var(--text-main);
                font-weight: 600;
            }

            .dashboard-title {
                background: linear-gradient(90deg, #34d399, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 700;
            }
            
            /* Cartes Utilisateurs */
            .visitor-view {
                display: none; 
                animation: fadeIn 0.3s ease-in-out;
            }
            .visitor-view.active-view {
                display: block;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .visitor-card {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
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

            /* Timeline */
            .timeline-container { padding: 1rem 1.5rem; }
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
            
            .timeline-item.type-cv .timeline-icon { border-color: #fbbf24; box-shadow: 0 0 8px rgba(251, 191, 36, 0.4); }
            .timeline-item.type-read .timeline-icon { border-color: #38bdf8; box-shadow: 0 0 8px rgba(56, 189, 248, 0.4); }
            .timeline-item.type-time .timeline-icon { border-color: #a855f7; box-shadow: 0 0 8px rgba(168, 85, 247, 0.4); }
            .timeline-item.type-page .timeline-icon { border-color: #34d399; box-shadow: 0 0 8px rgba(52, 211, 153, 0.4); }
            .timeline-item.type-click .timeline-icon { border-color: #fb7185; box-shadow: 0 0 8px rgba(251, 113, 133, 0.4); }

            /* J'ai élargi la largeur minimale ici pour accueillir la date + l'heure */
            .time-label {
                font-size: 0.85rem;
                color: var(--text-muted);
                min-width: 135px; 
                font-variant-numeric: tabular-nums;
            }

            .badge-custom {
                font-size: 0.75rem;
                padding: 6px 12px;
                border-radius: 20px;
                font-weight: 600;
                text-transform: uppercase;
            }
            .bg-cv { background-color: rgba(251, 191, 36, 0.15); color: #fcd34d; border: 1px solid rgba(251, 191, 36, 0.3); }
            .bg-page { background-color: rgba(52, 211, 153, 0.15); color: #6ee7b7; border: 1px solid rgba(52, 211, 153, 0.3); }
            .bg-read { background-color: rgba(56, 189, 248, 0.15); color: #7dd3fc; border: 1px solid rgba(56, 189, 248, 0.3); }
            .bg-time { background-color: rgba(168, 85, 247, 0.15); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.3); }
            .bg-click { background-color: rgba(251, 113, 133, 0.15); color: #fda4af; border: 1px solid rgba(251, 113, 133, 0.3); }

            .offcanvas { background-color: var(--bg-card); color: var(--text-main); }
            .btn-close-white { filter: invert(1) grayscale(100%) brightness(200%); }
        </style>
    </head>
    <body>
        
        <div class="d-md-none bg-card border-bottom border-color p-3 d-flex justify-content-between align-items-center">
            <h2 class="dashboard-title fs-4 m-0"><i class="fas fa-chart-network me-2"></i>Analytics</h2>
            <button class="btn btn-outline-secondary text-white" type="button" data-bs-toggle="offcanvas" data-bs-target="#sidebarMenu">
                <i class="fas fa-bars"></i>
            </button>
        </div>

        <div class="d-flex">
            <!-- Sidebar (Offcanvas sur mobile, Fixe sur desktop) -->
            <div class="offcanvas-md offcanvas-start sidebar" tabindex="-1" id="sidebarMenu" style="width: 280px;">
                <div class="offcanvas-header d-md-none border-bottom border-color">
                    <h5 class="offcanvas-title dashboard-title">IP Visiteurs</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas" aria-label="Close"></button>
                </div>
                
                <div class="p-3 d-none d-md-block border-bottom border-color">
                    <h2 class="dashboard-title fs-4 m-0"><i class="fas fa-chart-network me-2"></i>Analytics</h2>
                    <div class="small text-muted mt-1">{{ grouped_visits|length }} Visiteurs Uniques</div>
                </div>

                <div class="list-group list-group-flush" id="ip-list">
                    {% for ip, data in grouped_visits.items() %}
                    <div class="ip-menu-item d-flex justify-content-between align-items-center {% if loop.first %}active{% endif %}" onclick="showIpData('{{ ip|replace('.', '-') }}', this)">
                        <span class="text-truncate" style="max-width: 150px;">{{ ip }}</span>
                        <span class="badge bg-secondary bg-opacity-25 rounded-pill">{{ data.actions|length }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- Contenu Principal -->
            <div class="flex-grow-1 p-3 p-md-5" style="max-height: 100vh; overflow-y: auto;">
                
                <div class="container-fluid max-w-4xl">
                    
                    {% for ip, data in grouped_visits.items() %}
                    <div id="view-{{ ip|replace('.', '-') }}" class="visitor-view {% if loop.first %}active-view{% endif %}">
                        <div class="visitor-card mb-4">
                            
                            <div class="card-header-custom d-flex flex-wrap justify-content-between align-items-center gap-3">
                                <div class="d-flex align-items-center gap-2">
                                    <div class="bg-dark rounded-circle d-flex justify-content-center align-items-center" style="width: 35px; height: 35px; border: 1px solid #334155;">
                                        <i class="fas fa-globe text-info"></i>
                                    </div>
                                    <span class="fs-4 fw-bold text-white">{{ ip }}</span>
                                </div>
                            </div>
                            
                            <div class="timeline-container">
                                <div class="user-agent-text mb-4 text-break">
                                    <i class="fas fa-laptop-code me-2 text-primary"></i> 
                                    {{ data.user_agent }}
                                </div>
                                
                                <div class="timeline">
                                    {% for v in data.actions %}
                                    
                                    {% set type_class = 'type-page' %}
                                    {% set badge_class = 'bg-page' %}
                                    {% set icon = 'fa-eye' %}
                                    
                                    {% if v.action == 'cv_download' %}
                                        {% set type_class = 'type-cv' %}
                                        {% set badge_class = 'bg-cv' %}
                                        {% set icon = 'fa-file-pdf' %}
                                    {% elif 'click_' in v.action %}
                                        {% set type_class = 'type-click' %}
                                        {% set badge_class = 'bg-click' %}
                                        {% set icon = 'fa-arrow-up-right-from-square' %}
                                    {% elif 'hover_' in v.action %}
                                        {% set type_class = 'type-read' %}
                                        {% set badge_class = 'bg-read' %}
                                        {% set icon = 'fa-computer-mouse' %}
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
                                        <!-- Affichage de l'heure ET de la date ici -->
                                        <span class="time-label">
                                            {{ v.timestamp.strftime('%H:%M:%S') }}
                                            <span class="text-muted small ms-1">{{ v.timestamp.strftime('%d/%m/%Y') }}</span>
                                        </span>
                                        <span class="badge-custom {{ badge_class }}">
                                            <i class="fas {{ icon }} me-1"></i> {{ v.action|replace('_', ' ') }}
                                        </span>
                                    </div>
                                    
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                    
                    {% if not grouped_visits %}
                    <div class="text-center text-muted mt-5">
                        <i class="fas fa-inbox fs-1 mb-3"></i>
                        <p>Aucune visite enregistrée pour le moment.</p>
                    </div>
                    {% endif %}
                    
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            function showIpData(ipId, element) {
                document.querySelectorAll('.ip-menu-item').forEach(el => {
                    el.classList.remove('active');
                });
                
                element.classList.add('active');
                
                document.querySelectorAll('.visitor-view').forEach(el => {
                    el.classList.remove('active-view');
                });
                
                const targetView = document.getElementById('view-' + ipId);
                if (targetView) {
                    targetView.classList.add('active-view');
                }
                
                const offcanvasElement = document.getElementById('sidebarMenu');
                if (window.innerWidth < 768) {
                    const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasElement);
                    if (bsOffcanvas) {
                        bsOffcanvas.hide();
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html, grouped_visits=grouped_visits)
    
if __name__ == '__main__':
    app.run(debug=True)
