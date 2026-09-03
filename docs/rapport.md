# Project Meltdown — rapport de hackathon

**Version de travail du 3 septembre 2026 — MVP local en anglais et premiers essais OpenAI réalisés.** Ce rapport distingue les fonctionnalités réalisées, les essais effectués et les objectifs encore non évalués. Les consignes officielles du hackathon, l'équipe et la répartition des contributions restent à renseigner avec leurs données réelles.

## 1. Résumé

Project Meltdown est un serious game de gestion de crise dans un projet numérique. Le joueur dispose de six tours pour arbitrer entre livraison, sécurité, demandes du client et capacité de l'équipe. Quatre personnages représentent le développement, le client, le commercial et la sécurité.

Le premier prototype comprend un tableau de commandement en anglais, un moteur de règles, un graphe LangGraph persistant, deux rondes d'interactions internes au maximum et un débrief lié aux événements enregistrés. Deux parcours complets ont été exécutés via l'API publique : une livraison négociée réussit, tandis qu'une partie sans intervention n'aboutit pas à une livraison.

Ces essais valident un premier fonctionnement technique. Ils ne démontrent ni l'efficacité pédagogique ni le réalisme des comportements d'un modèle de langage en conditions réelles.

## 2. Problématique et intention pédagogique

Comment simuler des parties prenantes qui disposent d'informations et d'objectifs différents, tout en conservant des conséquences vérifiables et une explication fidèle au déroulement de la partie ?

Les objectifs pédagogiques envisagés sont la priorisation sous pression, la recherche d'information, la négociation d'engagements et l'analyse des conséquences. Le joueur doit comprendre qu'un socle techniquement avancé ne constitue pas, à lui seul, une livraison acceptable : le périmètre doit être convenu et la sécurité validée.

Le public envisagé est constitué d'étudiants en informatique et de futurs chefs de projet. Aucun test d'apprentissage avec des participants n'a encore été mené.

## 3. Scénario et périmètre livré

Dans « La livraison impossible », une livraison est attendue dans trois jours. Le développeur a repéré un défaut, le client attend une fonctionnalité promise par le commercial et la capacité de l'équipe est limitée. Certaines informations sont connues d'un personnage mais pas encore du joueur.

Le joueur peut notamment auditer le défaut, prioriser le correctif ou le socle, clarifier le besoin métier, communiquer, négocier un périmètre réduit ou un report, accepter la fonctionnalité, réduire la charge, mobiliser du renfort, valider la correction puis livrer.

Les décisions sont sélectionnées dans des cartes, avec un maximum de deux par tour. La saisie libre d'instructions n'est pas implémentée. Le travail accepté continue sans demander au joueur de le réaffecter à chaque tour.

L'interface livre les éléments suivants :

- Briefing de départ et création d'une partie.
- Indicateurs du socle, du budget, de la confiance, du moral et de l'état de sécurité connu.
- Quatre fiches de personnages avec activité observable et pression.
- Actions avec coût, préconditions et état indisponible explicite.
- Journal des événements et trace des activations du graphe par ronde.
- Sauvegarde côté serveur, reprise de la dernière partie et export JSON public.
- Débrief final avec liens vers les événements et pistes alternatives clairement présentées comme hypothèses.

Le bureau 3D n'est pas inclus dans ce premier MVP. La présentation actuelle est un tableau 2D adaptatif.

## 4. Architecture réalisée

Le frontend utilise Next.js, React et TypeScript. Il appelle un proxy `/api` vers FastAPI. Python porte les règles, les personnages et l'orchestration. SQLite conserve les parties canoniques et les reçus de requêtes ; un second fichier SQLite conserve les checkpoints LangGraph.

Le [graphe conceptuel](graphe-orchestration.md) possède deux boucles. La boucle externe attend le joueur avec `interrupt()` puis reprend avec une décision. La boucle interne prépare les observations privées, distribue les agents avec `Send`, collecte les intentions, applique les règles et redistribue les réactions autorisées.

L'implémentation utilise un nœud worker `agent` paramétré par personnage. La première ronde active les quatre personnages ; la seconde sélectionne les destinataires des nouveaux messages. Les sorties sont rassemblées avec des clés stables par tour, ronde et personnage. Le graphe effectif est exporté depuis LangGraph dans [langgraph.mmd](evidence/langgraph.mmd).

La séparation entre workflow, état et agents s'appuie sur les primitives documentées par LangGraph. Les frontières métier, règles et budgets de rondes ont été conçus pour ce jeu. [Workflows et agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents), [interruptions](https://docs.langchain.com/oss/python/langgraph/interrupts), consultés le 3 septembre 2026.

### Contrôle des conséquences

Un personnage propose une intention structurée. Le moteur vérifie l'action, les connaissances et les préconditions avant d'appliquer un effet. Les sorties concurrentes ne modifient pas directement les métriques. La progression du travail et les coûts périodiques sont calculés une seule fois à la clôture du tour.

Les intentions d'une ronde utilisent un instantané cohérent, filtré pour chaque personnage. Les messages validés deviennent utilisables à la ronde suivante. Les messages produits après consommation des deux rondes attendent le tour suivant. Une livraison autorisée termine le jeu sans déclencher de nouvelles activations de personnages.

### Persistance et reprises

Chaque décision porte une version attendue et un identifiant de requête. L'état et le reçu public sont enregistrés dans une transaction. Une nouvelle tentative identique reçoit le résultat déjà enregistré ; réutiliser un identifiant pour une autre décision est refusé.

Une reprise après un échec survenu juste après le commit canonique a été testée. Les checkpoints permettent de terminer l'exécution interrompue puis de reprendre une nouvelle décision sans consommer deux fois le tour.

La version actuelle sérialise les mutations dans un seul processus Python. Elle vise une démonstration locale et ne doit pas être présentée comme un service multi-utilisateur prêt à être exposé publiquement.

## 5. Modes des agents et débrief

Le mode par défaut utilise des politiques déterministes à l'intérieur du même graphe LangGraph. Il permet de jouer sans clé API et constitue le mode des deux premiers parcours enregistrés. Il est identifié comme « Rules simulation » dans l'interface.

Un adaptateur LangChain est disponible pour un modèle configuré via l'environnement. Les personnages reçoivent leur contexte filtré et choisissent une sortie structurée. Les appels ont un plafond de 384 tokens de sortie et un timeout de 20 secondes, sans relance automatique du fournisseur. Une erreur ou une intention invalide active la politique de secours et le signale dans la trace. Le budget est limité à huit activations de personnages par tour ; la clôture d'une livraison peut en utiliser zéro.

Le coach LLM optionnel sélectionne et ordonne des moments parmi des événements déjà rédigés par le moteur. Les références sont validées ; le texte factuel reste celui des événements. Ce choix limite les affirmations causales inventées. Les relations enregistrées indiquent les décisions et messages pertinents ; elles ne prétendent pas révéler le raisonnement interne du modèle.

Des appels OpenAI réels ont maintenant été effectués. Le choix local est **GPT-5.6 Luna**, raisonnement `none`, après comparaison avec GPT-5.4 nano et un essai de raisonnement `low`. Les 156 appels d'évaluation instrumentés représentent environ **0,0268 USD estimé**. Une exécution de tests ayant hérité du mode live a produit des appels supplémentaires non mesurés ; ce montant n'est donc pas le total facturé de la session. L'isolation de la suite a été corrigée. Le [protocole détaillé](model-calibration.md) conserve les paramètres, résultats et sources de prix. Les tests automatisés de panne utilisent toujours des politiques locales pour ne pas consommer de crédit.

## 6. Vérification technique

La suite contient **26 tests backend**, tous passants lors de la vérification finale. Elle couvre notamment :

- Le nombre d'actions et les décisions impossibles.
- L'isolation d'un fait privé dans les observations et les réponses publiques.
- Le rejet d'une transmission de fait inconnu de son émetteur.
- Les rondes bornées et l'avancement du temps une seule fois.
- Les intentions de secours après échec d'un personnage.
- La reprise SQLite, les requêtes répétées et la réutilisation conflictuelle d'un identifiant.
- La reprise après un échec postérieur au commit canonique.
- La fin d'une partie, la validation globale d'un lot de décisions et l'absence d'activations après livraison.
- La non-répétition d'un gain de confiance ou d'une pénalité de suspension entre rondes.
- L'absence d'attribution d'un audit à une décision client sans rapport.
- Le refus d'un changement silencieux de mode d'agents.
- Deux issues différentes et des références de débrief existantes.
- L’indépendance de la configuration locale et le blocage réseau externe pendant les tests.
- Les plafonds de modèle, le comptage des sorties mal formées, les références privées et les messages à soi-même.
- Les termes de négociation filtrés, les unités de travail explicites, la validation technique courante et les identifiants du coach.

La sortie complète est conservée dans [pytest.txt](evidence/pytest.txt). Elle contient un avertissement de dépréciation provenant de l'intégration Starlette/AnyIO utilisée par le client de test ; aucun test ne manque à cause de cet avertissement.

Le contrôle Ruff passe et le build de production Next.js réussit, y compris la vérification TypeScript. Le parcours HTTP a été exercé à travers le proxy Next.js vers FastAPI. La page locale renvoie HTTP 200. Les erreurs réseau du frontend ont été examinées en revue de code ; aucune injection de panne dans un navigateur ni revue visuelle par captures n'a été effectuée.

Versions principales enregistrées : Python 3.12.13, Next.js 16.3.4, FastAPI 0.141.1, LangGraph 1.2.11, LangChain 1.3.18 et Pydantic 2.13.5. Les fichiers `uv.lock` et `web/package-lock.json` fixent les dépendances ; un relevé Python est disponible dans [versions.json](evidence/versions.json).

## 7. Parcours expérimentés

Les deux parcours utilisent le même scénario initial, le mode à règles et six tours. Ils sont exécutés par [scripts/demo.py](../scripts/demo.py), qui appelle les mêmes routes publiques que le navigateur et enregistre uniquement les états publics.

| Parcours | Issue | Budget final | Confiance client | Moral | Activations des personnages |
| --- | --- | --- | --- | --- | --- |
| Audit, correctif, clarification, communication et périmètre réduit | Livraison maîtrisée | 22/100 | 66/100 | 68/100 | 22 |
| Aucun nouvel ordre pendant six tours | Échéance non tenue | 28/100 | 30/100 | 51/100 | 25 |

Aucun recours au secours n'a été nécessaire dans ces deux parcours à règles. Le socle atteint 100 % dans les deux cas, mais le second parcours ne dispose pas des conditions de livraison : avancement, accord commercial et validation technique sont des dimensions distinctes.

Les fichiers [negotiated-delivery.json](evidence/negotiated-delivery.json) et [no-intervention.json](evidence/no-intervention.json) contiennent les décisions, métriques, rondes, événements et débriefs observés. Les durées internes de résolution y sont enregistrées ; ce petit échantillon local ne constitue pas un benchmark de performance.

### Essai avec le modèle réel

Le dernier parcours OpenAI atteint la livraison avec les mêmes métriques finales que le parcours négocié à règles : budget 22, confiance 66 et moral 68. Il utilise 31 activations de personnages et un coach, 21 284 tokens d'entrée et 1 311 de sortie, soit **0,00583 USD estimé**. Une intention du développeur est remplacée par le secours au cinquième tour ; le coach final utilise des références valides. Les tours actifs durent de 3,0 à 14,6 secondes dans cet essai.

Les premiers passages ont révélé une proposition insuffisamment décrite, des identifiants de coach ambigus et une confusion unités/périodes. Ces points ont été corrigés dans le contexte et protégés par des tests. La [trace finale](evidence/model-evaluation-final.json) et les [essais intermédiaires](model-calibration.md) restent disponibles, y compris les échecs observés.

L'interface, les messages système des agents, les événements, erreurs et débriefs sont en anglais ; ce rapport reste en français. Les anciennes sauvegardes françaises sont conservées, avec un identifiant de reprise distinct pour les parties anglaises.

## 8. Méthode et retours de revue

La réalisation a commencé par des tests de comportement et d'intégration, puis le moteur, le graphe persistant et l'interface ont été assemblés. Une revue de code indépendante a ensuite examiné les frontières d'état, la confidentialité, les reprises et la validation des intentions.

La revue a notamment conduit à vérifier de nouveau une livraison après application de toutes les décisions du lot, à éviter les activations après une livraison, à empêcher une révélation récompensée deux fois et à préserver l'identifiant d'une requête lors d'une erreur HTTP ambiguë. Des tests de régression ont été ajoutés aux corrections backend. Les liens d'événements ont également été resserrés pour ne pas attribuer un résultat à toutes les décisions du tour par défaut.

L'assistance IA a servi au cadrage, à la conception du graphe, à la rédaction du code et de la documentation, à la revue et à l'analyse des résultats. Les commandes et traces citées constituent les vérifications techniques réellement effectuées. Le [journal](journal.md) conserve les étapes et décisions.

## 9. Limites et prochaines étapes

- Les règles numériques constituent une première calibration de jeu, sans validation empirique du réalisme organisationnel.
- Le scénario et les politiques à règles sont fixes ; la rejouabilité observée vient surtout des décisions du joueur.
- Les agents LLM ont été testés sur un petit nombre de situations ; la variabilité sur des séries répétées et d’autres stratégies reste à mesurer.
- Le coût est instrumenté dans le script d’évaluation, sans tableau de facturation dans le produit ni plafond monétaire global des parties.
- Les messages libres peuvent contenir des affirmations inexactes malgré des intentions et références structurellement valides.
- Le débrief est volontairement contraint aux faits et à des alternatives proposées, sans simulation contrefactuelle automatique.
- Le prototype possède un verrouillage de livraison et des issues commerciales ; il ne simule pas encore un incident de cybersécurité détaillé.
- Le bureau 3D, l'authentification, l'hébergement multi-utilisateur, les conversations libres et les scénarios supplémentaires ne sont pas implémentés.
- L'accessibilité, l'ergonomie et l'apprentissage doivent encore être évalués avec des utilisateurs.

Le prochain jalon est un essai utilisateur du parcours et une évaluation répétée des comportements. Le bureau 3D pourra ensuite représenter les mêmes événements validés, sans devenir une deuxième source de règles de simulation.
