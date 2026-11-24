# Applications Home Assistant - Les Alberts

## Portail Les Alberts (0.4)
Portail voyageurs pour tablette murale et smartphone, sur le réseau local :
pièces à jour (température, humidité, chauffage, lumières, portes), scènes Hue,
lampe par lampe, chauffage de toute la maison (menu Fil pilote), picto (i) vers le guide dans chaque section des pièces,
météo, guide, état des prises en lecture seule. Les entités suivent
documentation/reference-portail-entites.md (projet Claude).

- Portail : `http://<ip-ha>:8099`
- Diagnostic : `http://<ip-ha>:8099/sante`

### Installer (une seule fois)
HA > Paramètres > Applications > Boutique > ⋮ > Dépôts > ajouter
`https://github.com/JlmBievres/ha-alberts` > Portail Les Alberts > Installer > Démarrer.

### Mettre à jour
1. Modifier le code dans `portail_alberts/`, incrémenter `version` dans
   `portail_alberts/config.yaml` ET `VERSION` dans `app/app.py`.
2. `git commit` + `git push`.
3. HA : Terminal `ha store reload`, puis Applications > Portail Les Alberts > Mettre à jour.

### Décrire la maison sans toucher au code
Copier `portail_alberts/app/entities.yaml` dans
`/addon_configs/<id>_portail_alberts/entities.yaml`. Relu automatiquement.
Vérifier `/sante` : `entites_absentes` doit être vide.
Le portail n'agit QUE sur ce qui est décrit dans ce fichier (liste blanche).
Ne jamais y décrire la prise de la box, des Pi ou du coordinateur Zigbee.

### Guide de la maison (dépôt privé)
Le guide n'est PAS dans ce dépôt public. Il vit dans un dépôt GitHub privé
(ex. `ha-alberts-guide`, fichier `guide.yaml` + dossier `photos/`).
1. Sur le PI500 : `ssh-keygen -t ed25519 -N "" -f guide_deploy_key`
2. GitHub > dépôt privé > Settings > Deploy keys > Add : coller `guide_deploy_key.pub`,
   **sans** cocher « Allow write access ».
3. Copier `guide_deploy_key` (la clé privée) dans `/addon_configs/<id>_portail_alberts/`.
4. Options de l'application : `guide_depot: git@github.com:JlmBievres/ha-alberts-guide.git`.
5. Redémarrer l'application : le guide est récupéré, puis chaque nuit à `guide_heure`.
   Pour forcer une mise à jour du guide : redémarrer l'application (admins HA seulement).

Informations sensibles (téléphones, WiFi...) : uniquement dans
`/addon_configs/<id>_portail_alberts/secrets.yaml`, jamais dans un dépôt.
Le guide contient des repères `{telephone_proprietaire}` remplacés à l'affichage.

### Tester sans Home Assistant (PI500)
    cd portail_alberts/app && pip install pyyaml --break-system-packages && DEMO=1 python3 app.py
puis http://localhost:8099
