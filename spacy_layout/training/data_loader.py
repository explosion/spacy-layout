"""
Chargeur de données multi-format (TXT, CSV, JSON).
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EntityList:
    """Liste d'entités avec métadonnées."""

    entities: List[str]
    entity_type: str
    metadata: Dict[str, List[Dict]] = None  # Métadonnées optionnelles

    def __len__(self):
        return len(self.entities)


class DataLoader:
    """Chargeur de données pour listes d'entités et documents."""

    def __init__(self, data_dir: str = "./data"):
        """
        Initialise le chargeur de données.

        Args:
            data_dir: Répertoire racine des données
        """
        self.data_dir = Path(data_dir)
        self.entities_dir = self.data_dir / "entities"
        self.documents_dir = self.data_dir / "documents"

    def load_text_file(self, file_path: Path) -> List[str]:
        """
        Charge un fichier TXT (un élément par ligne).

        Args:
            file_path: Chemin du fichier

        Returns:
            Liste des éléments
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    def load_csv_file(self, file_path: Path) -> Tuple[List[str], List[Dict]]:
        """
        Charge un fichier CSV.

        Args:
            file_path: Chemin du fichier

        Returns:
            Tuple (liste des valeurs principales, liste des métadonnées complètes)
        """
        entities = []
        metadata = []

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # La première colonne est considérée comme la valeur principale
                first_col = list(row.keys())[0]
                entities.append(row[first_col])
                metadata.append(row)

        return entities, metadata

    def load_json_file(self, file_path: Path) -> Tuple[List[str], List[Dict]]:
        """
        Charge un fichier JSON.

        Args:
            file_path: Chemin du fichier

        Returns:
            Tuple (liste des valeurs principales, liste des métadonnées complètes)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            if all(isinstance(item, str) for item in data):
                # Liste simple de chaînes
                return data, []
            elif all(isinstance(item, dict) for item in data):
                # Liste de dictionnaires
                # Cherche la première clé contenant "nom" ou "name"
                first_item = data[0]
                name_key = None
                for key in first_item.keys():
                    if "nom" in key.lower() or "name" in key.lower():
                        name_key = key
                        break

                if name_key:
                    entities = [item[name_key] for item in data]
                else:
                    # Prend la première clé
                    first_key = list(first_item.keys())[0]
                    entities = [item[first_key] for item in data]

                return entities, data

        raise ValueError(f"Format JSON non supporté dans {file_path}")

    def load_entity_file(self, file_path: Path, entity_type: str) -> EntityList:
        """
        Charge un fichier d'entités (auto-détection du format).

        Args:
            file_path: Chemin du fichier
            entity_type: Type d'entité (STUDENT_NAME, SCHOOL, etc.)

        Returns:
            EntityList avec les entités chargées
        """
        suffix = file_path.suffix.lower()

        if suffix == ".txt":
            entities = self.load_text_file(file_path)
            return EntityList(entities=entities, entity_type=entity_type)

        elif suffix == ".csv":
            entities, metadata = self.load_csv_file(file_path)
            return EntityList(entities=entities, entity_type=entity_type, metadata={"items": metadata})

        elif suffix == ".json":
            entities, metadata = self.load_json_file(file_path)
            return EntityList(
                entities=entities,
                entity_type=entity_type,
                metadata={"items": metadata} if metadata else None
            )

        else:
            raise ValueError(f"Format non supporté : {suffix}")

    def load_schools_by_type(self) -> Dict[str, EntityList]:
        """
        Charge les établissements scolaires par type (écoles, collèges, lycées).

        Returns:
            Dictionnaire {type: EntityList}
        """
        schools_dir = self.entities_dir / "schools"
        schools_by_type = {}

        if not schools_dir.exists():
            return schools_by_type

        # Fichiers séparés par type
        type_mapping = {
            "ecoles": "ecole",
            "colleges": "college",
            "lycees": "lycee",
        }

        for pattern, school_type in type_mapping.items():
            for file_path in schools_dir.glob(f"{pattern}.*"):
                entity_list = self.load_entity_file(file_path, "SCHOOL")
                schools_by_type[school_type] = entity_list

        # Fichier unique avec métadonnées
        for file_path in schools_dir.glob("etablissements.*"):
            entity_list = self.load_entity_file(file_path, "SCHOOL")

            # Si métadonnées disponibles, sépare par type
            if entity_list.metadata and "items" in entity_list.metadata:
                for school_type in ["ecole", "college", "lycee"]:
                    filtered_items = [
                        item for item in entity_list.metadata["items"]
                        if item.get("type", "").lower() == school_type
                    ]
                    if filtered_items:
                        entities = [item.get("nom", item.get("name", "")) for item in filtered_items]
                        schools_by_type[school_type] = EntityList(
                            entities=entities,
                            entity_type="SCHOOL",
                            metadata={"items": filtered_items}
                        )

        return schools_by_type

    def load_all_entities(self) -> Dict[str, EntityList]:
        """
        Charge toutes les listes d'entités depuis data/entities/.

        Returns:
            Dictionnaire {label: EntityList}
        """
        entities_map = {}

        if not self.entities_dir.exists():
            return entities_map

        # Charge les élèves
        students_dir = self.entities_dir / "students"
        if students_dir.exists():
            all_students = []
            for file_path in students_dir.glob("*"):
                if file_path.suffix.lower() in [".txt", ".csv", ".json"]:
                    entity_list = self.load_entity_file(file_path, "STUDENT_NAME")
                    all_students.extend(entity_list.entities)

            if all_students:
                entities_map["STUDENT_NAME"] = EntityList(
                    entities=list(set(all_students)),  # Déduplique
                    entity_type="STUDENT_NAME"
                )

        # Charge les écoles (par type)
        schools_by_type = self.load_schools_by_type()
        if schools_by_type:
            entities_map["SCHOOL"] = schools_by_type

        # Charge les cursus/programmes
        programs_dir = self.entities_dir / "programs"
        if programs_dir.exists():
            all_programs = []
            for file_path in programs_dir.glob("*"):
                if file_path.suffix.lower() in [".txt", ".csv", ".json"]:
                    entity_list = self.load_entity_file(file_path, "PROGRAM")
                    all_programs.extend(entity_list.entities)

            if all_programs:
                entities_map["PROGRAM"] = EntityList(
                    entities=list(set(all_programs)),
                    entity_type="PROGRAM"
                )

        return entities_map

    def load_documents(self, split: str = "train") -> List[Path]:
        """
        Charge les chemins des documents d'entraînement ou de test.

        Args:
            split: "train" ou "test"

        Returns:
            Liste des chemins de fichiers
        """
        docs_dir = self.documents_dir / split

        if not docs_dir.exists():
            return []

        # Supporte PDF, DOCX, TXT
        documents = []
        for pattern in ["*.pdf", "*.docx", "*.txt"]:
            documents.extend(docs_dir.glob(pattern))

        return sorted(documents)

    def get_stats(self) -> Dict[str, int]:
        """
        Récupère les statistiques des données chargées.

        Returns:
            Dictionnaire avec les comptages
        """
        stats = {
            "train_docs": len(self.load_documents("train")),
            "test_docs": len(self.load_documents("test")),
        }

        entities = self.load_all_entities()
        for label, entity_list in entities.items():
            if isinstance(entity_list, dict):  # SCHOOL avec types
                total = sum(len(el.entities) for el in entity_list.values())
                stats[f"{label}_count"] = total
            else:
                stats[f"{label}_count"] = len(entity_list.entities)

        return stats


# Test du chargeur
if __name__ == "__main__":
    loader = DataLoader("./data")

    print("Statistiques des données :")
    for key, value in loader.get_stats().items():
        print(f"  {key}: {value}")

    print("\nEntités chargées :")
    entities = loader.load_all_entities()
    for label, entity_list in entities.items():
        if isinstance(entity_list, dict):
            print(f"  {label}:")
            for school_type, el in entity_list.items():
                print(f"    - {school_type}: {len(el.entities)} entrées")
        else:
            print(f"  {label}: {len(entity_list.entities)} entrées")
