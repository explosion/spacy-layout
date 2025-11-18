"""
LLM Juge pour l'évaluation de la pseudonymisation et la génération de données.
"""

import json
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
from spacy_layout.training.llm_client import AristoteLLMClient
from spacy_layout.training.pseudonymizer import PseudonymizationResult
from spacy_layout.training.config import PromptConfig, DataGenerationConfig


@dataclass
class EvaluationScore:
    """Score d'évaluation de la pseudonymisation."""

    exhaustivite: float  # /30
    precision: float     # /25
    coherence: float     # /20
    contexte: float      # /15
    classification: float  # /10
    total: float         # /100

    manques: List[str]
    faux_positifs: List[str]
    commentaires: str = ""


@dataclass
class TrainingExample:
    """Exemple d'entraînement généré."""

    text: str
    entities: List[Tuple[int, int, str]]  # (start, end, label)
    context: str = ""


class LLMJudge:
    """Juge LLM pour évaluation et génération de données."""

    def __init__(
        self,
        llm_client: AristoteLLMClient,
        prompt_config: PromptConfig,
        data_gen_config: DataGenerationConfig,
        logs_dir: str = "./logs",
        on_prompt_display: Optional[Callable[[str, str], None]] = None,
    ):
        """
        Initialise le juge LLM.

        Args:
            llm_client: Client LLM
            prompt_config: Configuration des prompts
            data_gen_config: Configuration génération de données
            logs_dir: Répertoire des logs
            on_prompt_display: Callback pour afficher les prompts
        """
        self.llm_client = llm_client
        self.prompt_config = prompt_config
        self.data_gen_config = data_gen_config
        self.logs_dir = Path(logs_dir)
        self.on_prompt_display = on_prompt_display

        # Crée le répertoire de logs
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _display_prompt(self, prompt_type: str, prompt: str):
        """Affiche un prompt à l'utilisateur."""
        if self.prompt_config.display_console:
            print("\n" + "=" * 70)
            print(f"PROMPT LLM JUGE ({prompt_type.upper()})")
            print("=" * 70)
            print(prompt)
            print("=" * 70 + "\n")

        if self.on_prompt_display:
            self.on_prompt_display(prompt_type, prompt)

    def _save_prompt(self, iteration: int, prompt_type: str, prompt: str, response: str):
        """Sauvegarde un prompt et sa réponse."""
        if not self.prompt_config.save_to_file:
            return

        iteration_dir = self.logs_dir / f"iteration_{iteration:03d}"
        iteration_dir.mkdir(parents=True, exist_ok=True)

        # Sauvegarde le prompt
        prompt_file = iteration_dir / f"prompt_{prompt_type}.txt"
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        # Sauvegarde la réponse
        response_file = iteration_dir / f"response_{prompt_type}.txt"
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(response)

    def _build_evaluation_prompt(
        self,
        pseudo_result: PseudonymizationResult,
        ner_labels: List[str],
    ) -> str:
        """Construit le prompt d'évaluation."""
        entities_str = "\n".join([
            f"- [{label}] \"{text}\" (position {start}-{end})"
            for start, end, label, text in pseudo_result.entities_detected
        ])

        prompt = f"""Tu es un expert en protection des données personnelles (RGPD) dans le domaine éducatif français.

TÂCHE : Évaluer la qualité de pseudonymisation d'un document scolaire.

DOCUMENT ORIGINAL :
{pseudo_result.original_text}

DOCUMENT PSEUDONYMISÉ :
{pseudo_result.pseudonymized_text}

ENTITÉS DÉTECTÉES PAR LE MODÈLE :
{entities_str if entities_str else "(Aucune entité détectée)"}

LABELS NER DISPONIBLES :
{", ".join(ner_labels)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITÈRES D'ÉVALUATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Évalue selon 5 critères (score /100) :

1. EXHAUSTIVITÉ (/30) : Toutes les données sensibles sont-elles pseudonymisées ?
   - Noms/prénoms élèves
   - Établissements scolaires
   - Cursus/formations
   - Données identifiantes (numéros, adresses...)

2. PRÉCISION (/25) : Y a-t-il des faux positifs ?
   - Mots communs pseudonymisés à tort ?
   - Sur-pseudonymisation ?

3. COHÉRENCE (/20) : Les remplacements sont-ils cohérents ?
   - Même élève = même pseudonyme dans tout le document ?
   - Même établissement = même remplacement ?

4. PRÉSERVATION DU CONTEXTE (/15) : Le document reste-t-il compréhensible ?
   - Structure préservée ?
   - Sens intact ?
   - Lisibilité conservée ?

5. CLASSIFICATION CORRECTE (/10) : Les types d'entités sont-ils corrects ?
   - STUDENT_NAME vs TEACHER bien différenciés ?
   - SCHOOL vs LOCATION bien séparés ?
   - PROGRAM vs matières bien distingués ?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fournis ta réponse au format JSON STRICT (sans markdown, sans commentaires) :

{{
  "scores": {{
    "exhaustivite": <nombre entre 0 et 30>,
    "precision": <nombre entre 0 et 25>,
    "coherence": <nombre entre 0 et 20>,
    "contexte": <nombre entre 0 et 15>,
    "classification": <nombre entre 0 et 10>,
    "total": <somme des scores ci-dessus>
  }},
  "manques": ["entité manquée 1", "entité manquée 2", ...],
  "faux_positifs": ["faux positif 1", ...],
  "commentaires": "Analyse détaillée de la pseudonymisation"
}}
"""
        return prompt

    def evaluate_pseudonymization(
        self,
        pseudo_result: PseudonymizationResult,
        ner_labels: List[str],
        iteration: int = 0,
    ) -> EvaluationScore:
        """
        Évalue la qualité de pseudonymisation.

        Args:
            pseudo_result: Résultat de pseudonymisation
            ner_labels: Labels NER disponibles
            iteration: Numéro d'itération

        Returns:
            Score d'évaluation
        """
        prompt = self._build_evaluation_prompt(pseudo_result, ner_labels)
        self._display_prompt("évaluation", prompt)

        # Envoie au LLM
        messages = [
            {"role": "system", "content": "Tu es un expert en évaluation de pseudonymisation RGPD."},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.chat_completion(messages, temperature=0.3)

        # Sauvegarde
        self._save_prompt(iteration, "evaluation", prompt, response)

        # Parse la réponse JSON
        try:
            # Nettoie la réponse (enlève markdown si présent)
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                response_clean = "\n".join(lines[1:-1])

            data = json.loads(response_clean)

            scores = data["scores"]
            return EvaluationScore(
                exhaustivite=scores["exhaustivite"],
                precision=scores["precision"],
                coherence=scores["coherence"],
                contexte=scores["contexte"],
                classification=scores["classification"],
                total=scores["total"],
                manques=data.get("manques", []),
                faux_positifs=data.get("faux_positifs", []),
                commentaires=data.get("commentaires", ""),
            )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠ Erreur de parsing JSON : {e}")
            print(f"Réponse brute : {response}")
            # Retourne un score par défaut
            return EvaluationScore(
                exhaustivite=0, precision=0, coherence=0, contexte=0, classification=0, total=0,
                manques=[], faux_positifs=[], commentaires=f"Erreur de parsing : {response}"
            )

    def _build_generation_prompt(
        self,
        evaluation_score: EvaluationScore,
        ner_labels: List[str],
        iteration: int,
    ) -> str:
        """Construit le prompt de génération de données d'entraînement."""
        manques_str = "\n".join([f"- {m}" for m in evaluation_score.manques]) if evaluation_score.manques else "(Aucune)"
        faux_positifs_str = "\n".join([f"- {fp}" for fp in evaluation_score.faux_positifs]) if evaluation_score.faux_positifs else "(Aucun)"

        prompt = f"""Tu es un générateur de données d'entraînement pour améliorer un modèle NER spécialisé dans la pseudonymisation de documents scolaires français.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Le modèle actuel (itération #{iteration}) a pseudonymisé des documents mais a commis des erreurs.

SCORE OBTENU : {evaluation_score.total}/100 (seuil requis: 98/100)

DÉTAIL DES SCORES :
- Exhaustivité : {evaluation_score.exhaustivite}/30
- Précision : {evaluation_score.precision}/25
- Cohérence : {evaluation_score.coherence}/20
- Contexte : {evaluation_score.contexte}/15
- Classification : {evaluation_score.classification}/10

ENTITÉS MANQUÉES ({len(evaluation_score.manques)}) :
{manques_str}

FAUX POSITIFS ({len(evaluation_score.faux_positifs)}) :
{faux_positifs_str}

COMMENTAIRES :
{evaluation_score.commentaires}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TÂCHE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Génère {self.data_gen_config.examples_per_iteration} exemples d'entraînement contextualisés au domaine scolaire français pour corriger ces erreurs spécifiques.

LABELS NER DISPONIBLES :
- STUDENT_NAME : Nom/prénom d'élève
- SCHOOL : Établissement scolaire (école/collège/lycée)
- PROGRAM : Cursus/formation/diplôme
- TEACHER : Nom d'enseignant/personnel
- LOCATION : Ville/adresse
- DATE : Dates
- ID_NUMBER : Numéros d'identification (INE, etc.)
- GRADE : Notes et résultats

CONTRAINTES :
1. Les exemples doivent refléter des situations réelles de documents scolaires français
2. Varier les contextes : dossiers élèves, bulletins, lettres de motivation, documents administratifs
3. Inclure les patterns qui ont posé problème dans l'évaluation
4. Mélanger des cas simples et complexes
5. Respecter le système éducatif français (écoles primaires, collèges, lycées, études supérieures)

FORMAT DE SORTIE (JSON STRICT, sans markdown) :

{{
  "training_examples": [
    {{
      "text": "Sophie Martin, élève en Terminale S au lycée Victor Hugo de Paris, souhaite intégrer une classe préparatoire.",
      "entities": [
        [0, 13, "STUDENT_NAME"],
        [38, 68, "SCHOOL"],
        [72, 77, "LOCATION"],
        [98, 119, "PROGRAM"]
      ],
      "context": "Lettre de motivation - poursuite d'études"
    }},
    ...
  ],
  "reasoning": "Explication brève de la stratégie de génération utilisée"
}}

GÉNÈRE MAINTENANT {self.data_gen_config.examples_per_iteration} EXEMPLES :
"""
        return prompt

    def generate_training_data(
        self,
        evaluation_score: EvaluationScore,
        ner_labels: List[str],
        iteration: int,
    ) -> List[TrainingExample]:
        """
        Génère des données d'entraînement basées sur l'évaluation.

        Args:
            evaluation_score: Score d'évaluation
            ner_labels: Labels NER disponibles
            iteration: Numéro d'itération

        Returns:
            Liste d'exemples d'entraînement
        """
        prompt = self._build_generation_prompt(evaluation_score, ner_labels, iteration)
        self._display_prompt("génération de données", prompt)

        # Envoie au LLM
        messages = [
            {"role": "system", "content": "Tu es un générateur expert de données d'entraînement NER."},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.chat_completion(messages, temperature=0.8, max_tokens=4000)

        # Sauvegarde
        self._save_prompt(iteration, "generation", prompt, response)

        # Parse la réponse JSON
        try:
            # Nettoie la réponse
            response_clean = response.strip()
            if response_clean.startswith("```"):
                lines = response_clean.split("\n")
                response_clean = "\n".join(lines[1:-1])

            data = json.loads(response_clean)

            examples = []
            for ex in data["training_examples"]:
                examples.append(TrainingExample(
                    text=ex["text"],
                    entities=[(e[0], e[1], e[2]) for e in ex["entities"]],
                    context=ex.get("context", ""),
                ))

            print(f"✓ {len(examples)} exemples générés")
            return examples

        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠ Erreur de parsing JSON : {e}")
            print(f"Réponse brute : {response}")
            return []
