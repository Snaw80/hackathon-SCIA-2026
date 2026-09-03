# Project Meltdown

Un serious game de gestion de crise : six tours, quatre personnages, deux décisions de gestion par tour. Le joueur dirige la livraison d'un projet numérique sous pression, puis consulte un débrief fondé sur les événements de sa partie.

## Lancer l'application

Prérequis : Node.js 20.9+ avec npm et [uv](https://docs.astral.sh/uv/). `uv` installe Python 3.12 si nécessaire.

```bash
test -f .env || cp .env.example .env
./scripts/dev.sh
```

Ouvrir **http://127.0.0.1:3000**. Le serveur Python écoute sur **http://127.0.0.1:8000**, avec la documentation API sur `/docs`. Le script démarre les deux processus ; Ctrl+C les arrête. Ne pas lancer une deuxième instance sur les mêmes ports.

Pour les démarrer séparément :

```bash
uv sync --locked
uv run uvicorn meltdown.api:app --app-dir backend --host 127.0.0.1 --port 8000
```

Dans un autre terminal :

```bash
npm --prefix web ci
npm --prefix web run dev
```

## Jouer

1. Prendre les commandes depuis le briefing.
2. Choisir zéro, une ou deux actions, puis résoudre le tour.
3. Lire les réactions, consulter les indicateurs et, si utile, l'onglet Orchestration.
4. Obtenir un accord de périmètre ou de report, terminer et valider le travail avant de livrer.
5. Consulter le débrief et ses événements sources ; exporter la trace publique avec le bouton de téléchargement du journal.

Les tâches acceptées continuent d'un tour à l'autre. Les personnages agissent aussi sans sollicitation directe. Une partie se termine à la livraison, au sixième tour ou si la confiance client entraîne une rupture du contrat. Le navigateur mémorise seulement l'identifiant de la dernière partie ; le serveur garde l'état.

## Agents et modèles

Le mode par défaut, `MELTDOWN_AGENT_MODE=rules`, fonctionne sans clé ni appel externe. Ce sont des politiques déterministes dans le **vrai graphe LangGraph**, et l'interface les identifie comme telles.

Pour utiliser des modèles via LangChain, configurer dans `.env` :

- `MELTDOWN_AGENT_MODE=llm`
- `MELTDOWN_MODEL` : `openai:gpt-5.6-luna`, retenu après les essais locaux.
- `MELTDOWN_REASONING_EFFORT=none`, `MELTDOWN_MAX_OUTPUT_TOKENS=384`, `MELTDOWN_TIMEOUT_SECONDS=20`.
- La clé du fournisseur correspondant ; les intégrations OpenAI et Anthropic sont installées.

Redémarrer le serveur et démarrer une nouvelle partie. Le mode d'une partie est fixé à sa création ; une reprise avec un mode différent est refusée pour éviter d'étiqueter incorrectement les résultats. Les appels utilisent une sortie structurée, un plafond de 384 tokens de sortie, un timeout de 20 secondes et aucune relance automatique du fournisseur. Une erreur ou une intention invalide active la politique de secours ; la trace l'indique. Au maximum huit appels aux personnages par tour, puis un appel de sélection pédagogique en fin de partie en mode LLM.

Le coach LLM sélectionne et ordonne des moments parmi des faits déjà rédigés par le moteur. Il ne produit pas de nouvelles affirmations factuelles libres. Un bilan à règles reste disponible si le coach échoue.

Le modèle a été testé avec des appels OpenAI réels. Les tests automatisés imposent le mode à règles et bloquent les appels HTTP externes, indépendamment du `.env` local. Le [protocole, les résultats et le coût estimé](docs/model-calibration.md) sont documentés. La clé reste dans `.env`, ignoré par Git. Le plafond de sortie comprend les éventuels tokens de raisonnement ; aucune relance automatique n'est effectuée.

## Architecture

- `web/` : Next.js, React et TypeScript ; tableau de commandement en anglais et proxy `/api` vers FastAPI.
- `backend/meltdown/graph.py` : pause joueur avec `interrupt`, reprise par `Command`, distribution avec `Send`, collecte des intentions et deux rondes maximum.
- `scenario.py` : faits, personnages, actions et observations privées.
- `engine.py` : règles, validations, conséquences et progression du temps.
- `agents.py` : politiques à règles, adaptateur LangChain et sélection du coach.
- `store.py` et `service.py` : SQLite canonique, reçus idempotents, checkpoints et sérialisation locale des mutations.
- `projection.py` : vue publique et débrief lié aux événements.

Les agents d'une ronde voient le même instantané filtré pour chacun. Les messages validés sont transmis à la ronde suivante ; ceux qui dépassent le budget de deux rondes attendent le prochain tour. Le travail et le temps avancent une seule fois. Les LLM ne modifient jamais directement les métriques.

Les parties et checkpoints sont dans `.data/`, ignoré par Git. Les mutations sont sérialisées par le service : utiliser **un seul processus Uvicorn**, sans `--workers`. Cette version vise une démonstration locale ; elle n'inclut pas l'authentification ou l'isolation d'utilisateurs d'un hébergement public.

## Vérifier et produire des preuves

```bash
uv run pytest -q
uv run ruff check backend
npm --prefix web run build
```

Avec les serveurs lancés, enregistrer deux parcours complets via le proxy public :

```bash
python3 scripts/demo.py
```

En mode LLM, ce script effectue des appels payants. Pour une comparaison explicitement bornée (maximum 0,25 USD par exécution) :

```bash
uv run python scripts/evaluate_models.py --models gpt-5.6-luna --play gpt-5.6-luna --budget-usd 0.15
```

Cet essai utilise une base temporaire et sauvegarde les résultats dans `docs/evidence/model-evaluation.json`. Le plafond couvre cet essai seulement ; les parties jouées dans l'application consomment leur propre budget API.

Les JSON publics sont enregistrés dans `docs/evidence/`. Ce script crée deux nouvelles parties et ne modifie pas la partie affichée dans le navigateur.

## Documentation du hackathon

- [Concept initial](brainstorm.md)
- [Cadrage](docs/cadrage.md)
- [Graphe d'orchestration](docs/graphe-orchestration.md)
- [Plan d'implémentation](docs/superpowers/plans/2026-09-03-meltdown-mvp.md)
- [Rapport](docs/rapport.md)
- [Journal](docs/journal.md)

Le premier MVP livré est le tableau 2D jouable en anglais, avec agents OpenAI évalués. Le rapport reste en français. Les anciennes parties françaises restent en base ; l'interface anglaise mémorise séparément sa dernière partie. Le bureau 3D, les essais pédagogiques avec des participants et l'hébergement restent les prochains jalons.
