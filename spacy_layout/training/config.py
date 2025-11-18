"""
Configuration module for automated fine-tuning system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import os
from pathlib import Path


@dataclass
class AristoteConfig:
    """Configuration pour l'API Aristote (compatible OpenAI)."""

    base_url: str = "https://llm.ilaas.fr/v1"
    api_key: Optional[str] = None
    model: Optional[str] = None  # Auto-détecté si None
    timeout: int = 120
    max_retries: int = 3

    def __post_init__(self):
        """Charge l'API key depuis l'environnement si non fournie."""
        if self.api_key is None:
            self.api_key = os.getenv("ARISTOTE_API_KEY", "")

        if not self.api_key:
            raise ValueError(
                "API key manquante. Définissez ARISTOTE_API_KEY dans l'environnement "
                "ou passez api_key dans la config."
            )


@dataclass
class PseudonymizationConfig:
    """Configuration de la pseudonymisation."""

    strategy: str = "french_placeholder"
    format: Dict[str, str] = field(default_factory=lambda: {
        "STUDENT_NAME": "ELEVE_{id:02d}",
        "SCHOOL": "{type}_{id:02d}",  # ECOLE_01, COLLEGE_01, LYCEE_01
        "PROGRAM": "CURSUS_{id:02d}",
        "TEACHER": "ENSEIGNANT_{id:02d}",
        "LOCATION": "LIEU_{id:02d}",
        "DATE": "DATE_{id:02d}",
        "ID_NUMBER": "ID_{id:02d}",
        "GRADE": "NOTE_{id:02d}",
    })
    maintain_consistency: bool = True  # Même entité = même placeholder


@dataclass
class PromptConfig:
    """Configuration des prompts pour le LLM juge."""

    display_console: bool = True
    save_to_file: bool = True
    custom_prompts_path: Optional[str] = None
    prompt_language: str = "fr"  # Langue des prompts


@dataclass
class DataGenerationConfig:
    """Configuration de la génération de données d'entraînement."""

    examples_per_iteration: int = 15
    min_confidence: float = 0.8
    include_context: bool = True
    diversify_examples: bool = True


@dataclass
class TrainingConfig:
    """Configuration du fine-tuning spaCy."""

    n_iter: int = 10
    batch_size: int = 8
    drop: float = 0.2
    learn_rate: float = 0.001
    patience: int = 3  # Early stopping
    eval_frequency: int = 100


@dataclass
class Config:
    """Configuration globale du système de fine-tuning automatisé."""

    # API LLM
    aristote_api: AristoteConfig = field(default_factory=AristoteConfig)

    # Paramètres de fine-tuning
    success_threshold: float = 98.0  # Score minimal requis
    max_iterations: int = 20

    # Pseudonymisation
    pseudonymization: PseudonymizationConfig = field(default_factory=PseudonymizationConfig)

    # Prompts
    prompts: PromptConfig = field(default_factory=PromptConfig)

    # Génération de données
    data_generation: DataGenerationConfig = field(default_factory=DataGenerationConfig)

    # Training spaCy
    training: TrainingConfig = field(default_factory=TrainingConfig)

    # Labels NER
    ner_labels: List[str] = field(default_factory=lambda: [
        "STUDENT_NAME",
        "SCHOOL",
        "PROGRAM",
        "TEACHER",
        "LOCATION",
        "DATE",
        "ID_NUMBER",
        "GRADE",
    ])

    # Répertoires
    data_dir: str = "./data"
    output_dir: str = "./output"
    logs_dir: str = "./logs"

    # Validation
    validation_split: float = 0.2

    def __post_init__(self):
        """Crée les répertoires nécessaires."""
        for dir_path in [self.data_dir, self.output_dir, self.logs_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """Crée une configuration depuis un dictionnaire."""
        # Gère les sous-configs
        if "aristote_api" in config_dict and isinstance(config_dict["aristote_api"], dict):
            config_dict["aristote_api"] = AristoteConfig(**config_dict["aristote_api"])

        if "pseudonymization" in config_dict and isinstance(config_dict["pseudonymization"], dict):
            config_dict["pseudonymization"] = PseudonymizationConfig(**config_dict["pseudonymization"])

        if "prompts" in config_dict and isinstance(config_dict["prompts"], dict):
            config_dict["prompts"] = PromptConfig(**config_dict["prompts"])

        if "data_generation" in config_dict and isinstance(config_dict["data_generation"], dict):
            config_dict["data_generation"] = DataGenerationConfig(**config_dict["data_generation"])

        if "training" in config_dict and isinstance(config_dict["training"], dict):
            config_dict["training"] = TrainingConfig(**config_dict["training"])

        return cls(**config_dict)


# Configuration par défaut
DEFAULT_CONFIG = Config()
