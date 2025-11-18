#!/usr/bin/env python3
"""
Interface CLI pour le fine-tuning automatisé spaCy Layout.
"""

import argparse
import sys
from pathlib import Path

from spacy_layout.training import AutoFineTuner
from spacy_layout.training.config import Config, AristoteConfig


def print_banner():
    """Affiche la bannière."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  🎓 spaCy Layout - Fine-Tuning Automatisé NER                ║
║     Pseudonymisation de documents scolaires                   ║
╚═══════════════════════════════════════════════════════════════╝
""")


def cmd_train(args):
    """Commande d'entraînement."""
    print_banner()

    # Construit la configuration
    config = Config(
        aristote_api=AristoteConfig(
            api_key=args.api_key,
            model=args.llm_model,
        ),
        success_threshold=args.threshold,
        max_iterations=args.max_iterations,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        logs_dir=args.logs_dir,
    )

    # Lance le fine-tuning
    fine_tuner = AutoFineTuner(
        base_model=args.base_model,
        data_dir=args.data_dir,
        config=config,
    )

    results = fine_tuner.run()

    # Affiche les résultats
    print("\n" + "=" * 70)
    print("RÉSULTATS")
    print("=" * 70)

    if results["success"]:
        print(f"✅ SUCCÈS ! Seuil atteint.")
    else:
        print(f"⚠ Seuil non atteint.")

    print(f"\nScore final       : {results['final_score']:.1f}/100")
    print(f"Itérations        : {results['num_iterations']}")
    print(f"Modèle final      : {results['best_model_path']}")
    print(f"Rapport           : {results['report_path']}")

    return 0 if results["success"] else 1


def cmd_data_stats(args):
    """Affiche les statistiques des données."""
    from spacy_layout.training.data_loader import DataLoader

    loader = DataLoader(args.data_dir)
    stats = loader.get_stats()

    print("\n📊 Statistiques des données")
    print("=" * 70)

    for key, value in stats.items():
        print(f"  {key:20s}: {value}")

    print("\n✓ Entités chargées :")
    entities = loader.load_all_entities()
    for label, entity_list in entities.items():
        if isinstance(entity_list, dict):
            print(f"  {label}:")
            for school_type, el in entity_list.items():
                print(f"    - {school_type:10s}: {len(el.entities)} entrées")
        else:
            print(f"  {label:20s}: {len(entity_list.entities)} entrées")

    return 0


def cmd_test_llm(args):
    """Teste la connexion au LLM."""
    from spacy_layout.training.llm_client import AristoteLLMClient

    config = AristoteConfig(api_key=args.api_key, model=args.llm_model)

    print("\n🔌 Test de connexion au LLM Aristote...")
    print(f"URL: {config.base_url}")

    try:
        client = AristoteLLMClient(config)

        print(f"\n✓ Modèle auto-détecté : {client.model}")

        print("\nModèles disponibles :")
        for model in client.get_available_models():
            print(f"  - {model}")

        # Test simple
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": "Tu es un assistant utile."},
                {"role": "user", "content": "Dis bonjour en une phrase."},
            ]
        )

        print(f"\nRéponse test : {response}")
        print("\n✅ Connexion LLM OK")

        return 0

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        return 1


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="spaCy Layout - Fine-Tuning Automatisé NER",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Commande: train
    train_parser = subparsers.add_parser("train", help="Lancer le fine-tuning automatisé")
    train_parser.add_argument(
        "--base-model",
        default="fr_core_news_lg",
        help="Modèle spaCy de base (défaut: fr_core_news_lg)",
    )
    train_parser.add_argument(
        "--data-dir",
        default="./data",
        help="Répertoire des données (défaut: ./data)",
    )
    train_parser.add_argument(
        "--output-dir",
        default="./output",
        help="Répertoire de sortie (défaut: ./output)",
    )
    train_parser.add_argument(
        "--logs-dir",
        default="./logs",
        help="Répertoire des logs (défaut: ./logs)",
    )
    train_parser.add_argument(
        "--api-key",
        help="API key Aristote (ou variable d'env ARISTOTE_API_KEY)",
    )
    train_parser.add_argument(
        "--llm-model",
        help="Modèle LLM (auto-détecté par défaut)",
    )
    train_parser.add_argument(
        "--threshold",
        type=float,
        default=98.0,
        help="Seuil de réussite (défaut: 98.0)",
    )
    train_parser.add_argument(
        "--max-iterations",
        type=int,
        default=20,
        help="Nombre max d'itérations (défaut: 20)",
    )

    # Commande: data-stats
    stats_parser = subparsers.add_parser("data-stats", help="Afficher les statistiques des données")
    stats_parser.add_argument(
        "--data-dir",
        default="./data",
        help="Répertoire des données (défaut: ./data)",
    )

    # Commande: test-llm
    test_parser = subparsers.add_parser("test-llm", help="Tester la connexion au LLM")
    test_parser.add_argument(
        "--api-key",
        help="API key Aristote (ou variable d'env ARISTOTE_API_KEY)",
    )
    test_parser.add_argument(
        "--llm-model",
        help="Modèle LLM (auto-détecté par défaut)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch vers la commande appropriée
    if args.command == "train":
        return cmd_train(args)
    elif args.command == "data-stats":
        return cmd_data_stats(args)
    elif args.command == "test-llm":
        return cmd_test_llm(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
