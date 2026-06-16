import os
import json

from app.models import Statistique, DiagnosticIA
from datetime import date
from datetime import datetime
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


@app.route('/patients/<int:id>', methods=['GET', 'POST'])
@login_required(role=['patient', 'admin'])
def patient_profile(id):
    patient = Patient.query.get_or_404(id)
    if current_user.role == 'patient' and (not current_user.patient or current_user.patient.id != id):
        return redirect(url_for('patient_profile', id=current_user.patient.id))
    if request.method == 'POST':
        patient.prenom = request.form.get('prenom', '').strip() or patient.prenom
        patient.nom = request.form.get('nom', '').strip() or patient.nom
        patient.telephone = request.form.get('telephone', '').strip()
        patient.preference_specialite = request.form.get('preference_specialite', '').strip()
        patient.preference_medecin = request.form.get('preference_medecin', '').strip()
        patient.horaires_preferes = request.form.get('horaires_preferes', '').strip()
        patient.historique_medical = request.form.get('historique_medical', '').strip()
        db.session.commit()
        flash('Profil patient mis à jour.', 'success')
    return render_template('patient_profile.html', patient=patient)


@app.route('/medecins')
def medecins():
    specialite = request.args.get('specialite', '').strip()
    search = request.args.get('search', '').strip()
    query = Medecin.query.outerjoin(Specialite)
    if search:
        query = query.filter(Medecin.nom.ilike(f'%{search}%'))
    if specialite:
        query = query.filter((Specialite.nom.ilike(f'%{specialite}%')) | (Medecin.specialite.ilike(f'%{specialite}%')))
    medecins_list = query.order_by(Medecin.nom).all()
    specialites = Specialite.query.order_by(Specialite.nom).all()
    return render_template('medecins.html', medecins=medecins_list, specialites=specialites, selected_specialite=specialite, search=search)


@app.route('/medecin/<int:id>')
def medecin_detail(id):
    medecin = Medecin.query.get_or_404(id)
    disponibilites = Disponibilite.query.filter_by(medecin_id=id, est_disponible=True).order_by(Disponibilite.date).all()
    disponibilites_par_date = {}
    for dispo in disponibilites:
        disponibilites_par_date.setdefault(dispo.date, []).append(dispo)
    return render_template(
        'medecin_detail.html',
        medecin=medecin,
        disponibilites=disponibilites,
        disponibilites_par_date=disponibilites_par_date,
    )


@app.route('/medecin/<int:id>/agenda')
@login_required(role=['medecin', 'admin'])
def medecin_agenda(id):
    medecin = Medecin.query.get_or_404(id)
    if current_user.role == 'medecin' and (not current_user.medecin or current_user.medecin.id != id):
        return redirect(url_for('home'))
    
    rdvs = RendezVous.query.filter_by(medecin_id=id).order_by(RendezVous.date).all()
    
    # 1. On définit 'today' correctement
    today = date.today().isoformat()
    
    # 2. On passe 'today' au template
    return render_template(
    'medecin_agenda.html', 
    medecin=medecin, 
    rdvs=rdvs, 
    today=today,
    get_rdv_statut_reel=get_rdv_statut_reel # Ajoute cette ligne ici !
)

@app.route('/medecin/<int:id>/availability', methods=['GET', 'POST'])
@login_required(role=['medecin', 'admin'])
def medecin_availability(id):
    medecin = Medecin.query.get_or_404(id)
    if current_user.role == 'medecin' and (not current_user.medecin or current_user.medecin.id != id):
        return redirect(url_for('home'))
    message = None
    if request.method == 'POST':
        date_value = request.form.get('date')
        plage_horaire = request.form.get('plage_horaire')
        if date_value and plage_horaire:
            disponible = Disponibilite(medecin_id=id, date=date_value, plage_horaire=plage_horaire)
            db.session.add(disponible)
            db.session.commit()
            message = 'Créneau ajouté avec succès.'
    disponibilites = Disponibilite.query.filter_by(medecin_id=id).order_by(Disponibilite.date).all()
    return render_template('medecin_availability.html', medecin=medecin, disponibilites=disponibilites, message=message)


@app.route('/medecin/<int:medecin_id>/agenda/update/<int:rdv_id>', methods=['POST'])
@login_required(role=['medecin', 'admin'])
def medecin_agenda_update(medecin_id, rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    
    # Sécurité
    if current_user.role == 'medecin' and (not current_user.medecin or current_user.medecin.id != medecin_id):
        return redirect(url_for('home'))
    
    # Mise à jour du statut
    rdv.statut = request.form.get('statut', 'Confirmé')
    
    # Enregistrement de la note dans la colonne 'note' du rendez-vous
    note = request.form.get('note', '').strip()
    if note:
        rdv.note = note
    
    db.session.commit()
    flash('Rendez-vous mis à jour avec succès.', 'success')
    return redirect(url_for('medecin_agenda', id=medecin_id))

@app.route('/confirmer_rdv/<int:id>', methods=['POST'])
def confirmer_rdv(id):
    nom = request.form.get('nom')
    email = request.form.get('email')
    telephone = request.form.get('telephone')
    motif = request.form.get('motif')
    slot = request.form.get('slot')
    date_value = ''
    horaire = request.form.get('horaire') or '09:00'

    if slot:
        try:
            date_value, horaire = slot.split('|')
        except ValueError:
            date_value = request.form.get('date')
    else:
        date_value = request.form.get('date')

    if not nom or not email or not date_value:
        flash('Veuillez remplir tous les champs obligatoires.', 'danger')
        return redirect(url_for('medecin_detail', id=id))

    # --- SÉCURITÉ : Vérification de disponibilité avant toute chose ---
    disponibilite = None
    if slot:
        disponibilite = Disponibilite.query.filter_by(
            medecin_id=id,
            date=date_value,
            plage_horaire=horaire,
            est_disponible=True
        ).first()
        
        if not disponibilite:
            flash('Désolé, ce créneau vient d\'être réservé ou n\'est plus disponible.', 'danger')
            return redirect(url_for('medecin_detail', id=id))

    # --- Gestion patient ---
    if current_user.is_authenticated and current_user.role == 'patient' and current_user.patient:
        patient = current_user.patient
        nom = nom or f"{patient.prenom or ''} {patient.nom}".strip()
        email = email or patient.email
        telephone = telephone or patient.telephone
    else:
        patient = Patient.query.filter_by(email=email).first()
        if not patient:
            patient = Patient(nom=nom, email=email, telephone=telephone)
            db.session.add(patient)
            db.session.flush()

    # --- Création du rendez-vous ---
    medecin = Medecin.query.get_or_404(id)
    nouveau_rdv = RendezVous(
        patient_id=patient.id if patient else None,
        patient_nom=nom,
        patient_email=email,
        medecin_id=id,
        date=date_value,
        horaire=horaire,
        statut='En attente',
        motif=motif,
    )
    db.session.add(nouveau_rdv)

    # --- Verrouillage du créneau ---
    if disponibilite:
        disponibilite.est_disponible = False

    db.session.commit()
    flash('Votre rendez-vous a été enregistré. Le médecin doit le confirmer.', 'success')
    return render_template(
        'succes.html',
        nom=nom,
        medecin=f"Dr. {medecin.prenom} {medecin.nom}",
        date=f"{date_value} à {horaire}",
        motif=motif,
    )


@app.route('/rendezvous')
@login_required()
def voir_rendezvous():
    # 1. On définit la date d'aujourd'hui
    today = date.today().isoformat()
    
    # 2. On récupère les rendez-vous
    if current_user.role == 'patient' and current_user.patient:
        rdv_list = RendezVous.query.filter_by(patient_id=current_user.patient.id).order_by(RendezVous.date).all()
    elif current_user.role == 'medecin' and current_user.medecin:
        rdv_list = RendezVous.query.filter_by(medecin_id=current_user.medecin.id).order_by(RendezVous.date).all()
    else:
        rdv_list = RendezVous.query.order_by(RendezVous.date).all()
        
    # 3. IMPORTANT : On passe 'today' dans le return render_template
    return render_template('rendezvous.html', rdv=rdv_list, today=today,get_rdv_statut_reel=get_rdv_statut_reel)


@app.route('/rendezvous/<int:rdv_id>/cancel', methods=['POST'])
@login_required(role='patient')
def cancel_rdv(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    if not current_user.patient or rdv.patient_id != current_user.patient.id:
        return redirect(url_for('voir_rendezvous'))
    rdv.statut = 'Annulé'
    db.session.commit()
    flash('Le rendez-vous a été annulé.', 'success')
    return redirect(url_for('voir_rendezvous'))


@app.route('/triage', methods=['GET', 'POST'])
def triage():
    # --- PARTIE GET : Pour afficher la page avec le compteur à jour ---
    if request.method == 'GET':
        stat = Statistique.query.first()
        total = stat.total_analyses if stat else 0
        return render_template('triage.html', total_analyses=total)

    # --- PARTIE POST : Pour traiter l'analyse quand on clique sur valider ---
    if request.method == 'POST':
        symptomes = request.form.get('symptomes', '')
        orientation = analyze_symptoms(symptomes)
        
        # 1. Mise à jour des statistiques globales
        stat = Statistique.query.first()
        if not stat:
            stat = Statistique(total_analyses=1)
            db.session.add(stat)
        else:
            stat.total_analyses += 1
        
        # 2. Sauvegarde du diagnostic individuel (si connecté)
        if current_user.is_authenticated and current_user.role == 'patient' and current_user.patient:
            diag = DiagnosticIA(
                patient_id=current_user.patient.id, 
                symptomes=symptomes, 
                orientation=orientation
            )
            db.session.add(diag)
            
        db.session.commit() # Commit unique pour tout valider
        
        return render_template('triage_result.html', symptomes=symptomes, orientation=orientation)


@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    total_patients = Patient.query.count()
    total_medecins = Medecin.query.count()
    total_rdv = RendezVous.query.count()
    today = date.today().isoformat()
    today_rdv = RendezVous.query.filter_by(date=today).count()
    blocked_users = User.query.filter_by(actif=False).count()
    return render_template(
        'admin_dashboard.html',
        total_patients=total_patients,
        total_medecins=total_medecins,
        total_rdv=total_rdv,
        today_rdv=today_rdv,
        blocked_users=blocked_users,
    )


@app.route('/admin/patients')
@login_required(role='admin')
def admin_patients():
    patients = Patient.query.order_by(Patient.nom).all()
    return render_template('admin_patients.html', patients=patients)


@app.route('/admin/appointments', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_appointments():
    if request.method == 'POST':
        rdv_id = request.form.get('rdv_id')
        statut = request.form.get('statut')
        rdv = RendezVous.query.get(rdv_id)
        if rdv and statut:
            rdv.statut = statut
            db.session.commit()
            flash('Statut du rendez-vous mis à jour.', 'success')
    appointments = RendezVous.query.order_by(RendezVous.date).all()
    return render_template('admin_appointments.html', appointments=appointments)


@app.route('/admin/medecins', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_medecins():
    message = None
    specialites = Specialite.query.order_by(Specialite.nom).all()
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        specialite_name = request.form.get('specialite', '').strip()
        prix = request.form.get('prix', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if nom and specialite_name and prix:
            specialite = Specialite.query.filter_by(nom=specialite_name).first()
            if not specialite:
                specialite = Specialite(nom=specialite_name)
                db.session.add(specialite)
                db.session.flush()
            if email and password and not User.query.filter_by(email=email).first():
                user = User(email=email, role='medecin')
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                medecin = Medecin(nom=nom, specialite=specialite_name, prix=prix, email=email, user_id=user.id, specialite_id=specialite.id)
            else:
                medecin = Medecin(nom=nom, specialite=specialite_name, prix=prix, email=email, specialite_id=specialite.id)
            db.session.add(medecin)
            db.session.commit()
            message = 'Médecin ajouté avec succès.'
    medecins = Medecin.query.order_by(Medecin.nom).all()
    return render_template('admin_medecins.html', medecins=medecins, specialites=specialites, message=message)


@app.route('/admin/medecins/<int:id>/delete', methods=['POST'])
@login_required(role='admin')
def admin_medecin_delete(id):
    medecin = Medecin.query.get_or_404(id)
    db.session.delete(medecin)
    db.session.commit()
    flash('Médecin supprimé.', 'success')
    return redirect(url_for('admin_medecins'))


@app.route('/admin/specialites', methods=['GET', 'POST'])
@login_required(role='admin')
def admin_specialites():
    message = None
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        if nom and not Specialite.query.filter_by(nom=nom).first():
            db.session.add(Specialite(nom=nom))
            db.session.commit()
            message = 'Spécialité ajoutée.'
    specialites = Specialite.query.order_by(Specialite.nom).all()
    return render_template('admin_specialites.html', specialites=specialites, message=message)


@app.route('/admin/specialites/<int:id>/delete', methods=['POST'])
@login_required(role='admin')
def admin_specialite_delete(id):
    specialite = Specialite.query.get_or_404(id)
    db.session.delete(specialite)
    db.session.commit()
    flash('Spécialité supprimée.', 'success')
    return redirect(url_for('admin_specialites'))


@app.route('/admin/users')
@login_required(role='admin')
def admin_users():
    users = User.query.order_by(User.email).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required(role='admin')
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    user.actif = not user.actif
    db.session.commit()
    flash('Statut utilisateur mis à jour.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/medecin/<int:id>/profile', methods=['GET', 'POST'])
@login_required(role=['medecin', 'admin'])
def medecin_profile(id):
    medecin = Medecin.query.get_or_404(id)
    # Récupération de la liste des spécialités pour le menu déroulant
    specialites = Specialite.query.order_by(Specialite.nom).all()
    
    if current_user.role == 'medecin' and (not current_user.medecin or current_user.medecin.id != id):
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        medecin.prenom = request.form.get('prenom', '').strip()
        medecin.nom = request.form.get('nom', '').strip()
        medecin.email = request.form.get('email', '').strip()
        medecin.telephone = request.form.get('telephone', '').strip()
        medecin.numero_ordre = request.form.get('numero_ordre', '').strip()
        medecin.experience = request.form.get('experience', '').strip()
        medecin.prix = request.form.get('prix', '').strip() or 'Sur devis'
        
        # Gestion de la spécialité via la liste déroulante
        specialite_name = request.form.get('specialite', '').strip()
        if specialite_name:
            specialite = Specialite.query.filter_by(nom=specialite_name).first()
            if not specialite:
                specialite = Specialite(nom=specialite_name)
                db.session.add(specialite)
                db.session.flush()
            medecin.specialite = specialite.nom
            medecin.specialite_id = specialite.id
            
        db.session.commit()
        flash('Profil médecin mis à jour.', 'success')
        
    # IMPORTANT : On passe 'specialites' au template ici
    return render_template('medecin_profile.html', medecin=medecin, specialites=specialites)


# Annulation par le patient
@app.route('/patient/rendezvous/<int:rdv_id>/annuler', methods=['POST'])
@login_required(role='patient')
def annuler_rdv_patient(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    # Vérifie que c'est bien le patient propriétaire du rdv
    if rdv.patient_id == current_user.patient.id:
        rdv.statut = 'Annulé par le patient'
        db.session.commit()
        flash('Rendez-vous annulé avec succès.', 'info')
    return redirect(url_for('dashboard_patient')) # Ou ta page de profil

# Annulation par le médecin
@app.route('/medecin/rendezvous/<int:rdv_id>/annuler', methods=['POST'])
@login_required(role=['medecin', 'admin'])
def annuler_rdv_medecin(rdv_id):
    rdv = RendezVous.query.get_or_404(rdv_id)
    # Vérifie que c'est bien le médecin qui possède ce rendez-vous
    if rdv.medecin_id == current_user.medecin.id:
        rdv.statut = 'Annulé par le médecin'
        db.session.commit()
        flash('Rendez-vous annulé et patient notifié.', 'info')
    return redirect(url_for('medecin_agenda', id=current_user.medecin.id))

@app.route('/medecin/toggle_disponibilite', methods=['POST'])
@login_required(role='medecin')
def toggle_disponibilite():
    medecin = current_user.medecin
    
    # On utilise le champ 'prix' comme indicateur d'état
    # Si le prix est égal à 'HORS_LIGNE', on le remet à une valeur par défaut ou vide
    if medecin.prix == 'HORS_LIGNE':
        medecin.prix = '10000' # Remets ton prix par défaut ici
        flash('Vous êtes maintenant disponible.', 'info')
    else:
        medecin.prix = 'HORS_LIGNE'
        flash('Vous êtes maintenant hors ligne.', 'info')
    
    db.session.commit()
    return redirect(url_for('dashboard_medecin'))


def get_rdv_statut_reel(rdv):
    # Combiner date et heure pour comparer
    rdv_datetime_str = f"{rdv.date} {rdv.horaire[:5]}" # Format "YYYY-MM-DD HH:MM"
    try:
        rdv_datetime = datetime.strptime(rdv_datetime_str, "%Y-%m-%d %H:%M")
        # Si la date/heure du rdv est passée et que le statut n'est pas déjà annulé
        if rdv_datetime < datetime.now() and rdv.statut not in ['Annulé', 'Annulé par le patient', 'Annulé par le médecin']:
            return "Terminé"
    except:
        pass
    return rdv.statut
