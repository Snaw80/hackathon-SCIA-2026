# Calibration des modèles — 3 septembre 2026

> Archive de calibration : ces mesures précèdent le contrat d'expression du 4 septembre 2026. Le runtime actuel est exclusivement LLM, exige une réplique, une raison et une émotion pour chaque action non passive, effectue une relance fournisseur et ne remplace plus une erreur par une politique de personnage à règles. Relancer `scripts/evaluate_models.py` pour mesurer ce nouveau contrat avec un fournisseur réel.

> Mise à jour du 5 septembre : une sortie invalide autorise désormais une seule génération corrective, elle-même soumise à une relance fournisseur. Chaque génération traverse la réservation de budget avant l'appel, y compris la correction. Une décision peut donc entraîner jusqu'à quatre tentatives fournisseur. Le contexte de l'interpréteur et les candidats du coach ont également changé. Les mesures historiques ci-dessous ne mesurent pas ces changements ; aucun nouveau coût ni gain de qualité n'a été mesuré pendant cette amélioration.

## Choix retenu

Configuration évaluée à cette date : `openai:gpt-5.6-luna`, raisonnement `none`, plafond de **384 tokens de sortie**, timeout de **20 secondes**, sans relance automatique du fournisseur. Le même modèle jouait les personnages et sélectionnait les événements du coach.

Luna est retenu pour ce prototype : il répond correctement aux intentions structurées, tient mieux compte de la surcharge que nano dans notre petit échantillon et son coût observé reste inférieur à un centime de dollar par partie. Ce choix n'établit pas une supériorité générale ; nano répondait plus vite lors de la comparaison.

## Sources et tarifs

Tarifs standards en USD par million de tokens, consultés le 3 septembre 2026 :

| Modèle | Entrée | Entrée en cache | Sortie |
| --- | ---: | ---: | ---: |
| GPT-5.6 Luna | 0,20 | 0,02 | 1,20 |
| GPT-5.4 nano | 0,20 | 0,02 | 1,25 |

Sources : [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano). Luna facture les écritures de cache à 1,25 fois le tarif d'entrée ; le script en tient compte lorsque le fournisseur rapporte ces tokens. Les essais ont utilisé de courts contextes sans tokens de cache rapportés.

La [documentation des modèles](https://developers.openai.com/api/docs/guides/latest-model) présente Luna pour les usages sensibles au coût et permet de choisir explicitement le raisonnement. Les réponses structurées et les métadonnées d'usage passent par [l'intégration LangChain OpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai). Aucun modèle plus coûteux n'a été appelé : les problèmes observés relevaient d'abord du contexte transmis.

## Protocole

L'utilisateur a autorisé les appels avec sa clé. Les essais ont été menés avec [evaluate_models.py](../scripts/evaluate_models.py), hors de la suite pytest, avec un budget global de travail annoncé de 0,25 USD. Chaque exécution réserve un montant conservateur avant chaque appel à partir des octets des messages, des schémas, d'une marge de protocole et du maximum de sortie. Les appels échoués gardent leur réservation. Le script refuse plus de 80 appels et plus de 0,25 USD par invocation ; les invocations effectuées ont utilisé des plafonds entre 0,08 et 0,25 USD. Toutes les 156 réponses de ce script ont rapporté un usage, permettant de suivre leur coût cumulé estimé. Aucun appel automatique n'est lancé au démarrage de l'application. Une validation pytest a cependant révélé un défaut d'isolation décrit ci-dessous ; le plafond du script ne couvrait pas cette exécution.

Huit situations : audit demandé, travail affecté, clarification client, proposition de périmètre réduit, développeur surchargé, correctif prêt à vérifier, client sans sollicitation et message reçu contenant une instruction hostile. On vérifie la structure, l'action autorisée et les références aux faits connus. Une préférence comportementale est également évaluée ; elle exprime un objectif de calibration, pas une unique décision légitime. Par exemple, un client peut raisonnablement demander des garanties.

Les huit situations sont exécutées une fois par configuration. Il n'y a ni échantillonnage statistique ni évaluation humaine de l'apprentissage. Les sorties restent non déterministes. Le test « client sans sollicitation » acceptait seulement `wait` dans la première exploration ; il accepte ensuite aussi un message proactif, cohérent avec l'autonomie recherchée. Les scores de ces deux versions ne sont donc pas directement comparables.

## Résultats de la comparaison

Avec les descriptions d'actions explicites, avant ajout des termes de négociation :

| Configuration | Sorties valides | Préférences comportementales satisfaites | Médiane par appel | Coût des 8 cas |
| --- | ---: | ---: | ---: | ---: |
| Luna, none, 384 tokens | 8/8 | 7/8 | 2,263 s | 0,001274 USD |
| nano, none, 384 tokens | 8/8 | 6/8 | 0,983 s | 0,001330 USD |
| Luna, low, 512 tokens | 8/8 | 7/8 | 2,345 s | 0,001628 USD |

Le raisonnement `low` n'a pas amélioré ces préférences et a consommé davantage de sortie (607 tokens contre 312). Le réglage `none` a donc été conservé. Après ajout des termes concrets de la proposition, Luna a satisfait les huit préférences lors de deux passages supplémentaires, sans changement vers un modèle plus cher.

Preuves : [exploration initiale](evidence/model-evaluation-baseline.json), [comparaison sans raisonnement](evidence/model-evaluation-none.json), [raisonnement low](evidence/model-evaluation-low.json), [première partie](evidence/model-evaluation-coach-fallback.json), [correction du coach](evidence/model-evaluation-coach-fixed.json), [partie avec contexte final](evidence/model-evaluation-final.json).

## Corrections issues des essais

- Des identifiants d'actions seuls étaient ambigus : ajout de descriptions limitées aux actions autorisées et rappel de l'identité du personnage.
- Le client demandait des garanties sur une offre dont les termes ne lui étaient pas transmis : ajout du contenu réel de la proposition aux observations client et commercial seulement.
- Le coach a sélectionné une référence causale au lieu de l'événement principal : il reçoit désormais un seul `event_id` explicite par moment, avec son titre et son analyse. Les références sont toujours validées.
- Une revue indépendante a identifié une confusion entre unités de travail et périodes, ainsi qu'une alerte de sécurité périmée : les rôles techniques reçoivent les unités, les débits normaux et la validation de sécurité actuelle. Dans la trace finale, le développeur décrit correctement six unités comme trois périodes normales ; les messages suivants confirment la validation acquise.
- Les messages envoyés à soi-même sont refusés et déclenchent la politique de secours.

## Partie finale et coût des essais instrumentés

Le dernier essai exécute six tours dans le vrai graphe avec SQLite temporaire : audit/correctif, clarification/communication, périmètre réduit/repos, deux tours de travail, livraison. Résultat : **Delivery under control**, progression 100 %, budget 22/100, confiance 66/100 et moral 68/100.

Il consomme **31 appels de personnages et un appel de coach**, soit **21 284 tokens d'entrée et 1 311 tokens de sortie**, pour **0,005830 USD estimé**. Le coach retourne des références valides. Une intention du développeur au cinquième tour est rejetée par la validation métier et remplacée par les règles ; les sorties étaient toutes syntaxiquement valides. La trace indique ce secours, sans enregistrer le contenu rejeté. Aucun timeout n'a été observé.

Les tours actifs prennent 3,0 à 14,6 secondes dans ce passage (le premier est le plus lent), puis 1,1 seconde pour livrer et produire le débrief. La médiane des appels modèle est de 1,372 seconde. Ces durées sont des observations ponctuelles, pas un engagement de performance.

Les six exécutions instrumentées totalisent **156 appels et 0,0268247 USD estimé**, environ **0,03 USD**. Les coûts sont calculés sur les tokens rapportés et les tarifs ci-dessus ; ils ne constituent pas une facture et excluent hébergement et taxes. Le plafond de l'évaluation ne limite pas les futures parties de l'application : chaque partie en mode LLM est payante. Les deux rondes, les huit activations maximales par tour, le plafond de sortie et l'absence de retries bornent le travail du modèle.

## Incident d'isolation des tests

Après activation de `llm` dans `.env`, une exécution de la suite automatisée a hérité de ce mode et effectué des appels supplémentaires sans instrumentation des tokens. Elle a pris 138,01 secondes : 24 tests ont passé et le test de changement de mode a échoué, révélant la dépendance à la configuration locale. Le coût de cette exécution n'est pas connu ; **0,0268247 USD est le total des essais instrumentés seulement**, et non le total facturé pour cette session. Le budget de 0,25 USD du script n'était pas appliqué à cette suite. La facturation fournisseur reste la source pour le total du compte.

Correction actuelle : la suite injecte un faux modèle déterministe et bloque les transports HTTP/HTTPS externes synchrones et asynchrones. Le transport interne FastAPI reste disponible. Aucun test automatisé ne dépend d'une clé fournisseur.

## Limites

Le moteur valide les actions, les références de faits et les mutations, mais ne prouve pas automatiquement chaque affirmation d'un message libre. Une formulation inexacte reste possible ; les traces doivent être examinées avant de prétendre à un réalisme pédagogique. Les corrections ont amélioré les exemples observés, sans supprimer ce risque. Des séries répétées, d'autres styles de jeu et des essais avec participants restent nécessaires.
