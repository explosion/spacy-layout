"""
Orchestrateur d'itérations pour le fine-tuning automatisé.
"""

import time
from datetime import datetime
from typing import List, Optional, Callable, Dict
from pathlib import Path

from spacy_layout.training.config import Config
from spacy_layout.training.data_loader import DataLoader
from spacy_layout.training.llm_client import AristoteLLMClient
from spacy_layout.training.llm_judge import LLMJudge, TrainingExample
from spacy_layout.training.pseudonymizer import Pseudonymizer
from spacy_layout.training.fine_tuner import SpaCyFineTuner
from spacy_layout.training.metrics import MetricsManager, IterationMetrics
from spacy_layout import spaCyLayout


class AutoFineTuner:
    """
    Orchestrateur principal du système de fine-tuning automatisé.
    """

    def __init__(
        self,
        base_model: str = "fr_core_news_lg",
        data_dir: str = "./data",
        config: Optional[Config] = None,
        on_iteration_start: Optional[Callable[[int], None]] = None,
        on_iteration_end: Optional[Callable[[int, float], None]] = None,
        on_prompt_display: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialise l'orchestrateur de fine-tuning.

        Args:
            base_model: Modèle spaCy de base
            data_dir: Répertoire des données
            config: Configuration (utilise la config par défaut si None)
            on_iteration_start: Callback appelé au début de chaque itération
            on_iteration_end: Callback appelé à la fin de chaque itération
            on_prompt_display: Callback pour afficher les prompts
        """
        self.base_model = base_model
        self.data_dir = Path(data_dir)
        self.config = config or Config()

        # Callbacks
        self.on_iteration_start = on_iteration_start
        self.on_iteration_end = on_iteration_end
        self.on_prompt_display = on_prompt_display

        # Composants
        self.data_loader = DataLoader(data_dir)
        self.llm_client = None
        self.llm_judge = None
        self.pseudonymizer = None
        self.fine_tuner = None
        self.metrics_manager = None

        # Données chargées
        self.entities = {}
        self.school_types = {}
        self.training_examples = []

        print(f"✓ AutoFineTuner initialisé (modèle: {base_model})")

    def _initialize_components(self):
        """Initialise tous les composants."""
        print("\n🔧 Initialisation des composants...")

        # 1. Chargeur de données
        self.entities = self.data_loader.load_all_entities()
        stats = self.data_loader.get_stats()

        print(f"✓ Données chargées :")
        for key, value in stats.items():
            print(f"    - {key}: {value}")

        # Extrait les types d'écoles
        if "SCHOOL" in self.entities and isinstance(self.entities["SCHOOL"], dict):
            for school_type, entity_list in self.entities["SCHOOL"].items():
                for school_name in entity_list.entities:
                    self.school_types[school_name] = school_type

        # 2. Client LLM
        self.llm_client = AristoteLLMClient(self.config.aristote_api)
        print(f"✓ Client LLM connecté (modèle: {self.llm_client.model})")

        # 3. LLM Juge
        self.llm_judge = LLMJudge(
            llm_client=self.llm_client,
            prompt_config=self.config.prompts,
            data_gen_config=self.config.data_generation,
            logs_dir=self.config.logs_dir,
            on_prompt_display=self.on_prompt_display,
        )
        print("✓ LLM Juge initialisé")

        # 4. Pseudonymiseur
        self.pseudonymizer = Pseudonymizer(
            config=self.config.pseudonymization,
            school_types=self.school_types,
        )
        print("✓ Pseudonymiseur initialisé")

        # 5. Fine-tuner
        self.fine_tuner = SpaCyFineTuner(
            base_model=self.base_model,
            ner_labels=self.config.ner_labels,
            config=self.config.training,
            output_dir=self.config.output_dir,
        )
        print("✓ Fine-tuner initialisé")

        # 6. Gestionnaire de métriques
        self.metrics_manager = MetricsManager(logs_dir=self.config.logs_dir)
        self.metrics_manager.summary.base_model = self.base_model
        self.metrics_manager.summary.threshold = self.config.success_threshold
        print("✓ Gestionnaire de métriques initialisé")

    def _run_iteration(self, iteration: int) -> float:
        """
        Exécute une itération complète.

        Args:
            iteration: Numéro d'itération

        Returns:
            Score obtenu
        """
        start_time = time.time()

        print(f"\n{'=' * 70}")
        print(f"ITÉRATION #{iteration}")
        print(f"{'=' * 70}\n")

        if self.on_iteration_start:
            self.on_iteration_start(iteration)

        # 1. PSEUDONYMISATION
        print("📝 Étape 1/4 : Pseudonymisation...")

        # Charge un document de test
        test_docs = self.data_loader.load_documents("test")
        if not test_docs:
            # Utilise un document d'entraînement si pas de test
            test_docs = self.data_loader.load_documents("train")

        if not test_docs:
            raise ValueError("Aucun document disponible pour la pseudonymisation")

        # Prend le premier document
        test_doc_path = test_docs[0]

        # Utilise spaCyLayout pour extraire le texte (si PDF/DOCX)
        if test_doc_path.suffix.lower() in [".pdf", ".docx"]:
            layout = spaCyLayout(self.fine_tuner.nlp)
            doc = layout(str(test_doc_path))
            # Applique le NER
            doc = self.fine_tuner.nlp(doc.text)
        else:
            # Fichier texte simple
            with open(test_doc_path, "r", encoding="utf-8") as f:
                text = f.read()
            doc = self.fine_tuner.nlp(text)

        # Pseudonymise
        pseudo_result = self.pseudonymizer.pseudonymize_doc(doc)
        print(f"✓ {len(pseudo_result.entities_detected)} entités détectées")

        # 2. ÉVALUATION PAR LLM JUGE
        print("\n🔍 Étape 2/4 : Évaluation par le LLM juge...")

        eval_score = self.llm_judge.evaluate_pseudonymization(
            pseudo_result=pseudo_result,
            ner_labels=self.config.ner_labels,
            iteration=iteration,
        )

        print(f"✓ Score obtenu : {eval_score.total:.1f}/100")
        print(f"    - Exhaustivité  : {eval_score.exhaustivite:.1f}/30")
        print(f"    - Précision     : {eval_score.precision:.1f}/25")
        print(f"    - Cohérence     : {eval_score.coherence:.1f}/20")
        print(f"    - Contexte      : {eval_score.contexte:.1f}/15")
        print(f"    - Classification: {eval_score.classification:.1f}/10")
        print(f"  Erreurs : {len(eval_score.manques)} manques, {len(eval_score.faux_positifs)} faux positifs")

        # 3. GÉNÉRATION DE DONNÉES D'ENTRAÎNEMENT
        print("\n🤖 Étape 3/4 : Génération de données d'entraînement...")

        new_examples = self.llm_judge.generate_training_data(
            evaluation_score=eval_score,
            ner_labels=self.config.ner_labels,
            iteration=iteration,
        )

        self.training_examples.extend(new_examples)
        print(f"✓ {len(new_examples)} nouveaux exemples générés")
        print(f"  Total d'exemples : {len(self.training_examples)}")

        # 4. FINE-TUNING
        print("\n🎓 Étape 4/4 : Fine-tuning du modèle...")

        if new_examples:
            training_metrics = self.fine_tuner.train(
                training_examples=new_examples,
                iteration=iteration,
            )
            final_loss = training_metrics.get("final_loss", 0.0)
        else:
            print("⚠ Aucun exemple valide, skip du fine-tuning")
            final_loss = 0.0

        # Sauvegarde les métriques
        duration = time.time() - start_time

        iteration_metrics = IterationMetrics(
            iteration=iteration,
            timestamp=datetime.now().isoformat(),
            score_total=eval_score.total,
            score_exhaustivite=eval_score.exhaustivite,
            score_precision=eval_score.precision,
            score_coherence=eval_score.coherence,
            score_contexte=eval_score.contexte,
            score_classification=eval_score.classification,
            num_manques=len(eval_score.manques),
            num_faux_positifs=len(eval_score.faux_positifs),
            num_training_examples=len(new_examples),
            training_loss=final_loss,
            duration_seconds=duration,
        )

        self.metrics_manager.add_iteration(iteration_metrics)

        if self.on_iteration_end:
            self.on_iteration_end(iteration, eval_score.total)

        print(f"\n✓ Itération #{iteration} terminée en {duration:.1f}s")

        return eval_score.total

    def run(self) -> Dict:
        """
        Lance le processus de fine-tuning automatisé.

        Returns:
            Dictionnaire avec les résultats
        """
        print("\n" + "=" * 70)
        print("DÉMARRAGE DU FINE-TUNING AUTOMATISÉ")
        print("=" * 70)

        # Initialise les composants
        self._initialize_components()

        # Boucle d'itérations
        for iteration in range(1, self.config.max_iterations + 1):
            score = self._run_iteration(iteration)

            # Affiche la progression
            self.metrics_manager.print_progress()

            # Vérifie si le seuil est atteint
            if score >= self.config.success_threshold:
                print(f"\n🎉 SUCCÈS ! Seuil de {self.config.success_threshold}% atteint !")
                print(f"Score final : {score:.1f}/100")

                # Finalise
                best_iter = self.metrics_manager.get_best_iteration()
                model_path = self.config.output_dir / f"model_iter_{best_iter.iteration:03d}"

                self.metrics_manager.finalize(
                    success=True,
                    final_score=score,
                    output_model_path=str(model_path),
                )

                # Génère le rapport
                report_path = self.metrics_manager.export_report()

                return {
                    "success": True,
                    "final_score": score,
                    "num_iterations": iteration,
                    "best_model_path": str(model_path),
                    "report_path": report_path,
                    "metrics_history": self.metrics_manager.get_history(),
                }

        # Seuil non atteint
        print(f"\n⚠ Seuil non atteint après {self.config.max_iterations} itérations")

        best_iter = self.metrics_manager.get_best_iteration()
        best_score = best_iter.score_total if best_iter else 0.0
        model_path = self.config.output_dir / f"model_iter_{best_iter.iteration:03d}" if best_iter else ""

        self.metrics_manager.finalize(
            success=False,
            final_score=best_score,
            output_model_path=str(model_path),
        )

        report_path = self.metrics_manager.export_report()

        return {
            "success": False,
            "final_score": best_score,
            "num_iterations": self.config.max_iterations,
            "best_model_path": str(model_path),
            "report_path": report_path,
            "metrics_history": self.metrics_manager.get_history(),
        }


# Point d'entrée pour test
if __name__ == "__main__":
    from spacy_layout.training.config import Config, AristoteConfig

    config = Config(
        aristote_api=AristoteConfig(),
        success_threshold=98.0,
        max_iterations=5,
    )

    fine_tuner = AutoFineTuner(
        base_model="fr_core_news_lg",
        data_dir="./data",
        config=config,
    )

    results = fine_tuner.run()

    print("\n" + "=" * 70)
    print("RÉSULTATS FINAUX")
    print("=" * 70)
    for key, value in results.items():
        print(f"{key}: {value}")
