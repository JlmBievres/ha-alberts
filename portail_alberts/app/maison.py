"""Modèle de la maison : lecture des états, règles d'alerte, actions en liste blanche,
séquences d'arrivée et de fermeture."""
import threading, time
from datetime import datetime, timedelta

import ha

DEMO = False                 # positionné par app.py
CACHE = {"etats": {}, "horodatage": 0, "erreur": None}
INDISPO = (None, "unavailable", "unknown")
MARCHE_ARRET = {"switch", "input_boolean", "light", "fan"}
APPUI = {"button", "input_button"}
VERROU = threading.Lock()


# ---------------------------------------------------------------- états
def lire_etats():
    if DEMO:
        import demo
        if not CACHE["etats"]:
            CACHE["etats"] = demo.etats()
        CACHE["horodatage"], CACHE["erreur"] = time.time(), None
        return True
    try:
        CACHE["etats"] = {e["entity_id"]: e for e in ha.rest("GET", "/states")}
        CACHE["horodatage"], CACHE["erreur"] = time.time(), None
        return True
    except Exception as exc:
        CACHE["erreur"] = str(exc)
        print(f"HA injoignable : {exc}", flush=True)
        return False


def etat(eid):
    return CACHE["etats"].get(eid, {}).get("state") if eid else None


def attr(eid, nom):
    return CACHE["etats"].get(eid, {}).get("attributes", {}).get(nom) if eid else None


def num(eid):
    try:
        return float(etat(eid))
    except (TypeError, ValueError):
        return None


def etat_direct(eid):
    """État lu à l'instant (pas le cache), pour vérifier qu'une commande a pris."""
    if DEMO:
        return etat(eid)
    try:
        e = ha.rest("GET", f"/states/{eid}")
        CACHE["etats"][eid] = e
        return e.get("state")
    except Exception:
        return None


def service(domaine, nom, data):
    if DEMO:
        import demo
        demo.service(CACHE["etats"], domaine, nom, data)
        return True
    try:
        ha.rest("POST", f"/services/{domaine}/{nom}", data)
        return True
    except Exception as exc:
        print(f"Service {domaine}.{nom} refusé : {exc}", flush=True)
        return False


def basculer(eid, on, **extra):
    dom = eid.split(".")[0]
    return service(dom, "turn_on" if on else "turn_off", dict({"entity_id": eid}, **extra))


def verifier(eid, attendu, delai=4.0):
    """Attend que l'entité prenne l'état attendu. Faux si elle ne répond pas."""
    fin = time.time() + delai
    while time.time() < fin:
        if etat_direct(eid) == attendu:
            return True
        time.sleep(0.5)
    return etat_direct(eid) == attendu


# ---------------------------------------------------------------- outils
def fmt(x, d=1):
    return None if x is None else f"{x:.{d}f}".replace(".", ",")


def pieces_cfg(CFG):
    return {p["id"]: p for p in CFG["pieces"]}


def lampe_cfg(CFG, pid, lid):
    p = pieces_cfg(CFG).get(pid)
    return p, next((l for l in (p or {}).get("lampes") or [] if l["id"] == lid), None)


def toutes_lampes(CFG):
    for p in CFG["pieces"]:
        for l in p.get("lampes") or []:
            yield p, l


def entites(CFG):
    ids = [CFG.get("prechauffage")] + [CFG["meteo"].get(k) for k in ("entite", "vigilance", "temperature_exterieure", "soleil")]
    for p in CFG["pieces"]:
        ids += [p.get("temperature"), p.get("humidite")]
        c = p.get("convecteur") or {}
        ids += [c.get(k) for k in ("mode", "puissance", "interrupteur", "energie")]
        ids += [(p.get("poele") or {}).get("prise"), (p.get("ventilation") or {}).get("entite")]
        ids += [l["entite"] for l in p.get("lampes") or []]
    ids += [d["entite"] for d in CFG.get("portes") or []]
    for c in CFG.get("commandes") or []:
        ids += [c["entite"], c.get("alimentation")]
    return [i for i in ids if i]


# ---------------------------------------------------------------- minuteries
MINUTERIES = {}   # clé -> {"fin": t, "annule": bool}


def _minuterie(cle, minutes, pendant, fin_action):
    """Lance une minuterie ; `pendant` est rappelée chaque minute (relance), `fin_action` à la fin."""
    if cle in MINUTERIES:
        MINUTERIES[cle]["annule"] = True
    m = {"fin": time.time() + minutes * 60, "annule": False}
    MINUTERIES[cle] = m

    def boucle():
        while time.time() < m["fin"] and not m["annule"]:
            if pendant:
                pendant()
            time.sleep(min(60, max(1, m["fin"] - time.time())))
        if not m["annule"]:
            fin_action()
            MINUTERIES.pop(cle, None)
    threading.Thread(target=boucle, daemon=True).start()


def reste_minuterie(cle):
    m = MINUTERIES.get(cle)
    return max(0, int(m["fin"] - time.time())) if m and not m["annule"] else 0


# ---------------------------------------------------------------- analyse
def analyser(CFG):
    S = CFG["seuils"]
    modes = CFG["modes"]
    alertes, pieces = [], []
    puissance_totale = 0.0
    for p in CFG["pieces"]:
        t, h = num(p.get("temperature")), num(p.get("humidite"))
        d = {"id": p["id"], "nom": p["nom"], "type": p.get("type", "sans_chauffage"),
             "t": fmt(t), "h": None if h is None else f"{h:.0f} %", "t_num": t, "h_num": h,
             "conseils": p.get("conseils") or [], "chip": None, "warn": False}
        # --- chauffage électrique
        c = p.get("convecteur")
        if c:
            mode, w = etat(c.get("mode")), num(c.get("puissance"))
            options = attr(c.get("mode"), "options") or list(modes)
            inter = etat(c.get("interrupteur"))
            diag = "inconnu"
            if c.get("interrupteur") and inter == "off":
                diag = "coupe"
                alertes.append({"niveau": "orange", "piece": p["id"], "titre": f"{p['nom']} : convecteur hors tension",
                                "texte": "Il ne peut pas chauffer tant qu'il n'est pas remis sous tension.",
                                "action": {"type": "remettre_tension", "piece": p["id"], "libelle": "Remettre sous tension"}})
            elif mode in CFG["modes_chauffe"]:
                if w is not None and w >= S["puissance_min_chauffe"]:
                    diag = "chauffe"
                elif t is not None and t < S["temp_chauffe_attendue"]:
                    diag = "panne"
                    alertes.append({"niveau": "orange", "piece": p["id"], "titre": f"{p['nom']} ne chauffe pas",
                                    "texte": f"{fmt(t)} °C en {modes.get(mode, {}).get('libelle', mode)}, {fmt(w or 0, 0)} W consommés. "
                                             "Vérifiez le sélecteur et le thermostat du convecteur, puis le disjoncteur.",
                                    "lien": f"#/piece/{p['id']}", "bouton": "Voir"})
                else:
                    diag = "ok"
            elif mode in (CFG["mode_depart"], "Off", "Eco"):
                diag = "arret"
            if w:
                puissance_totale += w
            d["convecteur"] = {
                "mode": mode, "mode_libelle": modes.get(mode, {}).get("libelle", mode or "?"),
                "aide": modes.get(mode, {}).get("aide", ""), "w": w, "w_txt": f"{fmt(w or 0, 0)} W",
                "diag": diag, "modele": c.get("modele", ""), "dispo": mode not in INDISPO,
                "modes": [{"valeur": k, "libelle": v["libelle"]} for k, v in modes.items() if k in options]}
            libel = {"panne": "Ne chauffe pas", "chauffe": f"Chauffe {fmt(w, 0)} W", "coupe": "Hors tension"}
            d["chip"] = libel.get(diag, d["convecteur"]["mode_libelle"])
            d["warn"] = diag in ("panne", "coupe")
        elif p.get("type") == "poele":
            prise = (p.get("poele") or {}).get("prise")
            st, w = etat(prise), num((p.get("poele") or {}).get("puissance"))
            texte = {"on": "Console allumée", "off": "Prise coupée"}.get(st, "État non relié")
            if st == "on" and w is not None and w >= float((CFG.get("fermeture") or {}).get("poeles_seuil_w", 15)):
                texte = f"En marche, {fmt(w, 0)} W"
            d["poele"] = {"etat": "inconnu" if not prise or st in INDISPO else st, "texte": texte, "w": w}
            d["chip"] = "Poêle"
        elif p.get("type") == "passage":
            d["chip"] = "Détecteur la nuit"
        else:
            d["chip"] = "Sans chauffage"
        # --- seuils
        if t is not None and t < S["temp_gel"]:
            alertes.append({"niveau": "rouge", "piece": p["id"], "titre": f"Risque de gel : {p['nom']}",
                            "texte": f"{fmt(t)} °C. Mettez la pièce en Confort et prévenez le propriétaire."})
        elif t is not None and t < S["temp_froide"] and not d["warn"] and p.get("type") == "convecteur" \
                and (d.get("convecteur") or {}).get("mode") in CFG["modes_chauffe"]:
            alertes.append({"niveau": "jaune", "piece": p["id"], "titre": f"{p['nom']} est froide",
                            "texte": f"{fmt(t)} °C. Comptez 1 à 2 h pour gagner quelques degrés."})
        if h is not None and h > S["humidite_max"]:
            v = p.get("ventilation")
            a = {"niveau": "orange", "piece": p["id"], "titre": f"{p['nom']} : {h:.0f} % d'humidité",
                 "texte": "Lancez la ventilation et laissez la porte ouverte." if v else "Aérez quelques minutes et laissez la porte ouverte."}
            if v and etat(v["entite"]) != "on":
                a["action"] = {"type": "ventilation", "piece": p["id"], "valeur": "on", "libelle": "Ventiler"}
            alertes.append(a)
            d["chip"], d["warn"] = "Trop humide", True
        # --- lampes
        lampes = []
        for l in p.get("lampes") or []:
            st = etat(l["entite"])
            br = attr(l["entite"], "brightness")
            modes_coul = attr(l["entite"], "supported_color_modes") or []
            sans_courant = bool(l.get("alimentation")) and etat(l["alimentation"]) != "on"
            lampes.append({"id": l["id"], "nom": l["nom"], "on": st == "on", "ko": st in INDISPO and not sans_courant,
                           "sans_courant": sans_courant,
                           "variable": l["entite"].startswith("light.") and any(m != "onoff" for m in modes_coul),
                           "luminosite": round((br or 0) * 100 / 255) if br else None,
                           "minuterie_min": l.get("minuterie_min"), "reste": reste_minuterie(f"lampe:{p['id']}:{l['id']}")})
        d["lampes"] = lampes
        on = [l for l in lampes if l["on"]]
        if not lampes:
            d["lumiere"] = {"etat": "none", "texte": "Pas de lumière pilotée"}
        elif all(l["sans_courant"] for l in lampes):
            d["lumiere"] = {"etat": "off", "texte": "Non alimentée"}
        elif not on:
            d["lumiere"] = {"etat": "off", "texte": "Éteinte"}
        else:
            d["lumiere"] = {"etat": "on", "texte": "Allumée" if len(lampes) == 1 else f"{len(on)} sur {len(lampes)}"}
        # --- ventilation
        v = p.get("ventilation")
        if v:
            d["ventilation"] = {"on": etat(v["entite"]) == "on", "ko": etat(v["entite"]) in INDISPO,
                                "maintien_min": v.get("maintien_min", 30), "arret_auto": v.get("arret_auto", ""),
                                "reste": reste_minuterie(f"vmc:{p['id']}")}
        pieces.append(d)

    # --- météo extérieure
    M = CFG["meteo"]
    vig = etat(M.get("vigilance"))
    if vig and vig.lower() not in ("vert", "green", "unknown", "unavailable"):
        alertes.append({"niveau": "jaune", "titre": f"Vigilance météo {vig.lower()}",
                        "texte": "Consultez la météo avant de prendre la route.", "lien": "#/meteo", "bouton": "Météo"})
    ext = num(M.get("temperature_exterieure"))
    if ext is None:
        ext = attr(M.get("entite"), "temperature")

    # --- portes
    portes = [{"nom": d["nom"], "ouverte": etat(d["entite"]) in ("on", "open"), "ko": etat(d["entite"]) in INDISPO}
              for d in CFG.get("portes") or []]

    # --- appareils
    appareils = commandes_voyageur(CFG)

    # --- veille et liste de départ
    convs = [p for p in pieces if p.get("convecteur")]
    tous_depart = bool(convs) and all(p["convecteur"]["mode"] in (CFG["mode_depart"], "Off") for p in convs)
    eau = next((a for a in appareils if a["id"] == "eau_chaude"), None)
    veille = tous_depart and (not eau or eau["etat"] in ("off", "veille"))
    allumees = [p["nom"] for p in pieces if p["lumiere"]["etat"] == "on"]
    en_marche = [p["nom"] for p in convs if p["convecteur"]["mode"] not in (CFG["mode_depart"], "Off")]
    auto = [
        {"id": "radiateurs", "groupe": "radiateur", "t": "Radiateurs tous en hors-gel", "ok": not en_marche,
         "x": ("Encore en marche : " + ", ".join(en_marche)) if en_marche else "Fait.",
         "action": None if not en_marche else {"type": "chauffage_tout", "libelle": "Tout arrêter"}},
        {"id": "lumieres", "groupe": "lumiere", "t": "Lumières éteintes", "ok": not allumees,
         "x": ("Allumées : " + ", ".join(allumees)) if allumees else "Fait.",
         "action": None if not allumees else {"type": "lumieres_maison", "valeur": "off", "libelle": "Tout éteindre"}},
    ]
    if eau:
        auto.insert(1, {"id": "eau", "groupe": "lumiere", "t": "Eau chaude arrêtée", "ok": eau["etat"] != "on",
                        "x": "Elle sera coupée à la fermeture." if eau["etat"] == "on" else "Fait.",
                        "action": None if eau["etat"] != "on" else {"type": "commande", "id": "eau_chaude", "valeur": "off", "libelle": "Arrêter"}})
    if portes:
        ouv = [d["nom"] for d in portes if d["ouverte"]]
        auto.append({"id": "portes", "groupe": "maison", "t": "Portes fermées", "ok": not ouv,
                     "x": ("Ouverte : " + ", ".join(ouv)) if ouv else "Fait.", "action": None})

    niveaux = [a["niveau"] for a in alertes]
    statut = next((n for n in ("rouge", "orange", "jaune") if n in niveaux), "vert")
    ordre = {"rouge": 0, "orange": 1, "jaune": 2}
    pre = etat(CFG.get("prechauffage"))
    return {
        "statut": statut, "veille": veille,
        "alertes": sorted(alertes, key=lambda a: ordre[a["niveau"]]),
        "pieces": pieces, "appareils": appareils, "portes": portes,
        "exterieur": {"t": fmt(ext) if isinstance(ext, (int, float)) else None, "vigilance": vig,
                      "condition": CONDITIONS.get(etat(M.get("entite")), etat(M.get("entite"))), "lieu": M.get("lieu", "")},
        "chauffage": {"puissance": round(puissance_totale), "prechauffage": None if pre in INDISPO else pre == "on"},
        "depart": {"auto": auto, "gestes": CFG.get("depart_gestes") or [], "delai_s": CFG.get("fermeture", {}).get("delai_s", 120),
                   "coupes": [c.get("alimentation_nom", c["nom"]) for c in CFG.get("commandes") or [] if c.get("couper_alimentation") == "differe"]
                             + sorted([c["nom"] for c in CFG.get("commandes") or [] if c.get("depart") == "differe"], key=lambda n: (n.startswith("WiFi"), "Livebox" in n)),
                   "gardes": [c["nom"] for c in CFG.get("commandes") or [] if c.get("depart") == "garder"],
                   "refroidis": [c["nom"] for c in CFG.get("commandes") or [] if c.get("depart") == "refroidissement"]},
        "arrivee": {"etapes": CFG.get("arrivee_etapes") or [], "mise_en_route": etat_mise_en_route(CFG)},
        "fermeture": etat_fermeture(),
    }


CONDITIONS = {"clear-night": "Nuit claire", "cloudy": "Nuageux", "exceptional": "Exceptionnel", "fog": "Brouillard",
              "hail": "Grêle", "lightning": "Orage", "lightning-rainy": "Orage et pluie", "partlycloudy": "Éclaircies",
              "pouring": "Averses", "rainy": "Pluie", "snowy": "Neige", "snowy-rainy": "Pluie et neige",
              "sunny": "Ensoleillé", "windy": "Venteux", "windy-variant": "Venteux et nuageux"}


# ---------------------------------------------------------------- appareils
EN_COURS = {}     # id de commande -> {"message": str, "echec": bool}


def commandes_voyageur(CFG):
    out = []
    for c in CFG.get("commandes") or []:
        if not c.get("voyageur"):
            continue
        st, dom, alim = etat(c["entite"]), c["entite"].split(".")[0], c.get("alimentation")
        cours = EN_COURS.get(c["id"])
        b_on = {"valeur": "on", "libelle": c.get("bouton_on", "Allumer")}
        b_off = {"valeur": "off", "libelle": c.get("bouton_off", "Arrêter")} if c.get("peut_eteindre") else None
        if cours and not cours.get("echec"):
            e, lib, btn = "demarrage", cours["message"], None
        elif st in INDISPO and dom not in APPUI:
            if alim and etat(alim) != "on":
                e, lib, btn = "veille", c.get("etat_veille", c.get("etat_off", "Arrêté")), b_on
            else:
                e, lib, btn = "ko", (cours or {}).get("message", "Ne répond pas"), (b_on if alim else None)
        else:
            on = st == "on"
            e = "on" if on else "off"
            lib = c.get("etat_on" if on else "etat_off", "En marche" if on else "Arrêté")
            btn = b_off if on else b_on
        out.append({"id": c["id"], "nom": c["nom"], "icone": c.get("icone", ""), "explication": c.get("explication", ""),
                    "etat": e, "texte": lib, "bouton": btn, "confirmation": c.get("confirmation", "")})
    return out


def _allumer_commande(c):
    """Allume une commande ; si elle a une alimentation, l'allume d'abord et attend l'appareil."""
    cid, eid, alim = c["id"], c["entite"], c.get("alimentation")
    if not alim or (etat_direct(alim) == "on" and etat_direct(eid) not in INDISPO):
        ok = basculer(eid, True) and verifier(eid, "on")
        if ok:
            EN_COURS.pop(cid, None)
        else:
            EN_COURS[cid] = {"message": f"{c['nom']} n'a pas répondu.", "echec": True}
        return
    nom = c.get("alimentation_nom", "appareil")
    try:
        EN_COURS[cid] = {"message": f"Allumage : {nom}…"}
        basculer(alim, True)
        if DEMO:
            time.sleep(6)
            CACHE["etats"].setdefault(eid, {"attributes": {}})["state"] = "off"
        limite = time.time() + int(c.get("delai_max", 240))
        EN_COURS[cid]["message"] = f"Démarrage : {nom}, 1 à 3 minutes…"
        while etat_direct(eid) in INDISPO:
            if time.time() > limite:
                EN_COURS[cid] = {"message": f"Pas de réponse : {nom}. Réessayez ou consultez le guide.", "echec": True}
                return
            time.sleep(5)
        basculer(eid, True)
        EN_COURS.pop(cid, None)
    except Exception as exc:
        EN_COURS[cid] = {"message": "La mise en route a échoué.", "echec": True}
        print(f"Mise en route {cid} : {exc}", flush=True)


def allumer_commande_async(c):
    if c["id"] in EN_COURS and not EN_COURS[c["id"]].get("echec"):
        return
    EN_COURS[c["id"]] = {"message": "Mise en route…"}
    threading.Thread(target=_allumer_commande, args=(c,), daemon=True).start()


# ---------------------------------------------------------------- arrivée
def etat_mise_en_route(CFG):
    out = []
    for c in CFG.get("commandes") or []:
        if not c.get("arrivee"):
            continue
        st, cours = etat(c["entite"]), EN_COURS.get(c["id"])
        if cours and not cours.get("echec"):
            e, x = "encours", cours["message"]
        elif cours and cours.get("echec"):
            e, x = "echec", cours["message"]
        elif st == "on":
            e, x = "ok", c.get("etat_on", "Allumé")
        elif st in INDISPO and not c.get("alimentation"):
            e, x = "echec", "Prise introuvable ou hors ligne"
        else:
            e, x = "attente", "Sera allumé par la mise en route"
        out.append({"id": c["id"], "t": c["nom"], "etat": e, "x": x})
    return out


def mise_en_route(CFG):
    FERMETURE["phase"] = None
    for c in CFG.get("commandes") or []:
        if c.get("arrivee") and etat(c["entite"]) != "on":
            allumer_commande_async(c)


# ---------------------------------------------------------------- fermeture
FERMETURE = {"fin": 0, "annule": False, "phase": None, "eau_etait_on": False}


def etat_fermeture():
    if FERMETURE["phase"] == "compte":
        return {"phase": "compte", "reste": max(0, int(FERMETURE["fin"] - time.time()))}
    return {"phase": FERMETURE["phase"]}


def demarrer_fermeture(CFG):
    with VERROU:
        if FERMETURE["phase"] == "compte":
            return
        FERMETURE.update(phase="compte", annule=False, fin=time.time() + int(CFG.get("fermeture", {}).get("delai_s", 120)))
    print("Fermeture de la maison : lancée", flush=True)
    # 1. Tout de suite : radiateurs, lumières, ventilation, appareils « immédiat »
    for p in CFG["pieces"]:
        c = p.get("convecteur")
        if c and c.get("mode"):
            service("select", "select_option", {"entity_id": c["mode"], "option": CFG["mode_depart"]})
        for l in p.get("lampes") or []:
            if etat(l["entite"]) == "on":
                basculer(l["entite"], False)
        if p.get("ventilation") and etat(p["ventilation"]["entite"]) == "on":
            basculer(p["ventilation"]["entite"], False)
    for c in CFG.get("commandes") or []:
        if c.get("depart") == "immediat" and etat(c["entite"]) == "on":
            if c["id"] == "eau_chaude":
                FERMETURE["eau_etait_on"] = True
            basculer(c["entite"], False)

    def suite():
        while time.time() < FERMETURE["fin"]:
            if FERMETURE["annule"]:
                return
            time.sleep(1)
        FERMETURE["phase"] = "coupure"
        # 2. Après le compte à rebours : alimentations, puis appareils « différé » (WiFi en dernier)
        for c in CFG.get("commandes") or []:
            if c.get("couper_alimentation") == "differe" and c.get("alimentation"):
                basculer(c["alimentation"], False)
        differes = [c for c in CFG.get("commandes") or [] if c.get("depart") == "differe"]
        differes.sort(key=lambda c: (c["id"].startswith("wifi"), c["id"].startswith("wifi_box")))
        for c in differes:
            time.sleep(2)
            basculer(c["entite"], False)
        FERMETURE["phase"] = "fermee"
        print("Fermeture de la maison : terminée", flush=True)
        for c in CFG.get("commandes") or []:
            if c.get("depart") == "refroidissement":
                threading.Thread(target=_couper_poele, args=(CFG, c), daemon=True).start()
    threading.Thread(target=suite, daemon=True).start()


def _couper_poele(CFG, c):
    """Coupe la prise d'un poêle seulement quand il ne ventile plus.
    Avec mesure de puissance : 10 minutes de suite sous le seuil (au plus tard delai_max).
    Sans mesure : attente fixe delai_min. Annulé si la maison est remise en route."""
    F = CFG.get("fermeture") or {}
    seuil, sous, debut = float(F.get("poeles_seuil_w", 15)), 0, time.time()
    limite = debut + 60 * int(F.get("poeles_delai_max_min", 180))
    attente = debut + 60 * int(F.get("poeles_delai_min", 60))
    capteur = c.get("puissance")
    print(f"{c['nom']} : coupure après refroidissement ({'mesure ' + capteur if capteur else 'attente fixe'})", flush=True)
    while True:
        time.sleep(5 if DEMO else 60)
        if FERMETURE["phase"] != "fermee":
            print(f"{c['nom']} : coupure abandonnée (maison remise en route)", flush=True)
            return
        if capteur:
            try:
                w = float(etat_direct(capteur))
            except (TypeError, ValueError):
                w = None
            sous = sous + 1 if w is not None and w < seuil else 0
            if sous >= (1 if DEMO else 10) or time.time() > limite:
                break
        elif time.time() > attente or DEMO:
            break
    basculer(c["entite"], False)
    print(f"{c['nom']} : prise coupée", flush=True)


def annuler_fermeture(CFG):
    if FERMETURE["phase"] != "compte":
        return False
    FERMETURE.update(annule=True, phase=None)
    if FERMETURE.get("eau_etait_on"):
        c = next((c for c in CFG.get("commandes") or [] if c["id"] == "eau_chaude"), None)
        if c:
            basculer(c["entite"], True)
    print("Fermeture de la maison : annulée", flush=True)
    return True


# ---------------------------------------------------------------- actions
def refuse(msg="Action non autorisée"):
    return 403, {"ok": False, "message": msg}


def resultat(ok, msg_ko="Home Assistant n'a pas accepté la commande."):
    return 200, ({"ok": True} if ok else {"ok": False, "message": msg_ko})


def action(CFG, q):
    """Toutes les commandes passent ici. On n'accepte que des identifiants décrits dans
    entities.yaml : jamais un identifiant d'entité venu du navigateur."""
    T = q.get("type")
    P = pieces_cfg(CFG)
    p = P.get(q.get("piece")) if q.get("piece") else None

    if T == "mode":
        c = (p or {}).get("convecteur")
        if not c or q.get("valeur") not in CFG["modes"]:
            return refuse()
        ok = service("select", "select_option", {"entity_id": c["mode"], "option": q["valeur"]})
        return resultat(ok and verifier(c["mode"], q["valeur"]), "Le convecteur n'a pas répondu. Vérifiez qu'il est sous tension.")

    if T == "remettre_tension":
        c = (p or {}).get("convecteur")
        if not c or not c.get("interrupteur"):
            return refuse()
        return resultat(basculer(c["interrupteur"], True) and verifier(c["interrupteur"], "on"))

    if T == "chauffage_tout":
        ok = True
        for pc in CFG["pieces"]:
            c = pc.get("convecteur")
            if c and c.get("mode"):
                ok &= service("select", "select_option", {"entity_id": c["mode"], "option": CFG["mode_depart"]})
        return resultat(ok)

    if T == "lampe":
        p, l = lampe_cfg(CFG, q.get("piece"), q.get("lampe"))
        if not l:
            return refuse()
        eid, val = l["entite"], q.get("valeur")
        if val == "on":
            extra = {}
            if q.get("luminosite") is not None and eid.startswith("light."):
                extra["brightness_pct"] = max(1, min(100, int(q["luminosite"])))
            ok = basculer(eid, True, **extra)
            if q.get("minutes") and l.get("minuterie_min"):
                _minuterie(f"lampe:{p['id']}:{l['id']}", int(l["minuterie_min"]), None, lambda: basculer(eid, False))
        elif val == "off":
            ok = basculer(eid, False)
            m = MINUTERIES.get(f"lampe:{p['id']}:{l['id']}")
            if m:
                m["annule"] = True
        else:
            return refuse()
        return resultat(ok and verifier(eid, "on" if val == "on" else "off"),
                        f"{l['nom']} n'a pas répondu. La lampe est peut-être coupée à l'interrupteur mural : remettez-le en position allumée.")

    if T == "lumieres_piece":
        if not p or q.get("valeur") not in ("on", "off"):
            return refuse()
        ok = True
        for l in p.get("lampes") or []:
            ok &= basculer(l["entite"], q["valeur"] == "on")
        return resultat(ok)

    if T == "lumieres_maison":
        for _, l in toutes_lampes(CFG):
            if etat(l["entite"]) == "on":
                basculer(l["entite"], False)
        return resultat(True)

    if T == "ventilation":
        v = (p or {}).get("ventilation")
        if not v:
            return refuse()
        eid, val, cle = v["entite"], q.get("valeur"), f"vmc:{p['id']}"
        if val == "on":
            return resultat(basculer(eid, True) and verifier(eid, "on"), "La ventilation n'a pas répondu.")
        if val == "off":
            if cle in MINUTERIES:
                MINUTERIES[cle]["annule"] = True
            return resultat(basculer(eid, False))
        if val == "maintien":
            basculer(eid, True)
            # relance chaque minute : l'automatisation d'arrêt 5 min après la lumière ne la coupe pas
            _minuterie(cle, int(v.get("maintien_min", 30)), lambda: etat(eid) != "on" and basculer(eid, True),
                       lambda: basculer(eid, False))
            return resultat(True)
        return refuse()

    if T == "commande":
        c = next((c for c in CFG.get("commandes") or [] if c.get("id") == q.get("id")), None)
        if not c or not c.get("voyageur"):
            return refuse()
        eid, dom, val = c["entite"], c["entite"].split(".")[0], q.get("valeur")
        if dom in APPUI and val == "on":
            return resultat(service(dom, "press", {"entity_id": eid}))
        if dom in MARCHE_ARRET and val == "on":
            if c.get("alimentation") and (etat_direct(eid) in INDISPO or etat(c["alimentation"]) != "on"):
                allumer_commande_async(c)
                return 200, {"ok": True, "message": "Mise en route lancée"}
            return resultat(basculer(eid, True) and verifier(eid, "on"), f"{c['nom']} n'a pas répondu.")
        if dom in MARCHE_ARRET and val == "off" and c.get("peut_eteindre"):
            return resultat(basculer(eid, False) and verifier(eid, "off"), f"{c['nom']} n'a pas répondu.")
        return refuse()

    if T == "mise_en_route":
        mise_en_route(CFG)
        return 200, {"ok": True}

    if T == "fermeture":
        if q.get("valeur") == "annuler":
            return 200, {"ok": annuler_fermeture(CFG)}
        if q.get("valeur") == "demarrer" and q.get("confirme") is True:
            demarrer_fermeture(CFG)
            return 200, {"ok": True}
        return refuse("Confirmation manquante")

    return 400, {"ok": False, "message": "Action inconnue"}


# ---------------------------------------------------------------- consommation et météo
def _tz():
    try:
        from zoneinfo import ZoneInfo
        import os
        return ZoneInfo(os.environ.get("TZ") or "Europe/Paris")
    except Exception:
        return None


def maintenant():
    return datetime.now(_tz()) if _tz() else datetime.now().astimezone()


def _heure_creuse(h, plages):
    for pl in plages:
        a, b = pl.split("-")
        ha_, hb = int(a[:2]), int(b[:2])
        if (ha_ <= hb and ha_ <= h < hb) or (ha_ > hb and (h >= ha_ or h < hb)):
            return True
    return False


def stats(ids, debut, fin, periode, types):
    if DEMO:
        import demo
        return demo.stats(ids, debut, fin, periode, types)
    r = ha.ws_requetes([{"type": "recorder/statistics_during_period", "start_time": debut.isoformat(),
                         "end_time": fin.isoformat(), "statistic_ids": ids, "period": periode, "types": types}])[0]
    if isinstance(r, dict) and "erreur" in r:
        raise RuntimeError(str(r["erreur"]))
    return r


def _instant(x):
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, maintenant().tzinfo)
    return datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(maintenant().tzinfo)


def consommation(CFG):
    """kWh et € du jour, de la semaine (7 j) et du mois en cours, avec part heures creuses."""
    T = CFG.get("tarifs") or {}
    hc, hp, plages = T.get("heures_creuses", 0), T.get("heures_pleines", 0), T.get("plages_creuses", [])
    convs = [(p, p["convecteur"]["energie"]) for p in CFG["pieces"] if (p.get("convecteur") or {}).get("energie")]
    now = maintenant()
    j0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    debut = min(j0 - timedelta(days=6), j0.replace(day=1))
    data = stats([e for _, e in convs], debut, now, "hour", ["change"])
    tot = {k: {"kwh": 0.0, "nuit": 0.0, "eur": 0.0} for k in ("jour", "semaine", "mois")}
    par_piece = {}
    for p, e in convs:
        for row in data.get(e, []):
            v = row.get("change") or 0
            t = _instant(row["start"])
            creuse = _heure_creuse(t.hour, plages)
            eur = v * (hc if creuse else hp)
            for k, d0 in (("jour", j0), ("semaine", j0 - timedelta(days=6)), ("mois", j0.replace(day=1))):
                if t >= d0:
                    tot[k]["kwh"] += v; tot[k]["eur"] += eur
                    tot[k]["nuit"] += v if creuse else 0
            if t >= j0:
                par_piece[p["id"]] = par_piece.get(p["id"], 0) + v
    out = {}
    for k, d in tot.items():
        out[k] = {"kwh": fmt(d["kwh"]), "eur": fmt(d["eur"], 2),
                  "nuit_pct": round(100 * d["nuit"] / d["kwh"]) if d["kwh"] else 0}
    out["pieces"] = {k: fmt(v) for k, v in par_piece.items()}
    out["tarifs"] = {"hc": fmt(hc, 2), "hp": fmt(hp, 2), "plages": plages}
    return out


def convecteur(CFG, pid, mois=None):
    p = pieces_cfg(CFG).get(pid)
    c = (p or {}).get("convecteur")
    if not c:
        return None
    now = maintenant()
    # Puissance sur 24 h (moyennes 5 min)
    courbe = []
    if c.get("puissance"):
        d = stats([c["puissance"]], now - timedelta(hours=24), now, "5minute", ["mean"])
        courbe = [round(r.get("mean") or 0) for r in d.get(c["puissance"], [])]
    # Calendrier du mois
    if mois:
        a, m = (int(x) for x in mois.split("-"))
        m0 = now.replace(year=a, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        m0 = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    m1 = (m0 + timedelta(days=32)).replace(day=1)
    jours = {}
    if c.get("energie"):
        d = stats([c["energie"]], m0, min(m1, now), "day", ["change"])
        for r in d.get(c["energie"], []):
            jours[_instant(r["start"]).day] = round(r.get("change") or 0, 1)
    nb = (m1 - timedelta(days=1)).day
    vals = [jours.get(i) for i in range(1, nb + 1)]
    connus = [v for v in vals if v is not None]
    MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return {"id": pid, "nom": p["nom"], "modele": c.get("modele", ""), "courbe": courbe,
            "mois": {"cle": f"{m0.year}-{m0.month:02d}", "titre": f"{MOIS[m0.month - 1].capitalize()} {m0.year}",
                     "premier_jour": m0.weekday(), "jours": vals, "total": fmt(sum(connus)) if connus else "0",
                     "max": max(connus) if connus else 0,
                     "precedent": (m0 - timedelta(days=1)).strftime("%Y-%m"),
                     "suivant": m1.strftime("%Y-%m") if m1 <= now else None}}


JOURS = ["Lun.", "Mar.", "Mer.", "Jeu.", "Ven.", "Sam.", "Dim."]


def meteo(CFG):
    M = CFG["meteo"]
    eid = M.get("entite")
    a = (CACHE["etats"].get(eid) or {}).get("attributes", {})
    if DEMO:
        import demo
        prev = demo.previsions()
    else:
        r = ha.ws_requetes([
            {"type": "call_service", "domain": "weather", "service": "get_forecasts", "service_data": {"type": "hourly"},
             "target": {"entity_id": eid}, "return_response": True},
            {"type": "call_service", "domain": "weather", "service": "get_forecasts", "service_data": {"type": "daily"},
             "target": {"entity_id": eid}, "return_response": True}])
        prev = {k: ((x or {}).get("response") or {}).get(eid, {}).get("forecast", []) for k, x in zip(("hourly", "daily"), r)}
    heures = [{"h": f"{_instant(f['datetime']).hour} h", "cond": f.get("condition"), "t": fmt(f.get("temperature")),
               "mm": fmt(f.get("precipitation") or 0)} for f in prev.get("hourly", [])[:6]]
    jours = [{"j": JOURS[_instant(f["datetime"]).weekday()] + f" {_instant(f['datetime']).day}", "cond": f.get("condition"),
              "max": fmt(f.get("temperature")), "min": fmt(f.get("templow")), "mm": fmt(f.get("precipitation") or 0)}
             for f in prev.get("daily", [])[:5]]
    s = (CACHE["etats"].get(M.get("soleil")) or {}).get("attributes", {})
    hm = lambda k: _instant(s[k]).strftime("%H:%M") if s.get(k) else None
    return {"lieu": M.get("lieu", ""), "cond": etat(eid), "cond_txt": CONDITIONS.get(etat(eid), etat(eid)),
            "t": fmt(a.get("temperature")), "humidite": a.get("humidity"), "pression": fmt(a.get("pressure")),
            "vent": fmt(a.get("wind_speed")), "vent_dir": a.get("wind_bearing"), "nuages": a.get("cloud_coverage"),
            "vigilance": etat(M.get("vigilance")), "heures": heures, "jours": jours,
            "soleil": {"aube": hm("next_dawn"), "lever": hm("next_rising"), "midi": hm("next_noon"),
                       "coucher": hm("next_setting"), "crepuscule": hm("next_dusk")}}
