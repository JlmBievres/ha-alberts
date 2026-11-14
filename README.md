# Applications Home Assistant - Les Alberts

## Installer (une seule fois)
HA > Paramètres > Applications > Installer une application > ⋮ > Dépôts
> ajouter https://github.com/JlmBievres/ha-alberts > Portail Les Alberts > Installer > Démarrer.
Portail : http://<ip-ha>:8099   Diagnostic : http://<ip-ha>:8099/sante

## Faire évoluer
1. Modifier le code dans portail_alberts/
2. Incrémenter `version` dans portail_alberts/config.yaml ET VERSION dans app/app.py
3. git commit + push
4. HA : Applications > Portail Les Alberts > Mettre à jour (ou ⋮ > Vérifier les mises à jour)

## Régler les entités sans toucher au code
Copier portail_alberts/app/entities.yaml dans /addon_configs/<id>_portail_alberts/entities.yaml
(onglet File editor ou Samba). Relu à chaque requête, pas de redémarrage.
Vérifier ensuite /sante : la liste `entites_absentes` doit être vide.

## Tester sans HA (PI500)
    cd portail_alberts/app && pip install pyyaml --break-system-packages && DEMO=1 python3 app.py
