# Feuille de route

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
