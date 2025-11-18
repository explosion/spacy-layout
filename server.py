#!/usr/bin/env python3
"""
Serveur web pour le fine-tuning automatisé spaCy Layout.
"""

import argparse
import uvicorn
from spacy_layout.web.app import app


def main():
    parser = argparse.ArgumentParser(
        description="Serveur web pour le fine-tuning automatisé spaCy Layout"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Adresse d'écoute (défaut: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port d'écoute (défaut: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Active le rechargement automatique (dev)",
    )

    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║  🎓 spaCy Layout - Fine-Tuning Automatisé                    ║
║     Serveur Web                                               ║
╚═══════════════════════════════════════════════════════════════╝

Serveur démarré sur: http://{args.host}:{args.port}

Interface web: http://localhost:{args.port}
Documentation API: http://localhost:{args.port}/docs

Appuyez sur Ctrl+C pour arrêter le serveur.
""")

    uvicorn.run(
        "spacy_layout.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
