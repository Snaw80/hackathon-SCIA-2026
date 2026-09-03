# Project Meltdown — journal de réalisation et décisions

Ce journal alimente le [rapport](rapport.md). Le [cadrage](cadrage.md) contient les propositions de périmètre. Une proposition ne devient une décision retenue qu'après arbitrage explicite ; une réalisation n'est indiquée comme vérifiée qu'avec une preuve.

## Suivi du travail

- [x] Lire le concept et examiner l'état du dépôt.
- [x] Préparer une proposition de périmètre et une base de rapport.
- [ ] Recueillir les contraintes du hackathon.
- [ ] Arrêter le périmètre et documenter la conception approuvée.
- [ ] Préparer le plan d'implémentation.
- [ ] Réaliser et vérifier les jalons retenus.
- [ ] Consolider les résultats, limites et preuves dans le rapport final.

## 3 septembre 2026 — cadrage initial

**Constat.** Le dépôt contient `brainstorm.md`, sans code applicatif ni premier commit au moment de l'inspection.

**Travail effectué.** Lecture du concept ; identification du risque de périmètre lié à la simulation, aux agents, à la 3D et au débrief ; rédaction de `cadrage.md`, `rapport.md` et du présent journal. Consultation des documentations officielles LangGraph et React Three Fiber citées dans le rapport.

**Statut.** Documentation initiale. Aucune fonctionnalité applicative ou mesure de performance réalisée. Les choix ci-dessous restent proposés.

| ID | Proposition | Motif | Statut |
| --- | --- | --- | --- |
| P-001 | Un scénario, six tours et quatre personnages actifs | Obtenir une partie complète avec une portée limitée | Proposé |
| P-002 | Intentions par LLM, effets par moteur déterministe | Vérifier les conséquences et maîtriser les règles | Proposé |
| P-003 | Game Master à règles et coach en fin de partie | Limiter les appels et conserver un rythme contrôlable | Proposé |
| P-004 | Tableau 2D jouable avant le bureau 3D | Valider la boucle principale avant la présentation animée | Proposé |
| P-005 | Historique causal et rapport mis à jour à chaque jalon | Conserver les preuves au moment où elles sont produites | Proposé |
| P-006 | Mode de secours à règles, identifié dans l'interface et les traces | Permettre une démonstration même sans fournisseur LLM | Proposé |

**Questions ouvertes.** Échéance, équipe, consignes du jury, budget modèle, exigences de 3D et format du rapport.

## 3 septembre 2026 — branches et autonomie des personnages

**Demande.** Après un accueil favorable du premier cadrage, approfondir l'arbre décisionnel et les interactions entre agents avant de commencer l'implémentation.

**Travail effectué.** Rédaction de [l'arbre décisionnel](arbre-decisionnel.md) : comparaison de trois approches, proposition hybride, six jalons, trois ouvertures possibles, branche de négociation, pouvoirs des quatre personnages et dimensions du bilan. Ajout de deux schémas Mermaid dans le document. Assistance IA utilisée pour formuler et examiner cette proposition.

**Arbitrages proposés.** Conserver l'état lors de la convergence des branches ; rendre les communications entre agents disponibles au tour suivant ; distinguer promesse, accord et validation ; permettre le redressement après une mauvaise décision. Les tâches acceptées continuent selon les règles sans nouvelle instruction à chaque tour.

**Statut et limites.** Brouillon à discuter ; aucun résultat de simulation. La liberté de saisie du joueur, les faits cachés supplémentaires et les valeurs numériques restent à arbitrer. Les contraintes du hackathon restent à recueillir.

## 3 septembre 2026 — clarification du graphe technique

**Clarification.** L'utilisateur demande le graphe d'exécution LangGraph : entrée et état → organisateur → personnages en interaction → nouvel état → décision suivante. La proposition narrative précédente ne répondait pas directement à cette demande.

**Travail effectué.** Rédaction de [graphe-orchestration.md](graphe-orchestration.md), avec deux boucles, les responsabilités des nœuds, l'état partagé, la collecte des sorties et un exemple de redistribution. Consultation des références officielles Graph API, orchestrator-worker, interrupts et persistence. Mise en cohérence du cadrage et du rapport ; conservation des branches narratives comme document distinct.

**Ajustement proposé.** Deux rondes internes par tour, une première occasion autonome pour chaque personnage puis redistribution ciblée. Les messages deviennent accessibles à la ronde suivante ; l'excédent est reporté au prochain tour. Le temps de travail avance une seule fois par tour. Cette proposition remplace la limite initiale d'une seule intention et des échanges toujours reportés au tour suivant.

**Statut.** Conception technique en discussion, sans code ni validation expérimentale. La question précédente sur la saisie libre est secondaire et ne bloque pas cette discussion.

## Format des prochaines entrées

Ajouter une entrée datée après chaque jalon ou arbitrage significatif avec : objectif, changement réalisé, raison du choix, contributeurs et assistance IA, vérification effectuée, résultat observé, preuve consultable et limites restantes.

Pour une mesure, préciser le protocole, le nombre d'essais et les versions. Pour une capture ou une trace, relier le fichier à la version du jeu concernée. Les traces partagées dans le rapport doivent exclure les secrets de configuration.
