# Feuille de route — état au 18 juillet 2026

## Livré le 12 juillet 2026

- [x] Migrations Alembic versionnées, exécutées au démarrage et testées en montée/descente.
- [x] Gestion des utilisateurs, rôles, activation des comptes et révocation des sessions.
- [x] Planificateur de scans persistant et modifiable depuis l’interface.
- [x] Test SNMP interactif et diagnostic des OID par équipement.
- [x] VRF, hiérarchie IPAM, plages IP et réservations DHCP.
- [x] Exports CSV/PDF et planification des envois SMTP.
- [x] Tests navigateur Playwright et CI GitHub Actions.
- [x] Versionnement et sauvegarde JSON des configurations applicatives.
- [x] Reverse proxy Caddy HTTPS prêt à l’emploi et documenté.
- [x] Reconnaissance des constructeurs par enterprise OID et base OUI hors ligne.

## Prochaines améliorations

- [ ] Ajouter des migrations incrémentales pour chaque évolution future du schéma.
- [ ] Étendre les diagnostics aux MIB propriétaires installables par constructeur.
- [ ] Ajouter un scénario Playwright couvrant IPAM, les scans planifiés et les rapports.
- [ ] Automatiser le rafraîchissement vérifié de la base OUI hors ligne.

## Sondes et découverte réseau

- [x] Agent distant authentifié, heartbeat, remontée des capacités et alerte hors ligne.
- [x] Exécution distante des modules ICMP, ARP, Nmap et DNS.
- [x] Menu Sonde avec lancement immédiat, suivi à 3 secondes et équipements observés.
- [x] Inventaire des routes IPv4 visibles par la sonde et sélection directe du sous-réseau.
- [ ] Ajouter la remontée des routes IPv6 et des interfaces (adresse, VLAN, passerelle, métrique).
- [ ] Découvrir les réseaux indirects via SNMP (tables de routage des routeurs) avec validation explicite avant scan.
- [ ] Ajouter un mode de découverte en continu, limité par site/VRF, avec budget et plages interdites.
- [ ] Diffuser les mises à jour par SSE/WebSocket pour remplacer le rafraîchissement périodique.
- [ ] Afficher une topologie dédiée par sonde et différencier « route annoncée » de « réseau effectivement joignable ».

## Manques prioritaires identifiés

- [ ] Couvrir le nouveau parcours Sonde par des tests API et Playwright.
- [ ] Permettre des secrets SNMP locaux à la sonde sans transmettre les identifiants centraux.
- [ ] Ajouter annulation, délai maximal et progression par module aux tâches distantes.
- [ ] Durcir le déploiement de la sonde (paquet signé, auto-update contrôlé, journal de diagnostic).
- [ ] Mesurer la rétention et purger automatiquement observations et historiques volumineux.
