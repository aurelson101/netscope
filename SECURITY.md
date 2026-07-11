# Sécurité

NetScope est réservé aux réseaux dont vous avez l’autorisation explicite. Les plages non valides, loopback, multicast, `/0` et grandes plages sans confirmation sont refusées. Les réseaux publics exigent une confirmation explicite via API.

Changez tous les secrets du fichier `.env`, ne l’ajoutez jamais au contrôle de source et placez l’interface derrière TLS en production. Le conteneur scanner possède les capacités réseau nécessaires; les conteneurs web n’en disposent pas. Signalez toute vulnérabilité de façon privée au mainteneur.
