"""
Exemple basique d'utilisation du fine-tuning automatisé.
"""

import os
from spacy_layout.training import AutoFineTuner
from spacy_layout.training.config import Config, AristoteConfig


def main():
    """
    Exemple d'utilisation basique du système de fine-tuning automatisé.
    """

    # Configuration
    config = Config(
        aristote_api=AristoteConfig(
            api_key=os.getenv("ARISTOTE_API_KEY"),  # Depuis variable d'environnement
            # model est auto-détecté
        ),
        success_threshold=98.0,  # Score minimal requis
        max_iterations=20,       # Nombre max d'itérations
        data_dir="./data",       # Répertoire des données
        output_dir="./output",   # Répertoire de sortie des modèles
        logs_dir="./logs",       # Répertoire des logs
    )

    # Callbacks optionnels pour suivre la progression
    def on_iteration_start(iteration: int):
        print(f"\n{'='*70}")
        print(f"Début de l'itération #{iteration}")
        print(f"{'='*70}")

    def on_iteration_end(iteration: int, score: float):
        print(f"\n✓ Itération #{iteration} terminée - Score: {score:.1f}/100")

    def on_prompt_display(prompt_type: str, prompt: str):
        # Déjà affiché par défaut, mais vous pouvez personnaliser ici
        pass

    # Initialisation du fine-tuner
    fine_tuner = AutoFineTuner(
        base_model="fr_core_news_lg",  # Modèle spaCy de base
        data_dir="./data",
        config=config,
        on_iteration_start=on_iteration_start,
        on_iteration_end=on_iteration_end,
        on_prompt_display=on_prompt_display,
    )

    # Lancement du processus
    print("\n🚀 Démarrage du fine-tuning automatisé...")
    results = fine_tuner.run()

    # Affichage des résultats
    print("\n" + "="*70)
    print("RÉSULTATS FINAUX")
    print("="*70)

    if results["success"]:
        print("✅ SUCCÈS ! Le seuil de qualité a été atteint.")
    else:
        print("⚠ Le seuil de qualité n'a pas été atteint.")

    print(f"\nScore final        : {results['final_score']:.1f}/100")
    print(f"Nombre d'itérations: {results['num_iterations']}")
    print(f"Modèle final       : {results['best_model_path']}")
    print(f"Rapport détaillé   : {results['report_path']}")

    print("\nHistorique des scores:")
    for i, score in enumerate(results['metrics_history'], 1):
        status = "✅" if score >= config.success_threshold else "❌"
        print(f"  Itération #{i:2d} : {score:5.1f}/100 {status}")


if __name__ == "__main__":
    # Avant de lancer, assurez-vous d'avoir:
    # 1. Défini ARISTOTE_API_KEY dans votre environnement
    # 2. Placé vos données dans ./data/
    #    - ./data/entities/students/
    #    - ./data/entities/schools/
    #    - ./data/entities/programs/
    #    - ./data/documents/train/
    #    - ./data/documents/test/

    main()
