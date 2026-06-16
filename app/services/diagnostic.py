import requests


def analyze_symptoms(symptomes_text):

    url = "http://localhost:11434/api/generate"

    system_instructions = """
Tu es un assistant de triage médical.

Ton rôle est uniquement d'aider à orienter l'utilisateur selon ses symptômes.

Règles obligatoires :
- Réponds uniquement en français.
- Utilise des phrases simples.
- Maximum 3 ou 4 phrases.
- Ne donne jamais un diagnostic définitif.
- Ne prescris aucun médicament.
- Ne propose aucun traitement.
- Ne remplace jamais un médecin.
- Ne provoque pas de peur inutile.
- Si les symptômes semblent graves, indique :
"Veuillez consulter un médecin rapidement."

Termine toujours par une recommandation simple.
"""

    prompt = f"""
{system_instructions}

Symptômes de l'utilisateur :
{symptomes_text}

Analyse :
"""

    payload = {
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 150
        }
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=90
        )

        response.raise_for_status()

        data = response.json()

        resultat = data.get("response")

        if resultat:
            return resultat.strip()

        return "Aucune analyse disponible."

    except requests.exceptions.Timeout:
        return (
            "Le service IA est momentanément lent. "
            "Veuillez réessayer dans quelques instants."
        )

    except requests.exceptions.ConnectionError:
        return (
            "Impossible de contacter le service IA. "
            "Vérifiez que Ollama est bien lancé."
        )

    except Exception as e:
        print("Erreur IA :", e)
        return "Service IA temporairement indisponible."
