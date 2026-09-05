# Project Meltdown — journal de réalisation et décisions

Ce journal alimente le [rapport](rapport.md). Le [cadrage](cadrage.md) contient les propositions de périmètre. Une proposition ne devient une décision retenue qu'après arbitrage explicite ; une réalisation n'est indiquée comme vérifiée qu'avec une preuve.

## Suivi du travail

- [x] Lire le concept et examiner l'état du dépôt.
- [x] Préparer une proposition de périmètre et une base de rapport.
- [ ] Recueillir les contraintes du hackathon.
- [x] Arrêter le périmètre et documenter la conception approuvée.
- [x] Préparer le plan d'implémentation.
- [x] Réaliser et vérifier les jalons retenus.
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

## 3 septembre 2026 — premier MVP local

**Autorisation.** L'utilisateur a validé le graphe et demandé de commencer l'implémentation. Travail sur la branche `codex/meltdown-mvp` dans le dépôt local.

**Réalisé.** Moteur Python, FastAPI, checkpoints SQLite, boucle LangGraph avec interruption joueur, distribution dynamique des quatre personnages et seconde ronde ciblée ; dashboard Next.js en français, actions, fiches, journal, trace du graphe, reprise et export public. Politiques à règles par défaut et adaptateur LangChain configurable. Coach déterministe ou sélection LLM de faits déjà validés.

**Vérifications.** 18 tests backend passants, Ruff sans erreur, build Next.js avec TypeScript réussi. Deux parcours complets via le proxy public : livraison négociée (budget 22, confiance 66, moral 68, 22 activations) et absence d'intervention (échéance non tenue, budget 28, confiance 30, moral 51, 25 activations). Preuves dans `docs/evidence/`.

**Revue et corrections.** Une revue indépendante en lecture seule a vérifié la persistance, les sorties d'agents et les reprises. Corrections des lots contradictoires à la livraison, des appels après fin, des effets répétés, du mode affiché et de la conservation des requêtes après erreur HTTP ambiguë. Un test protège aussi les références causales d'un audit contre une attribution à une décision sans rapport.

**Limites.** Le mode LLM n'a pas été exercé contre un fournisseur réel. Une alerte de dépréciation Starlette/AnyIO apparaît dans les tests. Pas de test avec participants, d'injection de panne navigateur, de 3D ou de déploiement public. Le rapport distingue ces limites des résultats observés.

**Choix d'implémentation.** Le même nœud LangGraph `agent` est paramétré par personnage. La sélection LLM du coach conserve le texte factuel du moteur. La version publique est projetée explicitement ; les flux internes ne sont pas transmis au navigateur. Les parties sont conservées dans `.data/`, ignoré par Git.


## 3 septembre 2026 — interface anglaise et calibration OpenAI

**Demande.** Passer tout le contenu du site en anglais, continuer l'implémentation et tester la clé OpenAI déjà fournie afin de choisir un modèle efficace et abordable.

**Réalisé.** Traduction du briefing, dashboard, actions, erreurs, personnages, événements, débrief et instructions des modèles. Les anciennes parties françaises restent enregistrées ; la reprise des parties anglaises possède son propre identifiant navigateur. Le rapport est conservé en français.

**Calibration.** Comparaison Luna/nano, test du raisonnement low, puis trois parties complètes et corrections ciblées. La configuration locale retient `openai:gpt-5.6-luna`, `none`, 384 tokens et 20 secondes, sans retry fournisseur. La clé a été préservée à l'identique sans être affichée ou versionnée. Le serveur a été relancé en mode `llm`.

**Constats et ajustements.** Description des actions autorisées, termes réels des propositions, identité et interdiction de s'envoyer un message. Un échec du coach a motivé l'envoi d'un identifiant unique par moment. La revue indépendante a identifié des unités de travail ambiguës et une validation technique absente du contexte ; ces informations sont maintenant explicites. Assistance IA utilisée pour traduire, implémenter, analyser et revoir le travail.

**Résultats.** 156 appels instrumentés, environ 0,0268247 USD estimé pour ces appels. Une suite de tests a également effectué des appels non instrumentés en héritant du mode live ; son coût est inconnu et exclu de ce montant. La dernière partie livre avec budget 22, confiance 66 et moral 68 pour 0,00583 USD estimé ; elle comporte un secours de personnage et un coach LLM valide. 26 tests backend passants après isolation de la configuration locale et blocage des transports HTTP externes, Ruff et build Next.js vérifiés. HTTP 200 sur la page anglaise, état `llm` sur health et création de partie HTTP 201 via le proxy.

**Preuves et limites.** [Calibration détaillée](model-calibration.md), [trace finale](evidence/model-evaluation-final.json), essais intermédiaires conservés. Le coût est une estimation issue des tokens, pas une facture. Les sorties libres restent susceptibles d'erreur et les petits échantillons ne démontrent pas une supériorité générale ni une efficacité pédagogique. Pas de nouvelle revue visuelle navigateur ou de déploiement public.


## 4 septembre 2026 — bureau Three.js

**Demande.** Implémenter Three.js pour finaliser la présentation du jeu.

**Réalisé.** Scène isométrique React Three Fiber/Drei chargée à la demande, quatre personnages low-poly, bureaux et table de négociation, sélection des personnages et lien vers leur événement public, signaux de pression/sécurité/livraison et écran d'avancement. La géométrie est produite localement en code. Les anciennes fiches sont remplacées par une sélection compacte et une fiche détaillée sous la scène.

**Frontières.** Le bureau consomme uniquement le type public `Game`, sans appel API propre, mutation ou nouvel appel de modèle. Les négociations visibles du tour courant déterminent le rapprochement de la table ; les messages privés ne sont pas représentés. Les contrôles du jeu restent dans le tableau 2D.

**Accessibilité et coût graphique.** Sélection via boutons HTML, contrôle de caméra, pause, vue 2D, respect du mouvement réduit, arrêt de l'animation hors écran/onglet masqué, limite de ratio de pixels à 1,5 et gestion des échecs WebGL. La revue a détecté puis fait corriger un fallback qui basculait toujours en 2D et le blocage du défilement tactile par OrbitControls ; le mode caméra tactile est maintenant explicite.

**Vérification.** Cinq tests de projection frontend et les 26 tests backend isolés passent. Build Next.js/TypeScript et Ruff sans erreur. Revue indépendante du code. Aucun nouvel appel LLM pendant ce jalon ; `.env` est conservé. Le fichier `docs/evidence/threejs-checks.txt` conserve les contrôles.

**Limites.** Aucune capture, inspection DOM, interaction tactile ou mesure GPU dans un navigateur pendant ce jalon. Le fallback et les animations doivent encore être vérifiés visuellement sur le matériel de démonstration. Ni nouveaux scénarios, ni GLTF externe, ni déploiement public. Assistance IA utilisée pour l'implémentation, la revue et la documentation.


## 5 septembre 2026 — amélioration ciblée des appels LLM

**Demande et validation.** Améliorer rapidement l'usage des LLM ; trois changements validés avant implémentation : contexte de l'interpréteur, correction bornée des sorties invalides, sélection du coach sur l'ensemble des événements éligibles.

**Réalisé.** Contexte limité aux données publiques et aux huit derniers événements ; même validation métier avant le tour ; une génération corrective maximum sans secours à règles ; propagation des erreurs fournisseur ; sélection de trois moments maximum, incluant événements tardifs et types répétés. Les corrections passent par l'instrumentation existante et ne contournent pas le budget d'évaluation.

**Vérification.** Treize tests ajoutés, dont une correction via le service sans double coût ni double tour et une partie complète jusqu'au coach. Au total : 56 tests backend, 10 tests frontend, Ruff et build Next.js réussis. Preuves dans [llm-improvements-checks.txt](evidence/llm-improvements-checks.txt). Aucun appel fournisseur réel ni nouveau parcours navigateur ; coûts, latence et qualité réelle restent à réévaluer. Rapport Markdown et documentation actualisés.

**Mise à jour du rapport Word.** Ajout d’une page technique sur les contrats LLM, la correction bornée et les 56 tests backend / 10 tests frontend ; actualisation ciblée du résumé, du contrôle IA et de la conclusion. Structure et captures conservées, distinction explicite entre parcours historique et tests du nouveau contrat. DOCX rendu et 11 pages vérifiées visuellement ; PDF associé synchronisé.

**Réécriture du rapport courant.** Rapport entièrement restructuré en six pages et environ 1 480 mots, avec cinq captures produit et une figure d’architecture. Présentation continue du concept, du moteur, des contrats LLM, de l’orchestration, de la persistance, de la 3D et de la validation ; suppression des ajouts datés du rapport. Markdown, DOCX et PDF synchronisés, six pages contrôlées visuellement.
