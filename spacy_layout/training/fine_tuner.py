"""
Module de fine-tuning pour modèles spaCy NER.
"""

import random
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from spacy_layout.training.config import TrainingConfig
from spacy_layout.training.llm_judge import TrainingExample


class SpaCyFineTuner:
    """Fine-tuner pour modèles spaCy."""

    def __init__(
        self,
        base_model: str,
        ner_labels: List[str],
        config: TrainingConfig,
        output_dir: str = "./output",
    ):
        """
        Initialise le fine-tuner.

        Args:
            base_model: Nom du modèle spaCy de base
            ner_labels: Labels NER à entraîner
            config: Configuration de training
            output_dir: Répertoire de sortie
        """
        self.base_model = base_model
        self.ner_labels = ner_labels
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Charge le modèle
        self.nlp = None
        self.load_model()

    def load_model(self):
        """Charge ou crée le modèle spaCy."""
        try:
            # Essaie de charger le modèle
            self.nlp = spacy.load(self.base_model)
            print(f"✓ Modèle chargé : {self.base_model}")
        except OSError:
            print(f"⚠ Modèle {self.base_model} non trouvé, téléchargement...")
            # Télécharge le modèle
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", self.base_model], check=True)
            self.nlp = spacy.load(self.base_model)

        # Ajoute le NER si absent
        if "ner" not in self.nlp.pipe_names:
            ner = self.nlp.add_pipe("ner")
        else:
            ner = self.nlp.get_pipe("ner")

        # Ajoute les labels
        for label in self.ner_labels:
            ner.add_label(label)

    def prepare_training_data(
        self,
        training_examples: List[TrainingExample],
    ) -> List[Example]:
        """
        Prépare les données d'entraînement au format spaCy.

        Args:
            training_examples: Liste d'exemples générés

        Returns:
            Liste d'Examples spaCy
        """
        examples = []

        for ex in training_examples:
            # Crée le Doc
            doc = self.nlp.make_doc(ex.text)

            # Crée les entités
            ents = []
            for start, end, label in ex.entities:
                span = doc.char_span(start, end, label=label, alignment_mode="contract")
                if span is not None:
                    ents.append(span)

            # Crée le Doc de référence
            ref_doc = doc.copy()
            ref_doc.ents = ents

            # Crée l'Example
            examples.append(Example(doc, ref_doc))

        return examples

    def train(
        self,
        training_examples: List[TrainingExample],
        iteration: int = 0,
    ) -> Dict[str, float]:
        """
        Entraîne le modèle avec les nouveaux exemples.

        Args:
            training_examples: Exemples d'entraînement
            iteration: Numéro d'itération

        Returns:
            Métriques d'entraînement
        """
        print(f"\n🔧 Fine-tuning avec {len(training_examples)} exemples...")

        # Prépare les données
        examples = self.prepare_training_data(training_examples)

        if not examples:
            print("⚠ Aucun exemple valide pour l'entraînement")
            return {"loss": 0.0}

        # Obtient le pipe NER
        ner = self.nlp.get_pipe("ner")

        # Désactive les autres pipes pendant l'entraînement
        other_pipes = [pipe for pipe in self.nlp.pipe_names if pipe != "ner"]

        with self.nlp.disable_pipes(*other_pipes):
            # Réinitialise ou continue l'entraînement
            if iteration == 0:
                # Premier training : initialise les poids
                optimizer = self.nlp.begin_training()
            else:
                # Suite du training
                optimizer = self.nlp.resume_training()

            losses = {}
            best_loss = float("inf")
            patience_counter = 0

            # Training loop
            for epoch in range(self.config.n_iter):
                random.shuffle(examples)
                losses_epoch = {}

                # Mini-batches
                batches = minibatch(examples, size=compounding(4.0, 32.0, 1.001))

                for batch in batches:
                    self.nlp.update(
                        batch,
                        drop=self.config.drop,
                        losses=losses_epoch,
                        sgd=optimizer,
                    )

                # Moyenne des losses
                avg_loss = sum(losses_epoch.values()) / max(len(losses_epoch), 1)
                losses[f"epoch_{epoch}"] = avg_loss

                # Early stopping
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= self.config.patience:
                    print(f"  Early stopping à epoch {epoch} (loss: {avg_loss:.4f})")
                    break

                if epoch % 2 == 0:
                    print(f"  Epoch {epoch}: loss = {avg_loss:.4f}")

        print(f"✓ Fine-tuning terminé (loss finale: {best_loss:.4f})")

        # Sauvegarde le modèle
        model_path = self.output_dir / f"model_iter_{iteration:03d}"
        self.nlp.to_disk(model_path)
        print(f"✓ Modèle sauvegardé : {model_path}")

        return {"final_loss": best_loss, **losses}

    def predict(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Fait une prédiction sur un texte.

        Args:
            text: Texte à analyser

        Returns:
            Liste de tuples (start, end, label, text)
        """
        doc = self.nlp(text)
        return [(ent.start_char, ent.end_char, ent.label_, ent.text) for ent in doc.ents]

    def evaluate(self, test_examples: List[TrainingExample]) -> Dict[str, float]:
        """
        Évalue le modèle sur des exemples de test.

        Args:
            test_examples: Exemples de test

        Returns:
            Métriques d'évaluation
        """
        examples = self.prepare_training_data(test_examples)

        if not examples:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        # Évalue avec spaCy
        scorer = self.nlp.evaluate(examples)

        return {
            "precision": scorer.get("ents_p", 0.0),
            "recall": scorer.get("ents_r", 0.0),
            "f1": scorer.get("ents_f", 0.0),
        }

    def load_iteration_model(self, iteration: int):
        """
        Charge un modèle d'une itération précédente.

        Args:
            iteration: Numéro d'itération
        """
        model_path = self.output_dir / f"model_iter_{iteration:03d}"

        if not model_path.exists():
            raise FileNotFoundError(f"Modèle de l'itération {iteration} non trouvé : {model_path}")

        self.nlp = spacy.load(model_path)
        print(f"✓ Modèle de l'itération {iteration} chargé")


# Test du fine-tuner
if __name__ == "__main__":
    from spacy_layout.training.config import TrainingConfig

    config = TrainingConfig(n_iter=5)

    fine_tuner = SpaCyFineTuner(
        base_model="fr_core_news_lg",
        ner_labels=["STUDENT_NAME", "SCHOOL", "PROGRAM"],
        config=config,
    )

    # Exemples de test
    examples = [
        TrainingExample(
            text="Sophie Martin étudie au lycée Victor Hugo.",
            entities=[(0, 13, "STUDENT_NAME"), (27, 45, "SCHOOL")],
        ),
        TrainingExample(
            text="L'élève Jean Dupont est inscrit en BTS Commerce.",
            entities=[(7, 18, "STUDENT_NAME"), (35, 48, "PROGRAM")],
        ),
    ]

    # Train
    metrics = fine_tuner.train(examples, iteration=1)
    print(f"\nMétriques : {metrics}")

    # Test
    test_text = "Marie Dubois suit une formation au collège Jean Moulin."
    predictions = fine_tuner.predict(test_text)
    print(f"\nPrédictions sur : {test_text}")
    for start, end, label, text in predictions:
        print(f"  [{label}] {text} ({start}-{end})")
