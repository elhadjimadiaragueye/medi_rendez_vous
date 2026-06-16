{% extends "base.html" %}

{% block content %}
<section class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
  <div class="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
    <div class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
      <p class="text-sm font-semibold uppercase tracking-[0.3em] text-violet-600">Bienvenue</p>
      <h1 class="mt-3 text-3xl font-bold text-slate-900">Profil patient : {{ patient.prenom }} {{ patient.nom }}</h1>
      <p class="mt-4 text-slate-600">Retrouvez vos préférences de médecin, votre historique médical et vos rendez-vous récents.</p>
      
      <form method="POST" action="{{ url_for('patient_profile', id=patient.id) }}" class="mt-8 space-y-6">
        {% if csrf_token %}
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        {% endif %}
        
        <div class="grid gap-6 sm:grid-cols-2">
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Prénom</label>
            <input type="text" name="prenom" value="{{ patient.prenom }}" required class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Nom</label>
            <input type="text" name="nom" value="{{ patient.nom }}" required class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
          </div>
        </div>
        
        <div class="grid gap-6 sm:grid-cols-2">
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Email</label>
            <input type="email" value="{{ patient.email }}" disabled class="w-full cursor-not-allowed rounded-[1.5rem] border border-slate-200 bg-slate-100 px-4 py-3 text-sm text-slate-500">
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Téléphone</label>
            <input type="text" name="telephone" value="{{ patient.telephone or '' }}" class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
          </div>
        </div>
        
        <div class="grid gap-6 sm:grid-cols-2">
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Préférence spécialité</label>
            <input type="text" name="preference_specialite" value="{{ patient.preference_specialite or '' }}" class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
          </div>
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700">Préférence médecin</label>
            <input type="text" name="preference_medecin" value="{{ patient.preference_medecin or '' }}" class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
          </div>
        </div>
        
        <div>
          <label class="mb-2 block text-sm font-semibold text-slate-700">Horaires préférés</label>
          <input type="text" name="horaires_preferes" value="{{ patient.horaires_preferes or '' }}" class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">
        </div>
        
        <div>
          <label class="mb-2 block text-sm font-semibold text-slate-700">Historique médical</label>
          <textarea name="historique_medical" rows="5" class="w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-4 text-sm text-slate-900 focus:border-violet-500 focus:ring-2 focus:ring-violet-100">{{ patient.historique_medical or '' }}</textarea>
        </div>
        
        <button type="submit" class="inline-flex w-full items-center justify-center rounded-full bg-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-violet-700">Mettre à jour le profil</button>
      </form>
    </div>
    
    <div class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
      <p class="text-sm font-semibold uppercase tracking-[0.3em] text-violet-600">Historique médical</p>
      <p class="mt-4 text-slate-600">{{ patient.historique_medical or 'Aucun historique enregistré pour le moment.' }}</p>
    </div>
  </div>
  
  <div class="mt-10 rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-sm font-semibold uppercase tracking-[0.3em] text-violet-600">Rendez-vous</p>
        <h2 class="mt-3 text-2xl font-bold text-slate-900">Historique des consultations</h2>
      </div>
      <a href="{{ url_for('medecins') }}" class="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-100">Réserver un nouveau RDV</a>
    </div>
    
    {% if patient.rendezvous %}
    <div class="mt-8 overflow-hidden rounded-[1.75rem] border border-slate-200">
      <table class="min-w-full divide-y divide-slate-200">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Médecin</th>
            <th class="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Date</th>
            <th class="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Heure</th>
            <th class="px-6 py-4 text-left text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Statut</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200 bg-white">
          {% for rdv in patient.rendezvous %}
          <tr class="hover:bg-slate-50">
            <td class="px-6 py-4 text-sm text-slate-700">{{ rdv.medecin.nom }}</td>
            <td class="px-6 py-4 text-sm text-slate-700">{{ rdv.date }}</td>
            <td class="px-6 py-4 text-sm text-slate-700">{{ rdv.horaire }}</td>
            <td class="px-6 py-4 text-sm">
              <span class="rounded-full px-3 py-1 text-xs font-semibold {{ 'bg-emerald-100 text-emerald-700' if rdv.statut == 'Confirmé' else 'bg-amber-100 text-amber-700' }}">{{ rdv.statut }}</span>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="mt-8 rounded-[1.75rem] bg-slate-50 p-8 text-center text-slate-600">
      <p class="text-lg font-semibold">Aucun rendez-vous enregistré pour le moment.</p>
    </div>
    {% endif %}
  </div>
</section>
{% endblock %}
