# Project Meltdown — cadrage du prototype

**État au 3 septembre 2026 :** le graphe et le périmètre de la première boucle ont été approuvés pour implémentation. Le MVP local 2D est réalisé ; ce document conserve le cadrage et les pistes suivantes. Le [rapport](rapport.md) décrit précisément ce qui est livré et vérifié.

Source du concept : [brainstorm.md](../brainstorm.md). Documents associés : [rapport](rapport.md), [journal](journal.md).

Le fonctionnement technique est détaillé dans le [graphe d'orchestration LangGraph](graphe-orchestration.md). La proposition de branches narratives est conservée dans [l'arbre décisionnel](arbre-decisionnel.md).

## 1. Promesse et public

Un serious game dans lequel le joueur dirige un projet numérique en crise et découvre les conséquences techniques, humaines et commerciales de ses décisions. Le tableau de commandement constitue l'interface principale ; les échanges avec les personnages servent les décisions.

Public proposé : étudiants en informatique et futurs chefs de projet. Objectif d'une partie : faire expérimenter un arbitrage sous information incomplète, puis expliquer ses conséquences. L'efficacité pédagogique reste une hypothèse à évaluer.

## 2. Trois périmètres possibles

| Option | Contenu | Arbitrage |
| --- | --- | --- |
| Démonstrateur minimal | Tableau 2D, moteur à règles, un scénario, débrief factuel | Permet de vérifier le jeu rapidement ; ne démontre pas encore l'autonomie par LLM |
| **MVP recommandé** | Même base, quatre personnages pilotés par LLM, informations privées, historique causal, coach | Concentre l'effort sur la proposition agentique et une partie complète |
| Vision étendue | MVP et bureau 3D animé, conversations libres, plusieurs crises | Plus spectaculaire, mais davantage de travail sur les assets, l'intégration et les cas limites |

Le bureau 3D reste une cible de présentation après validation du parcours complet. Son importance dans le livrable dépendra du temps disponible et des critères du jury.

## 3. Partie proposée

- Scénario unique : « La livraison impossible ».
- Trois jours simulés, divisés en **six tours**. Une partie vise 8 à 12 minutes ; durée à mesurer.
- Jusqu'à deux décisions par tour, puis un bouton « Avancer le tour ». Le joueur peut aussi attendre.
- Quatre personnages actifs : lead developer, client, commercial, sécurité. La direction intervient par événements scénarisés.
- Six familles de décisions : enquêter, déléguer, négocier le périmètre, demander un report, communiquer, réaffecter une capacité disponible.
- Chaque décision possède une cible, un coût et des préconditions explicites. Une même ressource ne peut pas être affectée à deux tâches incompatibles.
- Un report demandé peut être refusé ou accepté sous conditions : cliquer ne garantit pas l'accord d'un personnage.
- Fin au terme du sixième tour, ou lors d'une rupture de contrat ou d'un incident critique défini par les règles.

Les demandes de report influencent l'engagement de livraison et le bilan final ; elles n'allongent pas les six tours du prototype. Les seuils et valeurs numériques devront être calibrés avant d'implémenter les règles.

### Interface

1. Briefing : rôle, échéance, faits initialement connus et objectif.
2. Tableau de commandement : temps restant, indicateurs, personnages, messages, tâches et décisions.
3. Résolution du tour : état d'attente, puis événements compréhensibles avec leurs effets observables.
4. Débrief : bilan, chronologie causale, compétences mobilisées et alternatives.

Le tableau affiche cinq indicateurs en plus du temps : avancement, budget, confiance client, moral et état du risque de sécurité. Les valeurs exactes inconnues sont remplacées par « non évalué » ou une estimation explicitement signalée. Le moteur peut conserver davantage de variables sans toutes les afficher.

### Arbitrages à rendre jouables

| Décision | Gain recherché | Contrepartie possible à modéliser |
| --- | --- | --- |
| Prioriser la correction de sécurité | Réduire le risque | Retarder la fonctionnalité promise |
| Accepter la demande du client | Préserver la relation immédiate | Accroître la charge et réduire la marge de livraison |
| Négocier une livraison partielle | Protéger la capacité de l'équipe | Exposer un désaccord avec le commercial |
| Enquêter avant de décider | Obtenir une information utile | Consommer une action et du temps |

Ces effets sont des propositions de règles de jeu, pas des lois générales sur le management. Éviter une action universellement optimale ; vérifier plusieurs stratégies sur le même scénario initial.

## 4. Responsabilités du moteur et des agents

**Le moteur possède l'état réel.** Il applique les coûts, capacités, délais, règles de sécurité et conditions de fin. Un LLM propose une intention structurée ; il ne modifie jamais directement les indicateurs.

**Les personnages décident dans un espace limité.** Chacun reçoit son rôle, ses objectifs privés, ses souvenirs pertinents, les faits qu'il connaît et les actions actuellement autorisées. Le lead choisit par exemple entre corriger, alerter, poursuivre une tâche ou refuser une surcharge.

**Le Game Master est d'abord déterministe.** Il déclenche les événements du scénario selon les tours et préconditions. Le coach intervient à la fin. Cela évite de demander sept décisions de modèles à chaque tour.

### Résolution d'un tour

1. Vérifier les décisions du joueur et la version attendue de la partie.
2. Appliquer les décisions recevables à un état de travail.
3. L'organisateur construit les observations privées et distribue une première ronde aux personnages actifs.
4. Recueillir au maximum une intention par personnage distribué, à partir du même instantané de ronde filtré pour chacun.
5. Valider les intentions et résoudre les conflits selon des priorités explicites : contraintes de sécurité, capacités disponibles, puis ordre stable des personnages. Redistribuer si nécessaire les réactions autorisées, dans une limite proposée de deux rondes par tour.
6. Calculer une seule fois le temps et la progression du travail, déclencher les événements scénarisés et enregistrer le tour de façon atomique.
7. Retourner uniquement la vue autorisée du joueur et les événements visibles.

Une information transmise entre personnages devient utilisable à la ronde suivante, uniquement pour ses destinataires. Après deux rondes, les messages restants attendent le prochain tour. Ce budget remplace la première proposition qui reportait systématiquement les interactions au tour suivant ; il est détaillé dans le graphe d'orchestration.

### Historique et confidentialité du scénario

Un événement doit conserver : identifiant, tour, acteur, type d'action, paramètres validés, effets, identifiants des événements causes et destinataires autorisés. Les liens de causalité viennent du moteur, pas d'une reconstruction libre du coach.

Le serveur filtre aussi les réponses API : un objectif privé ne doit pas se retrouver dans le navigateur sous prétexte qu'il est masqué visuellement. Les prompts ne reçoivent pas l'état global. Les logs destinés aux développeurs sont séparés de la vue du joueur ; aucune clé API n'est enregistrée dans les preuves du rapport.

Après la partie, le débrief peut révéler certains faits cachés pour expliquer la crise. Il distingue ce que le joueur savait au moment de décider de ce qui est révélé après coup.

### Défaillances prévues

- Sortie de modèle invalide ou délai dépassé : appliquer une intention de secours autorisée, enregistrer le recours au secours et poursuivre.
- Double clic ou nouvelle tentative réseau : une même requête de tour ne doit pas être appliquée deux fois.
- Échec d'enregistrement : conserver le dernier état complet, sans annoncer un tour validé.
- Coach indisponible : produire un bilan structuré à partir des événements, sans génération libre.
- Mode sans API : politiques à règles, explicitement identifiées comme mode de démonstration.

## 5. Architecture proposée

Conserver les technologies de l'idée initiale, sous réserve des compétences de l'équipe : Next.js/TypeScript pour le tableau, FastAPI/Python pour le moteur et l'API, SQLite pour les parties et événements. Commencer par une requête HTTP par tour ; ajouter le streaming seulement si une attente mesurée le justifie.

LangGraph peut orchestrer observations, intentions et validation. Sa documentation décrit le mélange d'étapes déterministes et de décisions par LLM, ainsi que la persistance. Il n'impose pas l'utilisation de LangChain : ce dernier reste optionnel pour les intégrations nécessaires. Le choix recommandé ici est une application de ces capacités au jeu, pas une architecture prescrite par la documentation. [Source officielle](https://docs.langchain.com/oss/python/langgraph/overview).

Prévoir une seule source de vérité pour l'état de partie. Les éventuels checkpoints d'orchestration doivent être reliés aux identifiants/version du tour enregistré, sans devenir un second état de jeu indépendant.

Pour la scène ultérieure, React Three Fiber permet de décrire Three.js dans React. Une caméra fixe, quatre personnages simples et des états visuels lisibles suffisent pour une première scène. Elle reflète les événements validés et ne calcule pas les règles. [Source officielle](https://r3f.docs.pmnd.rs/).

Le premier jalon vise une exécution locale mono-joueur. Hébergement public, accès aux parties et stockage durable sur l'hébergeur seront à préciser selon les exigences du hackathon.

## 6. Ordre de réalisation et preuves

| Jalon | Résultat attendu | Preuve à conserver pour le rapport |
| --- | --- | --- |
| 1. Règles | Une partie de six tours fonctionne avec des politiques à règles | Trace complète et tests des contraintes |
| 2. Parcours | Briefing → décisions → fin → débrief dans l'interface | Captures et démonstration enregistrée |
| 3. Agents | Les quatre personnages choisissent des intentions valides à partir de contextes distincts | Exemples d'observations filtrées, sorties et taux de secours |
| 4. Explication | Chaque conséquence citée par le coach référence des événements existants | Débrief annoté et vérification des références |
| 5. Présentation | Bureau 3D simple si le temps le permet, répétition de la démo | Captures, mesures de fluidité et déroulé de secours |

À chaque jalon, mettre à jour le journal et les sections concernées du rapport avant de passer au suivant. Conserver les révisions des règles, prompts et modèles pour pouvoir expliquer les résultats.

## 7. Critères d'acceptation proposés

- Terminer une partie et consulter son débrief, y compris sans accès au fournisseur de modèle.
- Obtenir au moins deux issues différentes avec deux séquences de décisions documentées.
- Interdire les actions sans ressource et l'application en double d'un tour.
- Vérifier qu'un personnage et le joueur ne reçoivent aucun fait privé non autorisé dans leur contexte respectif.
- Rattacher les affirmations factuelles du coach aux événements ; présenter les alternatives comme hypothèses, sauf si une simulation comparative les étaye.
- Rejouer exactement les transitions à partir des intentions enregistrées. Une graine seule ne garantit pas la reproduction des sorties LLM.
- Mesurer durée des tours, erreurs de validation, recours au secours, tokens et coût observé avant d'annoncer des performances.
- Vérifier que les décisions produisent des différences compréhensibles pour un testeur découvrant le jeu.

## 8. Contraintes encore à obtenir

Échéance et temps effectif de développement ; taille et compétences de l'équipe ; thème, barème et livrables imposés ; disponibilité et budget d'une API de modèle ; importance obligatoire ou facultative de la 3D ; langue et format du rendu final. Ces informations déterminent le périmètre retenu et le planning, qui ne sont pas encore engagés.
