"""
Gestionnaire de métriques pour le suivi des itérations.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class IterationMetrics:
    """Métriques d'une itération."""

    iteration: int
    timestamp: str

    # Scores d'évaluation LLM
    score_total: float
    score_exhaustivite: float
    score_precision: float
    score_coherence: float
    score_contexte: float
    score_classification: float

    # Erreurs détectées
    num_manques: int
    num_faux_positifs: int

    # Données générées
    num_training_examples: int

    # Métriques de training
    training_loss: float

    # Métriques NER (optionnel)
    ner_precision: Optional[float] = None
    ner_recall: Optional[float] = None
    ner_f1: Optional[float] = None

    # Temps d'exécution
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire."""
        return asdict(self)


@dataclass
class RunSummary:
    """Résumé complet d'un run."""

    run_id: str
    start_time: str
    end_time: Optional[str] = None
    success: bool = False
    final_score: float = 0.0
    num_iterations: int = 0
    best_iteration: int = 0
    best_score: float = 0.0
    threshold: float = 98.0
    base_model: str = ""
    output_model_path: str = ""

    iterations: List[IterationMetrics] = None

    def __post_init__(self):
        if self.iterations is None:
            self.iterations = []

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire."""
        data = asdict(self)
        data["iterations"] = [it.to_dict() for it in self.iterations]
        return data


class MetricsManager:
    """Gestionnaire de métriques."""

    def __init__(self, logs_dir: str = "./logs", run_id: Optional[str] = None):
        """
        Initialise le gestionnaire de métriques.

        Args:
            logs_dir: Répertoire des logs
            run_id: ID du run (auto-généré si None)
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Génère un run_id si non fourni
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.run_id = run_id
        self.run_dir = self.logs_dir / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Initialise le résumé
        self.summary = RunSummary(
            run_id=self.run_id,
            start_time=datetime.now().isoformat(),
        )

        self.iterations: List[IterationMetrics] = []

    def add_iteration(self, metrics: IterationMetrics):
        """Ajoute les métriques d'une itération."""
        self.iterations.append(metrics)
        self.summary.iterations = self.iterations
        self.summary.num_iterations = len(self.iterations)

        # Met à jour le meilleur score
        if metrics.score_total > self.summary.best_score:
            self.summary.best_score = metrics.score_total
            self.summary.best_iteration = metrics.iteration

        # Sauvegarde après chaque itération
        self.save()

    def finalize(
        self,
        success: bool,
        final_score: float,
        output_model_path: str = "",
    ):
        """Finalise le run."""
        self.summary.end_time = datetime.now().isoformat()
        self.summary.success = success
        self.summary.final_score = final_score
        self.summary.output_model_path = output_model_path

        self.save()

    def save(self):
        """Sauvegarde les métriques."""
        # Sauvegarde JSON
        json_path = self.run_dir / "summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.summary.to_dict(), f, indent=2, ensure_ascii=False)

        # Sauvegarde CSV des itérations
        if self.iterations:
            csv_path = self.run_dir / "iterations.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.iterations[0].to_dict().keys())
                writer.writeheader()
                for it in self.iterations:
                    writer.writerow(it.to_dict())

    def get_history(self) -> List[float]:
        """Récupère l'historique des scores totaux."""
        return [it.score_total for it in self.iterations]

    def get_best_iteration(self) -> Optional[IterationMetrics]:
        """Récupère les métriques de la meilleure itération."""
        if not self.iterations:
            return None

        return max(self.iterations, key=lambda it: it.score_total)

    def print_progress(self):
        """Affiche la progression."""
        if not self.iterations:
            print("Aucune itération enregistrée")
            return

        print("\n" + "=" * 70)
        print(f"PROGRESSION (Run: {self.run_id})")
        print("=" * 70)

        for it in self.iterations:
            status = "✅" if it.score_total >= self.summary.threshold else "❌"
            print(f"#{it.iteration:2d} {status} Score: {it.score_total:5.1f}/100 | "
                  f"Manques: {it.num_manques:2d} | FP: {it.num_faux_positifs:2d} | "
                  f"Exemples: {it.num_training_examples:2d}")

        print("=" * 70)
        print(f"Meilleur score : {self.summary.best_score:.1f}/100 (itération #{self.summary.best_iteration})")
        print(f"Seuil requis   : {self.summary.threshold:.1f}/100")
        print("=" * 70 + "\n")

    def export_report(self, output_path: Optional[str] = None) -> str:
        """
        Génère un rapport détaillé.

        Args:
            output_path: Chemin du fichier de sortie (optionnel)

        Returns:
            Chemin du rapport généré
        """
        if output_path is None:
            output_path = self.run_dir / "report.txt"
        else:
            output_path = Path(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("RAPPORT DE FINE-TUNING AUTOMATISÉ\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Run ID        : {self.summary.run_id}\n")
            f.write(f"Début         : {self.summary.start_time}\n")
            f.write(f"Fin           : {self.summary.end_time}\n")
            f.write(f"Succès        : {'Oui' if self.summary.success else 'Non'}\n")
            f.write(f"Modèle de base: {self.summary.base_model}\n")
            f.write(f"Seuil requis  : {self.summary.threshold}/100\n\n")

            f.write("-" * 70 + "\n")
            f.write("RÉSULTATS FINAUX\n")
            f.write("-" * 70 + "\n")
            f.write(f"Score final        : {self.summary.final_score:.1f}/100\n")
            f.write(f"Nombre d'itérations: {self.summary.num_iterations}\n")
            f.write(f"Meilleur score     : {self.summary.best_score:.1f}/100 (itération #{self.summary.best_iteration})\n")
            f.write(f"Modèle final       : {self.summary.output_model_path}\n\n")

            f.write("-" * 70 + "\n")
            f.write("DÉTAIL DES ITÉRATIONS\n")
            f.write("-" * 70 + "\n\n")

            for it in self.iterations:
                f.write(f"Itération #{it.iteration}\n")
                f.write(f"  Score total      : {it.score_total:.1f}/100\n")
                f.write(f"    - Exhaustivité : {it.score_exhaustivite:.1f}/30\n")
                f.write(f"    - Précision    : {it.score_precision:.1f}/25\n")
                f.write(f"    - Cohérence    : {it.score_coherence:.1f}/20\n")
                f.write(f"    - Contexte     : {it.score_contexte:.1f}/15\n")
                f.write(f"    - Classification: {it.score_classification:.1f}/10\n")
                f.write(f"  Erreurs détectées: {it.num_manques} manques, {it.num_faux_positifs} faux positifs\n")
                f.write(f"  Exemples générés : {it.num_training_examples}\n")
                f.write(f"  Loss training    : {it.training_loss:.4f}\n")
                if it.ner_f1 is not None:
                    f.write(f"  F1 NER           : {it.ner_f1:.3f}\n")
                if it.duration_seconds is not None:
                    f.write(f"  Durée            : {it.duration_seconds:.1f}s\n")
                f.write("\n")

        print(f"✓ Rapport sauvegardé : {output_path}")
        return str(output_path)


# Test du gestionnaire
if __name__ == "__main__":
    from datetime import datetime

    manager = MetricsManager()

    # Simule des itérations
    for i in range(1, 6):
        metrics = IterationMetrics(
            iteration=i,
            timestamp=datetime.now().isoformat(),
            score_total=70 + i * 5,
            score_exhaustivite=20 + i,
            score_precision=18 + i,
            score_coherence=15 + i,
            score_contexte=12 + i,
            score_classification=8,
            num_manques=10 - i,
            num_faux_positifs=5 - i,
            num_training_examples=15,
            training_loss=0.5 - i * 0.05,
            ner_f1=0.70 + i * 0.05,
            duration_seconds=120.0,
        )
        manager.add_iteration(metrics)

    manager.finalize(success=True, final_score=95.0, output_model_path="./output/model_final")
    manager.print_progress()
    manager.export_report()
