# 📚 Documentation Index - spaCy Layout

Bienvenue ! Ce repository contient le projet **spaCy Layout** avec un module additionnel de **Fine-Tuning Automatisé** pour la pseudonymisation de documents.

## 📖 Documentation Disponible

### 📦 Module Principal (spaCy Layout)

**[README.md](README.md)** - Documentation officielle du module spaCy Layout
- Traitement de PDFs et documents Word avec spaCy
- Extraction de texte structuré
- Création de `Doc` spaCy avec spans de layout
- Extraction de tables en `pandas.DataFrame`

### 🎓 Module de Fine-Tuning Automatisé (NOUVEAU)

**[TRAINING_README.md](TRAINING_README.md)** - Documentation complète du système de fine-tuning
- Vue d'ensemble du système automatisé
- Architecture et workflow des itérations
- Installation et configuration
- Utilisation (Web UI, CLI, API Python)
- Guide de préparation des données
- Exemples et cas d'usage
- **À lire en priorité pour le fine-tuning !**

### 🚀 Déploiement sur Serveur

**[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** - Guide de déploiement
- Instructions pour déploiement sur RedHat 9.4
- Options : Claude Code (automatisé) ou manuel
- Configuration post-déploiement
- SSL et nom de domaine
- Sécurité et maintenance

**[DEPLOYMENT_PROMPT.md](DEPLOYMENT_PROMPT.md)** - Prompt pour Claude Code
- Guide pas-à-pas complet pour déploiement automatisé
- Installation système et dépendances
- Configuration systemd et pare-feu
- Nginx, SELinux, fail2ban
- Scripts de sauvegarde et monitoring
- **À copier-coller dans Claude Code pour déploiement automatique**

### 📂 Données

**[data/README.md](data/README.md)** - Guide de préparation des données
- Structure des répertoires
- Formats supportés (TXT, CSV, JSON)
- Exemples de fichiers d'entités
- Upload de documents

---

## 🎯 Guides de Démarrage Rapide

### Pour le Module Principal (spaCy Layout)

```bash
# Installation
pip install spacy-layout

# Utilisation
python -c "
import spacy
from spacy_layout import spaCyLayout

nlp = spacy.blank('en')
layout = spaCyLayout(nlp)
doc = layout('./mon_document.pdf')
print(doc._.markdown)
"
```

📖 Consultez [README.md](README.md) pour la documentation complète.

---

### Pour le Fine-Tuning Automatisé

#### Option 1 : Interface Web (Recommandé)

```bash
# Installation
git clone https://github.com/jedeth/spacy-layout.git
cd spacy-layout
pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# Configuration
cp .env.example .env
# Éditez .env avec votre clé API Aristote

# Lancement
python server.py

# Accès
# Ouvrir http://localhost:8000 dans votre navigateur
```

#### Option 2 : CLI

```bash
# Vérifier les données
python cli.py data-stats

# Tester la connexion LLM
python cli.py test-llm

# Lancer le fine-tuning
python cli.py train --threshold 98.0 --max-iterations 20
```

#### Option 3 : API Python

```python
from spacy_layout.training import AutoFineTuner

fine_tuner = AutoFineTuner(
    base_model="fr_core_news_lg",
    data_dir="./data"
)

results = fine_tuner.run()
print(f"Score: {results['final_score']}/100")
```

📖 Consultez [TRAINING_README.md](TRAINING_README.md) pour la documentation complète.

---

### Pour le Déploiement Serveur

#### Avec Claude Code (Automatisé)

1. Connectez-vous au serveur RedHat 9.4
2. Lancez Claude Code
3. Copiez-collez le contenu de [DEPLOYMENT_PROMPT.md](DEPLOYMENT_PROMPT.md)
4. Claude Code effectuera le déploiement automatiquement

#### Manuel

Suivez étape par étape le guide dans [DEPLOYMENT_PROMPT.md](DEPLOYMENT_PROMPT.md).

📖 Consultez [DEPLOYMENT_README.md](DEPLOYMENT_README.md) pour plus de détails.

---

## 📁 Structure du Repository

```
spacy-layout/
├── README.md                    # Module principal spaCy Layout
├── TRAINING_README.md           # Fine-tuning automatisé ⭐
├── DEPLOYMENT_README.md         # Guide de déploiement
├── DEPLOYMENT_PROMPT.md         # Prompt Claude Code
├── DOCS_INDEX.md               # Ce fichier
│
├── spacy_layout/
│   ├── layout.py               # Module principal
│   ├── training/               # 🆕 Module de fine-tuning
│   │   ├── config.py
│   │   ├── llm_client.py
│   │   ├── llm_judge.py
│   │   ├── pseudonymizer.py
│   │   ├── fine_tuner.py
│   │   └── iteration_manager.py
│   └── web/                    # 🆕 Interface web
│       └── app.py
│
├── cli.py                      # 🆕 Interface CLI
├── server.py                   # 🆕 Serveur web
├── examples/
│   └── training/               # 🆕 Exemples de fine-tuning
└── data/                       # 🆕 Répertoire de données
    └── README.md
```

---

## 🔗 Liens Rapides

### Documentation

- [📦 Module Principal](README.md)
- [🎓 Fine-Tuning](TRAINING_README.md)
- [🚀 Déploiement](DEPLOYMENT_README.md)
- [📂 Données](data/README.md)

### Exemples

- [Exemple Python de base](examples/training/basic_usage.py)
- Exemple CLI : `python cli.py --help`
- Interface Web : `python server.py`

### Déploiement

- [Guide d'utilisation](DEPLOYMENT_README.md)
- [Prompt Claude Code](DEPLOYMENT_PROMPT.md)

---

## 💡 Cas d'Usage

### Module Principal (spaCy Layout)

- Extraction de texte structuré depuis PDFs
- Conversion de documents Word en données analysables
- Extraction de tables de documents
- Préparation de documents pour RAG
- NLP sur documents structurés

### Module de Fine-Tuning

- Pseudonymisation de documents scolaires (RGPD)
- Entraînement automatisé de modèles NER personnalisés
- Amélioration itérative guidée par LLM
- Protection des données personnelles dans documents administratifs

---

## 🆘 Support

### Pour le Module Principal

Consultez le [README.md](README.md) principal et la [documentation spaCy](https://spacy.io).

### Pour le Fine-Tuning

1. Consultez [TRAINING_README.md](TRAINING_README.md)
2. Vérifiez la section "Dépannage"
3. Examinez les logs dans `logs/`

### Pour le Déploiement

1. Consultez [DEPLOYMENT_README.md](DEPLOYMENT_README.md)
2. Section "Dépannage" dans [DEPLOYMENT_PROMPT.md](DEPLOYMENT_PROMPT.md)
3. Vérifiez les logs : `sudo journalctl -u spacy-layout -f`

---

## 🎯 Par Où Commencer ?

**Vous voulez...**

| Objectif | Documentation |
|----------|--------------|
| Extraire du texte de PDFs | [README.md](README.md) |
| Pseudonymiser des documents | [TRAINING_README.md](TRAINING_README.md) |
| Fine-tuner un modèle NER | [TRAINING_README.md](TRAINING_README.md) |
| Déployer sur un serveur | [DEPLOYMENT_README.md](DEPLOYMENT_README.md) |
| Utiliser l'interface web | `python server.py` puis [localhost:8000](http://localhost:8000) |
| Utiliser en CLI | `python cli.py --help` |
| Intégrer dans Python | [examples/training/basic_usage.py](examples/training/basic_usage.py) |

---

## 📝 Licence

MIT License - Voir le fichier LICENSE

---

## 🙏 Crédits

- **spaCy Layout** : [Explosion AI](https://explosion.ai)
- **Module de Fine-Tuning** : Extension personnalisée pour pseudonymisation
- **Docling** : [IBM Research](https://ds4sd.github.io/docling/)
