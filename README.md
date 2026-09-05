# Project Meltdown

Un serious game de gestion de crise : six tours, quatre personnages, deux décisions de gestion par tour. Le joueur dirige la livraison d'un projet numérique sous pression, puis consulte un débrief fondé sur les événements de sa partie.

## Lancer l'application

Prérequis : Node.js 22.18+ avec npm et [uv](https://docs.astral.sh/uv/). `uv` installe Python 3.12 si nécessaire.

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
2. Écrire librement ce que l'on veut demander à l'équipe. L'interpréteur traduit la consigne en zéro, une ou deux décisions validées par les règles du jeu.
3. Suivre la résolution réelle dans le panneau de tour actif. Si des personnages ont besoin d'une précision, répondre à leurs questions groupées pour reprendre le même tour.
4. Lire la chronologie regroupée par tour et ronde, consulter les indicateurs et, si utile, l'onglet Orchestration.
5. Obtenir un accord de périmètre ou de report, terminer et valider le travail avant de livrer.
6. Consulter le débrief et ses événements sources ; exporter la trace publique avec le bouton de téléchargement du journal.

Une consigne claire démarre immédiatement et affiche un reçu « I understood this as ». Une consigne ambiguë attend une reformulation ou une confirmation sans consommer le tour. Les tâches acceptées continuent d'un tour à l'autre. Les personnages agissent aussi sans sollicitation directe. Une partie se termine à la livraison, au sixième tour ou si la confiance client entraîne une rupture du contrat. Le navigateur mémorise seulement l'identifiant de la dernière partie ; le serveur garde l'état, y compris une ronde en attente de réponse.

## Agents et modèles

Chaque personnage est piloté par un modèle via LangChain. Il n'existe plus de mode de personnages à règles ni de secours silencieux : une clé fournisseur et un modèle sont obligatoires. Configurer dans `.env` :

- `MELTDOWN_MODEL` : `openai:gpt-5.6-luna`, retenu après les essais locaux.
- `MELTDOWN_REASONING_EFFORT=none`, `MELTDOWN_MAX_OUTPUT_TOKENS=384`, `MELTDOWN_TIMEOUT_SECONDS=20`.
- La clé du fournisseur correspondant ; les intégrations OpenAI et Anthropic sont installées.

Les appels utilisent une sortie structurée, un plafond de 384 tokens de sortie par tentative, un timeout fournisseur de 20 secondes et une relance fournisseur. Une sortie invalide déclenche au plus une génération corrective pour l'interpréteur, les personnages et le coach. Les erreurs fournisseur ne déclenchent pas cette correction. Avec une relance fournisseur par génération, une décision logique peut entraîner jusqu'à quatre tentatives fournisseur. Chaque génération conserve les hooks de mesure et la réservation de budget dans le script d'évaluation. Une erreur persistante interrompt la ronde dans un état sauvegardé et propose une reprise explicite.

Chaque action non passive inclut une réplique, une raison courte et une émotion, affichées séparément des faits écrits par le moteur. L'interpréteur reçoit les indicateurs publics, les tâches visibles, l'état de sécurité et les huit derniers événements publics pour contextualiser la consigne. Les décisions claires restent validées par le moteur avant le démarrage du tour.

Le coach LLM sélectionne jusqu'à trois moments parmi tous les événements pédagogiques publics éligibles, y compris les événements tardifs et les répétitions d'un même type. Les références inconnues ou dupliquées sont rejetées et le texte factuel reste rédigé par le moteur.

Le modèle a été testé avec des appels OpenAI réels. Les tests automatisés injectent un faux modèle déterministe et bloquent les appels HTTP externes, indépendamment du `.env` local. Le [protocole, les résultats et le coût estimé](docs/model-calibration.md) est documenté. La clé reste dans `.env`, ignoré par Git. Le plafond de sortie comprend les éventuels tokens de raisonnement.

## Bureau 3D

Le bureau apparaît après création ou reprise d'une partie. Avec une souris, faire glisser la scène pour orienter la caméra ; sélectionner un personnage ou son bouton sous la scène pour consulter son état et rejoindre son événement dans le journal. Les touches Tab et Entrée permettent la sélection sans utiliser le canvas.

La scène montre les quatre personnages, la pression, les négociations publiques, l'avancement et l'état de sécurité connu. Elle représente le dernier état enregistré, même pendant la résolution suivante. Les contrôles permettent de suspendre les animations, réinitialiser la caméra et passer en vue 2D. Sur écran tactile, le défilement vertical reste actif ; le bouton « Orbit » active explicitement la manipulation de caméra et devient « Scroll » pour la quitter. Les animations respectent la préférence système de mouvement réduit et s'arrêtent hors écran ou dans un onglet masqué. Une indisponibilité de WebGL bascule vers la vue 2D.

Le rendu ne déclenche aucun appel LLM. Les objets low-poly sont construits localement en code, sans modèle 3D ni texture externe. La scène utilise React Three Fiber et Drei au-dessus de Three.js. Node 22.18+ est requis pour exécuter les tests TypeScript avec le lanceur natif.

## Architecture

- `web/` : Next.js, React et TypeScript ; consigne libre, suivi de ronde par polling, chronologie en anglais et proxy `/api` vers FastAPI.
- `backend/meltdown/graph.py` : pauses joueur avec `interrupt`, reprise par `Command`, distribution avec `Send`, collecte des intentions et suivi ciblé après les questions.
- `scenario.py` : faits, personnages, actions et observations privées.
- `engine.py` : règles, validations, conséquences et progression du temps.
- `agents.py` : adaptateur LangChain, contrat d'expression structuré et sélection du coach.
- `store.py` et `service.py` : SQLite canonique, rondes persistées, reçus idempotents, exécution locale en arrière-plan et checkpoints.
- `projection.py` : vue publique et débrief lié aux événements.

Les agents d'une ronde voient le même instantané filtré pour chacun. Leurs questions sont groupées à la barrière de ronde ; les réponses du joueur sont transmises uniquement aux demandeurs dans une phase de suivi bornée. Le travail et le temps avancent une seule fois. Les LLM ne modifient jamais directement les métriques.

Les parties et checkpoints sont dans `.data/`, ignoré par Git. Les mutations sont sérialisées par le service : utiliser **un seul processus Uvicorn**, sans `--workers`. Cette version vise une démonstration locale ; elle n'inclut pas l'authentification ou l'isolation d'utilisateurs d'un hébergement public.

## Vérifier et produire des preuves

```bash
uv run pytest -q
uv run ruff check backend
npm --prefix web run build
npm --prefix web test
```

Avec les serveurs lancés, enregistrer trois parcours complets via le proxy public, dont un avec une question de personnage :

```bash
python3 scripts/demo.py
```

En mode LLM, ce script effectue des appels payants. Pour une comparaison explicitement bornée (maximum 0,25 USD par exécution) :

```bash
uv run python scripts/evaluate_models.py --models gpt-5.6-luna --play gpt-5.6-luna --budget-usd 0.15
```

Cet essai utilise une base temporaire et sauvegarde les résultats dans `docs/evidence/model-evaluation.json`. Le plafond couvre cet essai seulement ; les parties jouées dans l'application consomment leur propre budget API.

Les JSON publics sont enregistrés dans `docs/evidence/`. Ce script crée trois nouvelles parties et ne modifie pas la partie affichée dans le navigateur.

## Documentation du hackathon

- [Concept initial](brainstorm.md)
- [Cadrage](docs/cadrage.md)
- [Graphe d'orchestration](docs/graphe-orchestration.md)
- [Plan d'implémentation](docs/superpowers/plans/2026-09-03-meltdown-mvp.md)
- [Rapport](docs/rapport.md)
- [Journal](docs/journal.md)

Le MVP comprend un tableau de commandement en anglais, un bureau Three.js interactif et des agents OpenAI évalués. Le rapport reste en français. Les anciennes parties françaises restent en base ; l'interface anglaise mémorise séparément sa dernière partie. Les essais pédagogiques avec des participants et l'hébergement restent les prochains jalons.
