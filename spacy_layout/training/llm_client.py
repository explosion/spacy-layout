"""
Client LLM pour l'API Aristote (compatible OpenAI).
"""

import time
from typing import List, Dict, Any, Optional
import requests
from spacy_layout.training.config import AristoteConfig


class AristoteLLMClient:
    """Client pour l'API Aristote (compatible OpenAI)."""

    def __init__(self, config: AristoteConfig):
        """
        Initialise le client LLM.

        Args:
            config: Configuration de l'API Aristote
        """
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.api_key = config.api_key
        self.model = config.model
        self.timeout = config.timeout
        self.max_retries = config.max_retries

        # Auto-détection du modèle si non spécifié
        if self.model is None:
            self.model = self._auto_detect_model()

    def _auto_detect_model(self) -> str:
        """
        Détecte automatiquement le premier modèle disponible.

        Returns:
            Nom du modèle détecté
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            models = response.json().get("data", [])

            if not models:
                raise ValueError("Aucun modèle disponible sur l'API Aristote")

            # Prend le premier modèle
            model_id = models[0].get("id", models[0])
            print(f"✓ Modèle auto-détecté : {model_id}")
            return model_id

        except Exception as e:
            raise RuntimeError(f"Erreur lors de la détection du modèle : {e}")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Envoie une requête de chat completion à l'API.

        Args:
            messages: Liste de messages (role: system/user/assistant, content: str)
            temperature: Température de génération (0-1)
            max_tokens: Nombre maximal de tokens

        Returns:
            Réponse du LLM
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                result = response.json()
                return result["choices"][0]["message"]["content"]

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    print(f"⚠ Timeout, nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError("Timeout après plusieurs tentatives")

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠ Erreur réseau, nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"Erreur API après plusieurs tentatives : {e}")

        raise RuntimeError("Échec de la requête après toutes les tentatives")

    def get_available_models(self) -> List[str]:
        """
        Récupère la liste des modèles disponibles.

        Returns:
            Liste des noms de modèles
        """
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            response.raise_for_status()
            models = response.json().get("data", [])
            return [m.get("id", str(m)) for m in models]

        except Exception as e:
            raise RuntimeError(f"Erreur lors de la récupération des modèles : {e}")

    def validate_connection(self) -> bool:
        """
        Valide la connexion à l'API.

        Returns:
            True si la connexion fonctionne
        """
        try:
            models = self.get_available_models()
            return len(models) > 0
        except Exception:
            return False


# Test du client
if __name__ == "__main__":
    # Test avec configuration par défaut
    try:
        config = AristoteConfig()
        client = AristoteLLMClient(config)

        print("Modèles disponibles :")
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

    except Exception as e:
        print(f"Erreur : {e}")
