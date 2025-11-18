# Répertoire des données

Placez vos données d'entraînement et de test dans ce répertoire.

## Structure

```
data/
├── entities/                    # Listes d'entités
│   ├── students/
│   │   ├── noms.txt            # Format: un nom par ligne
│   │   ├── prenoms.txt
│   │   └── eleves.csv          # Format: nom,prenom
│   │
│   ├── schools/
│   │   ├── ecoles.txt          # Écoles primaires
│   │   ├── colleges.txt        # Collèges
│   │   ├── lycees.txt          # Lycées
│   │   └── etablissements.json # Ou un seul fichier avec types
│   │
│   └── programs/
│       ├── cursus.txt
│       └── formations.csv
│
├── documents/
│   ├── train/                  # Documents d'entraînement (PDF, DOCX, TXT)
│   │   ├── dossier_eleve_1.pdf
│   │   ├── poursuite_etudes.docx
│   │   └── bulletin.txt
│   │
│   └── test/                   # Documents de validation
│       └── validation_1.pdf
│
└── annotations/               # (Optionnel) Annotations manuelles
    └── manual_annotations.json
```

## Formats supportés

### Fichiers TXT
Un élément par ligne, lignes vides et commentaires (#) ignorés.

```
Dupont
Martin
Bernard
```

### Fichiers CSV
Première colonne = valeur principale, autres colonnes = métadonnées.

```csv
nom,type,ville
Lycée Victor Hugo,lycee,Paris
Collège Jean Moulin,college,Lyon
```

### Fichiers JSON
Liste de chaînes ou d'objets.

```json
[
  {"nom": "Victor Hugo", "type": "lycee"},
  {"nom": "Jean Moulin", "type": "college"}
]
```

## Exemples de données

Vous pouvez créer des fichiers factices pour tester :

```bash
# Noms d'élèves
echo -e "Dupont\nMartin\nBernard\nDubois" > entities/students/noms.txt

# Établissements
echo -e "Lycée Victor Hugo\nLycée Henri IV" > entities/schools/lycees.txt
echo -e "Collège Jean Moulin\nCollège Pasteur" > entities/schools/colleges.txt

# Cursus
echo -e "BTS Commerce\nLicence Informatique\nMaster Éducation" > entities/programs/cursus.txt
```
