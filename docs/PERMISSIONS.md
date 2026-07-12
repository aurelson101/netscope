# Permissions et rôles

L’API constitue la barrière de sécurité. L’interface masque les commandes indisponibles pour rendre le rôle compréhensible, mais un contrôle `require(...)` doit rester présent sur chaque route d’écriture.

Le rôle Lecteur est prévu pour un affichage passif, par exemple sur une TV : il peut naviguer, filtrer et consulter, sans déclencher d’action ni extraire de données.

| Capacité | Lecteur | Opérateur | Administrateur |
| --- | :---: | :---: | :---: |
| Consulter dashboard, actifs, IPAM, scans et topologie | oui | oui | oui |
| Exporter ou télécharger des données et rapports | non | oui | oui |
| Modifier son mot de passe et son MFA | non | oui | oui |
| Créer/modifier/archiver des actifs | non | oui | oui |
| Lancer et planifier des scans, tester DNS/SNMP | non | oui | oui |
| Gérer les adresses, plages, réservations et relations | non | oui | oui |
| Envoyer ponctuellement un rapport SMTP | non | oui | oui |
| Supprimer sites, réseaux, VLAN et préfixes | non | non | oui |
| Restaurer des archives | non | non | oui |
| Gérer utilisateurs, sessions et identifiants SNMP | non | non | oui |
| Versionner la configuration et planifier les rapports | non | non | oui |

Un compte ne peut pas retirer son propre rôle administrateur. Le dernier administrateur actif ne peut pas être désactivé ou rétrogradé.
