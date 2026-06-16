import os
import json

from app.models import Statistique, DiagnosticIA
from datetime import date
from functools import wraps
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from app import app, db, login_manager
from app.models import (
    Consultation,
    DiagnosticIA,
    Disponibilite,
    Medecin,
    Patient,
    RendezVous,
    Specialite,
    User,
)
from app.services.diagnostic import analyze_symptoms


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.actif:
                logout_user()
                flash('Compte désactivé. Contactez l’administrateur.', 'danger')
                return redirect(url_for('login'))
            if role is not None:
                allowed_roles = role if isinstance(role, (list, tuple)) else [role]
                if current_user.role not in allowed_roles:
                    flash('Accès refusé.', 'danger')
                    return redirect(url_for('home'))
            return func(*args, **kwargs)
        return wrapper
    return decorator


@app.route('/')
def home():
    specialites = Specialite.query.order_by(Specialite.nom).all()
    medecins = Medecin.query.order_by(Medecin.nom).limit(6).all()
    stats = {
        'doctors': Medecin.query.count(),
        'appointments': RendezVous.query.count(),
        'patients': Patient.query.count(),
        'analyses': DiagnosticIA.query.count(),
        'specialites': Specialite.query.count(),
    }
    # Charger métriques du modèle IA si présentes
    metrics_path = os.path.join(os.path.dirname(__file__), 'models_ia', 'metrics.json')
    model_metrics = None
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r', encoding='utf-8') as f:
                model_metrics = json.load(f)
        except Exception:
            model_metrics = None

    return render_template('index.html', specialites=specialites, medecins=medecins, stats=stats, model_metrics=model_metrics)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if not user or not user.actif or not user.check_password(password):
            error = 'Email ou mot de passe invalide.'
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/register/patient', methods=['GET', 'POST'])
@app.route('/patients/new', methods=['GET', 'POST'])
def register_patient():
    error = None
    specialites = Specialite.query.order_by(Specialite.nom).all()
    if request.method == 'POST':
        prenom = request.form.get('prenom', '').strip()
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        telephone = request.form.get('telephone')
        preference_specialite = request.form.get('preference_specialite')
        preference_medecin = request.form.get('preference_medecin')
        horaires_preferes = request.form.get('horaires_preferes')
        historique_medical = request.form.get('historique_medical')

        if not prenom or not nom or not email or not password or not confirm_password:
            error = 'Veuillez remplir tous les champs obligatoires.'
        elif password != confirm_password:
            error = 'Les mots de passe ne correspondent pas.'
        elif User.query.filter_by(email=email).first():
            error = 'Cet email est déjà utilisé.'
        else:
            user = User(email=email, role='patient')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            patient = Patient(
                user_id=user.id,
                prenom=prenom,
                nom=nom,
                email=email,
                telephone=telephone,
                preference_specialite=preference_specialite,
                preference_medecin=preference_medecin,
                horaires_preferes=horaires_preferes,
                historique_medical=historique_medical,
            )
            db.session.add(patient)
            db.session.commit()
            login_user(user)
            flash('Compte patient créé avec succès.', 'success')
            return redirect(url_for('dashboard_patient'))
    return render_template('patient_new.html', error=error, specialites=specialites)


@app.route('/register')
def register():
    return redirect(url_for('register_patient'))


@app.route('/register/medecin', methods=['GET', 'POST'])
def register_medecin():
    # Récupération de la liste des spécialités pour le menu déroulant
    specialites = Specialite.query.order_by(Specialite.nom).all()
    error = None
    
    if request.method == 'POST':
        prenom = request.form.get('prenom', '').strip()
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone')
        specialite_name = request.form.get('specialite', '').strip()
        numero_ordre = request.form.get('numero_ordre', '').strip()
        prix = request.form.get('prix', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not prenom or not nom or not email or not specialite_name or not password or not confirm_password:
            error = 'Veuillez remplir tous les champs obligatoires.'
        elif password != confirm_password:
            error = 'Les mots de passe ne correspondent pas.'
        elif User.query.filter_by(email=email).first():
            error = 'Cet email est déjà utilisé.'
        else:
            user = User(email=email, role='medecin')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            
            # Recherche ou création de la spécialité
            specialite = Specialite.query.filter_by(nom=specialite_name).first()
            if not specialite:
                specialite = Specialite(nom=specialite_name)
                db.session.add(specialite)
                db.session.flush()
                
            medecin = Medecin(
                user_id=user.id,
                prenom=prenom,
                nom=nom,
                email=email,
                telephone=telephone,
                specialite=specialite_name,
                specialite_id=specialite.id,
                numero_ordre=numero_ordre,
                prix=prix or 'Sur devis',
            )
            db.session.add(medecin)
            db.session.commit()
            login_user(user)
            flash('Compte médecin créé avec succès.', 'success')
            return redirect(url_for('dashboard_medecin'))
            
    # On transmet 'specialites' au template pour peupler le menu <select>
    return render_template('register_medecin.html', error=error, specialites=specialites)

@app.route('/dashboard')
@login_required()
def dashboard():
    if current_user.role == 'patient':
        return redirect(url_for('dashboard_patient'))
    if current_user.role == 'medecin':
        return redirect(url_for('dashboard_medecin'))
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('home'))


@app.route('/dashboard/patient')
@login_required(role='patient')
def dashboard_patient():
    patient = current_user.patient
    upcoming_appointments = RendezVous.query.filter_by(patient_id=patient.id).filter(RendezVous.statut != 'Annulé').order_by(RendezVous.date).all()
    next_appointments = [rdv for rdv in upcoming_appointments if rdv.date >= date.today().isoformat()][:3]
    past_appointments = [rdv for rdv in upcoming_appointments if rdv.date < date.today().isoformat()][:3]
    diagnostics_count = DiagnosticIA.query.filter_by(patient_id=patient.id).count()
    return render_template(
        'dashboard_patient.html',
        patient=patient,
        upcoming_count=len([rdv for rdv in upcoming_appointments if rdv.date >= date.today().isoformat()]),
        past_count=len(past_appointments),
        diagnostics_count=diagnostics_count,
        next_appointments=next_appointments,
        recent_appointments=past_appointments,
        get_rdv_statut_reel=get_rdv_statut_reel,
    )


@app.route('/dashboard/medecin')
@login_required(role='medecin')
def dashboard_medecin():
    medecin = current_user.medecin
    rdvs = RendezVous.query.filter_by(medecin_id=medecin.id).order_by(RendezVous.date).all()
    today = date.today().isoformat()
    upcoming = [rdv for rdv in rdvs if rdv.date >= today][:5]
    patients = set(rdv.patient_id for rdv in rdvs if rdv.patient_id)
    return render_template(
        'dashboard_medecin.html',
        medecin=medecin,
        patients_count=len(patients),
        today_count=len([rdv for rdv in rdvs if rdv.date == today]),
        upcoming_count=len(upcoming),
        upcoming=upcoming,
        get_rdv_statut_reel=get_rdv_statut_reel,
    )
