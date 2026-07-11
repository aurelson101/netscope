# NetScope — plan d’implémentation

## MVP (ce dépôt)

1. Stack Compose isolant API, worker, scheduler et scanner, avec PostgreSQL et Redis.
2. Modèle piloté par les preuves : résultats bruts immuables, preuves normalisées, actifs corrélés et historique.
3. Authentification locale JWT (administrateur, opérateur, lecteur), sites, sous-réseaux, profils et tâches de scan.
4. Plugins ICMP, ARP, Nmap XML et DNS inverse exécutés hors de l’API.
5. Dashboard, inventaire filtrable/exportable, fiche actif et historique des scans.
6. Tests des règles de sécurité, du parseur Nmap, de la corrélation et de l’API.

## Jalon 2

SNMPv3, tables ARP/MAC, VLAN, LLDP/CDP, corrélation au port et graphe de topologie.

## Jalon 3

Sondes distantes signées, découverte passive, connecteurs DHCP et empreintes avancées.

Les réseaux découverts ne sont jamais scannés automatiquement. Toute cible doit être autorisée et les réseaux publics nécessitent une confirmation explicite.
