# Project Meltdown — rapport de hackathon

**Document de travail commencé le 3 septembre 2026.** Le dépôt contient actuellement le concept et les documents de cadrage. Aucune application, expérimentation ou mesure de performance n'a encore été réalisée dans ce dépôt.

Ce rapport sera enrichi pendant le développement. Les choix proposés sont détaillés dans le [cadrage](cadrage.md) ; les réalisations et preuves sont suivies dans le [journal](journal.md).

## 1. Résumé du projet

Project Meltdown propose un serious game de gestion de crise dans un projet numérique. Le joueur doit arbitrer entre délai, sécurité, attentes du client et capacité de l'équipe. Des personnages aux objectifs et informations différents réagissent à ses décisions. Un débrief final vise à expliquer les conséquences de ces arbitrages.

Le prototype envisagé se concentre sur un scénario : « La livraison impossible ». Son ambition est de rendre visibles les effets indirects d'une décision et de permettre au joueur d'analyser son parcours. L'apport pédagogique n'est pas encore démontré.

## 2. Problématique et objectifs

Comment proposer une simulation interactive où des parties prenantes autonomes créent des arbitrages crédibles, tout en conservant des règles vérifiables et un débrief fondé sur ce qui s'est réellement passé ?

Les objectifs de conception sont les suivants :

- Donner au joueur des décisions concrètes sous information incomplète.
- Faire varier les réactions des personnages selon leurs objectifs et leurs connaissances.
- Garder les conséquences de jeu contrôlées par un moteur explicite.
- Relier les observations du débrief aux décisions et événements enregistrés.

Les critères officiels du hackathon ne sont pas encore disponibles dans le dépôt. Leur correspondance avec ces objectifs devra être ajoutée après réception.

## 3. Scénario et expérience visée

À trois jours d'une livraison, une faille de sécurité est découverte alors qu'une fonctionnalité supplémentaire a été promise au client. La capacité de l'équipe est limitée et la direction refuse initialement de reporter l'échéance.

Le joueur consulte un tableau de commandement, enquête, délègue ou négocie, puis fait avancer le temps. Les personnages réagissent selon leur propre contexte. La proposition actuelle limite la partie à six tours avec quatre personnages actifs ; ce périmètre reste à valider selon les contraintes du hackathon.

## 4. Conception et arbitrages envisagés

La séparation centrale est celle des intentions et des effets : le modèle propose une action, tandis que le moteur vérifie sa validité et applique ses conséquences. Cette séparation vise à concilier diversité des comportements et contrôle des règles.

L'information privée est une partie du gameplay. Les contextes transmis aux agents et la vue transmise au joueur doivent être filtrés côté serveur. Le débrief doit tenir compte des informations accessibles au moment de la décision.

Le Game Master est envisagé sous forme de règles de scénario pour le premier prototype. La 3D est prévue comme représentation de l'état du jeu après obtention d'un parcours jouable complet.

Une première [proposition d'arbre décisionnel](arbre-decisionnel.md) explore les branches narratives. La demande a ensuite été précisée pour porter sur le [graphe technique d'orchestration](graphe-orchestration.md) : décision et état courant, organisateur, distribution des contextes privés, intentions des personnages, résolution déterministe et nouvel état. Une boucle interne permet une redistribution des réactions dans une limite proposée de deux rondes par tour ; la boucle externe attend ensuite la prochaine décision du joueur. Cette conception est en discussion et n'a pas encore été expérimentée.

## 5. Architecture technique envisagée

L'idée initiale propose Next.js et TypeScript pour l'interface, Python et FastAPI pour l'API, LangGraph pour l'orchestration des agents et SQLite pour la persistance. Ces choix ne sont pas encore implémentés ni évalués dans ce projet.

LangGraph permet d'associer des étapes déterministes et des étapes pilotées par modèle dans un graphe avec état, ce qui motive son examen pour la résolution d'un tour. [Documentation officielle](https://docs.langchain.com/oss/python/langgraph/overview), consultée le 3 septembre 2026.

React Three Fiber est un moteur de rendu React pour Three.js, envisagé pour représenter les personnages et leurs états dans un bureau. [Documentation officielle](https://r3f.docs.pmnd.rs/), consultée le 3 septembre 2026.

La version finale de cette section devra décrire l'architecture effectivement livrée, ses interfaces, les versions utilisées et les différences avec la proposition initiale.

## 6. Méthode de réalisation et traçabilité

Le développement proposé avance par jalons : moteur jouable avec politiques à règles, interface complète, intégration des agents, débrief vérifiable, puis présentation visuelle et répétition de la démonstration.

Pour chaque jalon, le journal enregistrera le problème traité, la solution retenue, les raisons du choix, la vérification effectuée et un lien vers la preuve. Les incidents et limites seront consignés au même titre que les réussites.

Les usages d'assistance IA doivent également être documentés : tâche confiée, fichier ou résultat produit, vérification humaine ou technique et limites constatées. À ce stade, l'assistance a servi à analyser le concept et à rédiger une proposition de cadrage et cette base de rapport.

## 7. Protocole d'évaluation prévu

| Question | Méthode prévue | État actuel |
| --- | --- | --- |
| Le jeu respecte-t-il ses règles ? | Tests des coûts, capacités, tours, conditions de fin et requêtes répétées | Non exécuté |
| Les informations privées restent-elles isolées ? | Inspection et tests des observations d'agents et réponses API | Non exécuté |
| Les décisions ont-elles un effet observable ? | Comparer deux stratégies documentées à partir du même état initial | Non exécuté |
| Le débrief reste-t-il fidèle à la partie ? | Vérifier les faits cités et leurs liens vers les événements | Non exécuté |
| L'expérience est-elle utilisable en démonstration ? | Partie complète, mesure des temps de réponse et essai en mode de secours | Non exécuté |
| Le joueur comprend-il mieux ses arbitrages ? | Questions avant/après et retour qualitatif de testeurs, si le temps le permet | Non exécuté |

Pour les comparaisons, conserver la version du scénario, des règles et des prompts, le modèle utilisé, les décisions, les intentions retenues et le mode de fonctionnement. Une graine aléatoire ne suffit pas à rendre les appels LLM reproductibles.

Tout résultat futur indiquera le nombre d'essais, les conditions, la méthode et les limites. Un retour positif de quelques testeurs ne suffira pas à établir une efficacité pédagogique générale.

## 8. Résultats obtenus

Aucun résultat expérimental à ce stade. La réalisation actuelle comprend uniquement le concept fourni et les documents de cadrage, de rapport et de suivi. Les résultats chiffrés, captures et traces seront ajoutés après les vérifications correspondantes.

## 9. Limites identifiées dès la conception

- Le comportement dépendra en partie du modèle, des prompts et de leur variabilité.
- La crédibilité des arbitrages dépendra des règles et valeurs choisies pour la simulation.
- Des personnalités simplifiées ne représentent pas la diversité des comportements professionnels réels.
- Une explication générée peut inventer une causalité ; les liens vers les événements devront être contrôlés.
- La latence, le coût des appels et la disponibilité du fournisseur restent à mesurer.
- Le temps disponible peut limiter la 3D, le nombre d'essais et la validation pédagogique.

## 10. Conclusion provisoire et éléments du rendu

Le concept articule décisions de gestion, information incomplète et réactions de personnages. La prochaine étape consiste à fixer les contraintes du hackathon et un périmètre accepté avant de réaliser le premier parcours jouable.

Le rendu final devra identifier l'équipe et ses contributions, présenter l'application effectivement livrée, expliquer les principaux arbitrages, montrer des preuves de fonctionnement et discuter les limites. Le format, la longueur, les exigences de citation et l'éventuel export PDF dépendront des consignes officielles.
