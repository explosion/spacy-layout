# 🎓 spaCy Layout - Fine-Tuning Automatisé NER

Système de fine-tuning automatisé pour la pseudonymisation de documents scolaires français, utilisant un LLM juge pour l'évaluation et la génération de données d'entraînement.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Installation](#installation)
- [Préparation des données](#préparation-des-données)
- [Utilisation](#utilisation)
  - [Interface Web](#interface-web)
  - [Interface CLI](#interface-cli)
  - [API Python](#api-python)
- [Configuration](#configuration)
- [Workflow d'une itération](#workflow-dune-itération)
- [Exemples](#exemples)

---

## 🎯 Vue d'ensemble

Ce système permet d'**entraîner automatiquement** un modèle NER spaCy pour pseudonymiser des documents scolaires (dossiers élèves, bulletins, etc.) en utilisant un processus itératif guidé par un LLM.

### Fonctionnalités principales

- ✅ **Fine-tuning automatisé** : Entraînement itératif jusqu'à atteindre un seuil de qualité (98% par défaut)
- ✅ **LLM Juge** : Évaluation de la pseudonymisation selon 5 critères
- ✅ **Génération de données** : Le LLM génère des exemples d'entraînement contextualisés
- ✅ **Placeholders français** : `ELEVE_01`, `ECOLE_01/COLLEGE_01/LYCEE_01`, etc.
- ✅ **Multi-format** : Support TXT, CSV, JSON pour les listes d'entités
- ✅ **3 interfaces** : Web, CLI, et API Python
- ✅ **Monitoring temps réel** : Suivi via WebSocket de la progression

### Labels NER supportés

- `STUDENT_NAME` : Noms/prénoms d'élèves
- `SCHOOL` : Établissements scolaires (avec distinction école/collège/lycée)
- `PROGRAM` : Cursus/formations/diplômes
- `TEACHER` : Noms d'enseignants
- `LOCATION` : Villes/adresses
- `DATE` : Dates
- `ID_NUMBER` : Numéros d'identification (INE, etc.)
- `GRADE` : Notes et résultats

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ITÉRATION N                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PSEUDONYMISATION                                        │
│     Modèle NER → Texte pseudonymisé                        │
│                                                             │
│  2. ÉVALUATION (LLM Juge)                                  │
│     5 critères → Score /100                                 │
│     - Exhaustivité (/30)                                    │
│     - Précision (/25)                                       │
│     - Cohérence (/20)                                       │
│     - Contexte (/15)                                        │
│     - Classification (/10)                                  │
│                                                             │
│  3. GÉNÉRATION DONNÉES (LLM Juge)                          │
│     Erreurs détectées → 15 nouveaux exemples annotés       │
│                                                             │
│  4. FINE-TUNING                                            │
│     spaCy training loop → Modèle N+1                       │
│                                                             │
│  ➜ Si score ≥ 98% : TERMINÉ                               │
│  ➜ Sinon : Itération N+1                                   │
└─────────────────────────────────────────────────────────────┘
```

### Modules principaux

```
spacy_layout/training/
├── config.py                  # Configuration système
├── llm_client.py             # Client API Aristote (compatible OpenAI)
├── data_loader.py            # Chargeur multi-format (TXT/CSV/JSON)
├── pseudonymizer.py          # Pseudonymisation avec placeholders FR
├── llm_judge.py              # Évaluation + Génération données
├── fine_tuner.py             # Fine-tuning spaCy
├── metrics.py                # Tracking métriques
└── iteration_manager.py      # Orchestration (AutoFineTuner)
```

---

## 📦 Installation

### 1. Cloner le repository

```bash
git clone <repository-url>
cd spacy-layout
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Télécharger le modèle spaCy français

```bash
python -m spacy download fr_core_news_lg
```

### 4. Configurer l'API Aristote

Créez un fichier `.env` à la racine :

```bash
ARISTOTE_API_KEY=drasi-idf-1-84e20c68-c43f-4a71-b655-a5af1426ebXX
```

---

## 📂 Préparation des données

### Structure des répertoires

```
data/
├── entities/                    # Listes d'entités
│   ├── students/
│   │   ├── noms.txt            # Un nom par ligne
│   │   ├── prenoms.csv         # CSV avec colonnes
│   │   └── eleves.json         # JSON structuré
│   ├── schools/
│   │   ├── ecoles.txt          # Écoles primaires
│   │   ├── colleges.txt        # Collèges
│   │   ├── lycees.txt          # Lycées
│   │   └── etablissements.json # Avec métadonnées
│   └── programs/
│       ├── cursus.txt
│       └── formations.csv
│
├── documents/
│   ├── train/                  # Documents d'entraînement
│   │   ├── dossier_eleve_1.pdf
│   │   ├── poursuite_etudes.docx
│   │   └── bulletin.txt
│   └── test/                   # Documents de test
│       └── validation_1.pdf
```

### Formats supportés

#### TXT (simple)
```
Dupont
Martin
Bernard
```

#### CSV (avec métadonnées)
```csv
nom,type,ville
Lycée Victor Hugo,lycee,Paris
Collège Jean Moulin,college,Lyon
École Jules Ferry,ecole,Marseille
```

#### JSON (structuré)
```json
[
  {"nom": "Victor Hugo", "type": "lycee", "ville": "Paris"},
  {"nom": "Jean Moulin", "type": "college", "ville": "Lyon"}
]
```

---

## 🚀 Utilisation

### Interface Web (Recommandé)

1. **Démarrer le serveur**

```bash
python server.py
```

2. **Ouvrir dans le navigateur**

```
http://localhost:8000
```

3. **Interface disponible**
   - Upload de fichiers (glisser-déposer)
   - Configuration du training
   - Monitoring temps réel avec WebSocket
   - Logs en direct
   - Téléchargement des résultats

### Interface CLI

#### Afficher les statistiques des données

```bash
python cli.py data-stats --data-dir ./data
```

#### Tester la connexion au LLM

```bash
python cli.py test-llm --api-key YOUR_API_KEY
```

#### Lancer le fine-tuning

```bash
python cli.py train \
  --base-model fr_core_news_lg \
  --data-dir ./data \
  --threshold 98.0 \
  --max-iterations 20
```

### API Python

```python
from spacy_layout.training import AutoFineTuner
from spacy_layout.training.config import Config, AristoteConfig

# Configuration
config = Config(
    aristote_api=AristoteConfig(
        api_key="YOUR_API_KEY"
    ),
    success_threshold=98.0,
    max_iterations=20,
)

# Initialisation
fine_tuner = AutoFineTuner(
    base_model="fr_core_news_lg",
    data_dir="./data",
    config=config,
)

# Lancement
results = fine_tuner.run()

print(f"Score final : {results['final_score']:.1f}/100")
print(f"Modèle : {results['best_model_path']}")
```

---

## ⚙️ Configuration

### Configuration complète

```python
from spacy_layout.training.config import Config

config = Config(
    # API LLM
    aristote_api=AristoteConfig(
        base_url="https://llm.ilaas.fr/v1",
        api_key="YOUR_KEY",
        model=None,  # Auto-détecté
    ),

    # Paramètres de fine-tuning
    success_threshold=98.0,
    max_iterations=20,

    # Pseudonymisation
    pseudonymization=PseudonymizationConfig(
        strategy="french_placeholder",
        format={
            "STUDENT_NAME": "ELEVE_{id:02d}",
            "SCHOOL": "{type}_{id:02d}",  # ECOLE_01, COLLEGE_01, LYCEE_01
        },
        maintain_consistency=True,
    ),

    # Prompts
    prompts=PromptConfig(
        display_console=True,
        save_to_file=True,
    ),

    # Génération de données
    data_generation=DataGenerationConfig(
        examples_per_iteration=15,
    ),

    # Training spaCy
    training=TrainingConfig(
        n_iter=10,
        batch_size=8,
    ),
)
```

---

## 🔄 Workflow d'une itération

### 1. Pseudonymisation (2-5s)

Le modèle NER actuel détecte les entités dans un document de référence et les remplace par des placeholders.

**Exemple :**
```
Original:
  "Sophie Martin, élève au Lycée Victor Hugo, suit un BTS Commerce."

Pseudonymisé:
  "ELEVE_01, élève au LYCEE_01, suit un CURSUS_01."
```

### 2. Évaluation par le LLM Juge (5-10s)

Le LLM analyse la qualité de la pseudonymisation selon 5 critères :

```
Exhaustivité  : 25/30  (entités manquées : "Paris")
Précision     : 22/25  (faux positifs : 0)
Cohérence     : 20/20  (mappings cohérents)
Contexte      : 14/15  (document compréhensible)
Classification: 9/10   (types corrects)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL         : 90/100
```

**Le prompt d'évaluation est affiché à l'utilisateur** dans la console et sauvegardé dans `logs/iteration_XXX/prompt_evaluation.txt`.

### 3. Génération de données d'entraînement (10-15s)

Basé sur les erreurs détectées, le LLM génère 15 nouveaux exemples annotés :

```json
{
  "training_examples": [
    {
      "text": "Marie Dubois, inscrite au collège Jean Jaurès de Lyon, prépare le DNB.",
      "entities": [
        [0, 12, "STUDENT_NAME"],
        [27, 48, "SCHOOL"],
        [52, 56, "LOCATION"],
        [66, 69, "PROGRAM"]
      ]
    },
    ...
  ]
}
```

**Le prompt de génération est affiché** et sauvegardé dans `logs/iteration_XXX/prompt_generation.txt`.

### 4. Fine-tuning (30-60s)

Les nouveaux exemples sont utilisés pour affiner le modèle spaCy avec `spacy.training.loop`.

```
Epoch 0: loss = 2.3456
Epoch 2: loss = 1.1234
Epoch 4: loss = 0.5678
...
✓ Modèle sauvegardé : output/model_iter_001
```

### 5. Métriques

Les résultats sont sauvegardés :
- `logs/run_YYYYMMDD_HHMMSS/summary.json`
- `logs/run_YYYYMMDD_HHMMSS/iterations.csv`
- `logs/iteration_XXX/prompt_*.txt`

---

## 📊 Exemples de résultats

### Rapport final

```
═══════════════════════════════════════════════════════════
RAPPORT DE FINE-TUNING AUTOMATISÉ
═══════════════════════════════════════════════════════════

Run ID        : 20250118_143052
Début         : 2025-01-18T14:30:52
Fin           : 2025-01-18T14:45:23
Succès        : Oui
Modèle de base: fr_core_news_lg

───────────────────────────────────────────────────────────
RÉSULTATS FINAUX
───────────────────────────────────────────────────────────
Score final        : 98.5/100
Nombre d'itérations: 7
Meilleur score     : 98.5/100 (itération #7)

───────────────────────────────────────────────────────────
DÉTAIL DES ITÉRATIONS
───────────────────────────────────────────────────────────

Itération #1 : 72.0/100
Itération #2 : 81.0/100
Itération #3 : 87.0/100
Itération #4 : 92.0/100
Itération #5 : 95.0/100
Itération #6 : 97.0/100
Itération #7 : 98.5/100 ✅
```

---

## 🛠️ Dépannage

### Erreur "API key manquante"

```bash
export ARISTOTE_API_KEY="votre_clé"
# Ou créez un fichier .env
```

### Erreur "Modèle spaCy non trouvé"

```bash
python -m spacy download fr_core_news_lg
```

### Connexion WebSocket échoue

Vérifiez que le serveur est bien lancé sur le bon port :
```bash
python server.py --port 8000
```

---

## 📝 Licence

Ce projet est sous licence MIT (voir LICENSE).

---

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

## 📚 Ressources

- [Documentation spaCy](https://spacy.io/)
- [API Aristote Dispatcher](https://llm.ilaas.fr/v1)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
