# Architecture

L’API valide et planifie les demandes. Le worker orchestre les tâches, tandis que le conteneur scanner possède seul les outils réseau. Les résultats suivent ce flux :

`RawObservation (immuable) → Evidence (fait sourcé) → Correlator → Asset + AssetHistory`

Une IP n’est jamais une identité. Le corrélateur privilégie MAC, identifiants matériels et empreintes stables, et refuse les fusions ambiguës. PostgreSQL est la source de vérité; Redis transporte les tâches Celery. Les secrets proviennent exclusivement de l’environnement ou de secrets Docker.

Le MVP conserve les modules de découverte comme plugins indépendants. Le scanner appelle les exécutables via des tableaux d’arguments, sans shell, et Nmap est interprété depuis XML.
