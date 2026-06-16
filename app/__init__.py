from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy import text
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Extensions (CSRFProtect supprimé)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

migrate = Migrate(app, db)

# Import des modèles et des routes
from app import models
from app.models import Medecin, Disponibilite, Specialite, User
from app import routes

with app.app_context():
    def ensure_column(table_name, column_name, column_type):
        existing = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        if not any(row[1] == column_name for row in existing):
            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            db.session.commit()

    db.create_all()
    ensure_column('medecin', 'email', 'VARCHAR(120)')
    ensure_column('medecin', 'user_id', 'INTEGER')
    ensure_column('medecin', 'specialite_id', 'INTEGER')
    ensure_column('medecin', 'numero_ordre', 'VARCHAR(80)')
    ensure_column('medecin', 'experience', 'VARCHAR(80)')
    ensure_column('medecin', 'telephone', 'VARCHAR(40)')
    ensure_column('patient', 'user_id', 'INTEGER')
    ensure_column('patient', 'prenom', 'VARCHAR(80)')
    ensure_column('patient', 'preference_specialite', 'VARCHAR(100)')
    ensure_column('patient', 'preference_medecin', 'VARCHAR(100)')
    ensure_column('patient', 'horaires_preferes', 'VARCHAR(120)')
    ensure_column('patient', 'historique_medical', 'TEXT')
    ensure_column('rendez_vous', 'patient_id', 'INTEGER')
    ensure_column('rendez_vous', 'patient_email', 'VARCHAR(120)')
    ensure_column('rendez_vous', 'horaire', 'VARCHAR(50)')
    ensure_column('rendez_vous', 'statut', 'VARCHAR(30)')
    ensure_column('rendez_vous', 'motif', 'VARCHAR(255)')
    ensure_column('user', 'actif', 'BOOLEAN')
    db.create_all()

    if Medecin.query.count() == 0:
        medecins = [
            Medecin(nom='Dubois', prenom='Léa', specialite='Généraliste', prix='60€', email='lea.dubois@mediris.fr'),
            Medecin(nom='El Hadi', prenom='Karim', specialite='Cardiologue', prix='90€', email='karim.elhadi@mediris.fr'),
            Medecin(nom='Lavergne', prenom='Emma', specialite='Dermatologue', prix='80€', email='emma.lavergne@mediris.fr'),
        ]
        db.session.add_all(medecins)
        db.session.commit()

    if Disponibilite.query.count() == 0:
        medecins = Medecin.query.all()
        disponibilites = []
        if len(medecins) > 0:
            disponibilites.extend([
                Disponibilite(medecin_id=medecins[0].id, date='2026-06-15', plage_horaire='09:00 - 10:00'),
                Disponibilite(medecin_id=medecins[0].id, date='2026-06-15', plage_horaire='14:00 - 15:00'),
            ])
        if len(medecins) > 1:
            disponibilites.append(Disponibilite(medecin_id=medecins[1].id, date='2026-06-16', plage_horaire='10:30 - 11:30'))
        if len(medecins) > 2:
            disponibilites.append(Disponibilite(medecin_id=medecins[2].id, date='2026-06-17', plage_horaire='13:00 - 14:00'))
        if disponibilites:
            db.session.add_all(disponibilites)
            db.session.commit()

    if Specialite.query.count() == 0:
        specialites = [
            Specialite(nom='Généraliste'),
            Specialite(nom='Cardiologie'),
            Specialite(nom='Dermatologie'),
            Specialite(nom='Pédiatrie'),
            Specialite(nom='Gynécologie'),
        ]
        db.session.add_all(specialites)
        db.session.commit()

    if User.query.filter_by(role='admin').count() == 0:
        admin = User(email='admin@mediris.fr', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()