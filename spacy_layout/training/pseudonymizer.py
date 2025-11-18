"""
Module de pseudonymisation avec placeholders français.
"""

import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, field
from spacy.tokens import Doc
from spacy_layout.training.config import PseudonymizationConfig


@dataclass
class PseudonymizationResult:
    """Résultat de la pseudonymisation."""

    original_text: str
    pseudonymized_text: str
    entities_detected: List[Tuple[int, int, str, str]]  # (start, end, label, original_text)
    replacement_map: Dict[str, str]  # {original: placeholder}
    school_types: Dict[str, str] = field(default_factory=dict)  # {school_name: type}


class Pseudonymizer:
    """Pseudonymise les documents avec placeholders français."""

    def __init__(
        self,
        config: PseudonymizationConfig,
        school_types: Dict[str, str] = None
    ):
        """
        Initialise le pseudonymiseur.

        Args:
            config: Configuration de pseudonymisation
            school_types: Mapping {nom_école: type} pour ECOLE/COLLEGE/LYCEE
        """
        self.config = config
        self.school_types = school_types or {}
        self.replacement_map: Dict[str, str] = {}
        self.counters: Dict[str, int] = {}

    def _get_school_type(self, school_name: str, context: str = "") -> str:
        """
        Détermine le type d'établissement (école/collège/lycée).

        Args:
            school_name: Nom de l'établissement
            context: Contexte autour de l'établissement

        Returns:
            Type d'établissement
        """
        # Vérifie d'abord dans le mapping fourni
        if school_name in self.school_types:
            return self.school_types[school_name].upper()

        # Sinon, détection par mots-clés
        full_text = (school_name + " " + context).lower()

        if any(keyword in full_text for keyword in ["lycée", "lycee", "lp ", "cfa"]):
            return "LYCEE"
        elif any(keyword in full_text for keyword in ["collège", "college"]):
            return "COLLEGE"
        elif any(keyword in full_text for keyword in ["école", "ecole", "maternelle", "primaire", "élémentaire"]):
            return "ECOLE"
        else:
            # Par défaut, considère comme lycée pour les établissements secondaires
            return "LYCEE"

    def _generate_placeholder(self, label: str, original_text: str, context: str = "") -> str:
        """
        Génère un placeholder français pour une entité.

        Args:
            label: Type d'entité (STUDENT_NAME, SCHOOL, etc.)
            original_text: Texte original
            context: Contexte pour déterminer le type d'école

        Returns:
            Placeholder généré
        """
        # Si cohérence activée et déjà rencontré
        if self.config.maintain_consistency and original_text in self.replacement_map:
            return self.replacement_map[original_text]

        # Incrémente le compteur pour ce label
        if label not in self.counters:
            self.counters[label] = 0
        self.counters[label] += 1

        # Récupère le format
        format_str = self.config.format.get(label, f"{label}_{{id:02d}}")

        # Gère le cas spécial de SCHOOL
        if label == "SCHOOL":
            school_type = self._get_school_type(original_text, context)
            placeholder = format_str.format(type=school_type, id=self.counters[label])
        else:
            placeholder = format_str.format(id=self.counters[label])

        # Sauvegarde pour cohérence
        if self.config.maintain_consistency:
            self.replacement_map[original_text] = placeholder

        return placeholder

    def pseudonymize_doc(self, doc: Doc) -> PseudonymizationResult:
        """
        Pseudonymise un document spaCy.

        Args:
            doc: Document spaCy avec entités détectées

        Returns:
            Résultat de pseudonymisation
        """
        original_text = doc.text
        entities_detected = []
        replacements = []

        # Collecte les entités à remplacer (en ordre inverse pour ne pas décaler les indices)
        for ent in sorted(doc.ents, key=lambda e: e.start_char, reverse=True):
            # Contexte autour de l'entité (30 caractères avant et après)
            context_start = max(0, ent.start_char - 30)
            context_end = min(len(original_text), ent.end_char + 30)
            context = original_text[context_start:context_end]

            # Génère le placeholder
            placeholder = self._generate_placeholder(ent.label_, ent.text, context)

            replacements.append((ent.start_char, ent.end_char, placeholder))
            entities_detected.append((ent.start_char, ent.end_char, ent.label_, ent.text))

        # Applique les remplacements
        pseudonymized_text = original_text
        for start, end, placeholder in replacements:
            pseudonymized_text = (
                pseudonymized_text[:start] + placeholder + pseudonymized_text[end:]
            )

        return PseudonymizationResult(
            original_text=original_text,
            pseudonymized_text=pseudonymized_text,
            entities_detected=entities_detected,
            replacement_map=self.replacement_map.copy(),
            school_types=self.school_types.copy(),
        )

    def pseudonymize_text(self, text: str, entities: List[Tuple[int, int, str]]) -> PseudonymizationResult:
        """
        Pseudonymise un texte avec une liste d'entités.

        Args:
            text: Texte original
            entities: Liste de tuples (start, end, label)

        Returns:
            Résultat de pseudonymisation
        """
        entities_detected = []
        replacements = []

        # Trie en ordre inverse
        for start, end, label in sorted(entities, key=lambda e: e[0], reverse=True):
            original_text = text[start:end]

            # Contexte
            context_start = max(0, start - 30)
            context_end = min(len(text), end + 30)
            context = text[context_start:context_end]

            # Placeholder
            placeholder = self._generate_placeholder(label, original_text, context)

            replacements.append((start, end, placeholder))
            entities_detected.append((start, end, label, original_text))

        # Applique les remplacements
        pseudonymized_text = text
        for start, end, placeholder in replacements:
            pseudonymized_text = (
                pseudonymized_text[:start] + placeholder + pseudonymized_text[end:]
            )

        return PseudonymizationResult(
            original_text=text,
            pseudonymized_text=pseudonymized_text,
            entities_detected=entities_detected,
            replacement_map=self.replacement_map.copy(),
            school_types=self.school_types.copy(),
        )

    def reset(self):
        """Réinitialise les compteurs et le mapping."""
        self.replacement_map.clear()
        self.counters.clear()


# Test du pseudonymiseur
if __name__ == "__main__":
    from spacy_layout.training.config import PseudonymizationConfig

    config = PseudonymizationConfig()
    school_types = {
        "Lycée Victor Hugo": "lycee",
        "Collège Jean Moulin": "college",
        "École Jules Ferry": "ecole",
    }

    pseudonymizer = Pseudonymizer(config, school_types)

    # Test
    text = "Sophie Martin, élève en Terminale S au Lycée Victor Hugo, souhaite intégrer une classe préparatoire."
    entities = [
        (0, 13, "STUDENT_NAME"),  # Sophie Martin
        (39, 58, "SCHOOL"),        # Lycée Victor Hugo
        (78, 99, "PROGRAM"),       # classe préparatoire
    ]

    result = pseudonymizer.pseudonymize_text(text, entities)

    print("Original :")
    print(result.original_text)
    print("\nPseudonymisé :")
    print(result.pseudonymized_text)
    print("\nMapping :")
    for original, placeholder in result.replacement_map.items():
        print(f"  {original} → {placeholder}")
