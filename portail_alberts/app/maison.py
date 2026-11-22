"""Modèle de la maison (version simple) : lecture des états, actions en liste blanche
sur les lumières, le chauffage et la ventilation. Les prises sont en lecture seule."""
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
        ids += [c.get(k) for k in ("mode", "puissance", "interrupteur")]
        ids += [(p.get("poele") or {}).get("prise"), (p.get("ventilation") or {}).get("entite")]
        ids += [l["entite"] for l in p.get("lampes") or []]
    ids += [d["entite"] for d in CFG.get("portes") or []]
    for g in CFG.get("prises") or []:
        ids += [p["entite"] for p in g["prises"]] + [p.get("puissance") for p in g["prises"]]
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
CONDITIONS = {"clear-night": "Nuit claire", "cloudy": "Nuageux", "exceptional": "Exceptionnel", "fog": "Brouillard",
              "hail": "Grêle", "lightning": "Orage", "lightning-rainy": "Orage et pluie", "partlycloudy": "Éclaircies",
              "pouring": "Averses", "rainy": "Pluie", "snowy": "Neige", "snowy-rainy": "Pluie et neige",
              "sunny": "Ensoleillé", "windy": "Venteux", "windy-variant": "Venteux et nuageux"}


def _lampes(p):
    out = []
    for l in p.get("lampes") or []:
        st = etat(l["entite"])
        br = attr(l["entite"], "brightness")
        modes = attr(l["entite"], "supported_color_modes") or []
        sans_courant = bool(l.get("alimentation")) and etat(l["alimentation"]) != "on"
        out.append({"id": l["id"], "nom": l["nom"], "on": st == "on", "sans_courant": sans_courant,
                    "ko": st in INDISPO and not sans_courant,
                    "variable": l["entite"].startswith("light.") and any(x != "onoff" for x in modes),
                    "luminosite": round(br * 100 / 255) if br else None,
                    "minuterie_min": l.get("minuterie_min"), "reste": reste_minuterie(f"lampe:{p['id']}:{l['id']}")})
    return out


def analyser(CFG):
    S, modes = CFG["seuils"], CFG["modes"]
    pieces = []
    for p in CFG["pieces"]:
        t, h = num(p.get("temperature")), num(p.get("humidite"))
        d = {"id": p["id"], "nom": p["nom"], "type": p.get("type", "sans_chauffage"),
             "t": fmt(t), "h": None if h is None else f"{h:.0f} %", "humide": h is not None and h > S["humidite_max"],
             "conseils": p.get("conseils") or []}
        c = p.get("convecteur")
        if c:
            mode, w = etat(c.get("mode")), num(c.get("puissance"))
            options = attr(c.get("mode"), "options") or list(modes)
            panne = mode in CFG["modes_chauffe"] and (w or 0) < S["puissance_min_chauffe"] and t is not None and t < S["temp_chauffe_attendue"]
            d["chauffage"] = {"type": "radiateur", "mode": mode, "dispo": mode not in INDISPO,
                              "libelle": modes.get(mode, {}).get("libelle", "Autre réglage" if mode not in INDISPO else "Ne répond pas"),
                              "panne": panne,
                              "modes": [{"valeur": k, "libelle": v["libelle"], "sous": v.get("sous", "")} for k, v in modes.items() if k in options]}
        elif p.get("type") == "poele":
            po = p.get("poele") or {}
            st, w = etat(po.get("prise")), num(po.get("puissance"))
            if st == "on" and w is not None and w >= S["puissance_min_chauffe"]:
                txt, en = "En marche", "on"
            elif st == "on":
                txt, en = "Console allumée", "veille"
            elif st == "off":
                txt, en = "Prise coupée", "off"
            else:
                txt, en = "État inconnu", "inconnu"
            d["chauffage"] = {"type": "poele", "etat": en, "libelle": txt}
        lampes = _lampes(p)
        d["lampes"] = lampes
        on = [l for l in lampes if l["on"]]
        lum = [l["luminosite"] for l in on if l["luminosite"]]
        d["lumiere"] = {"etat": "none" if not lampes else ("on" if on else "off"),
                        "nb_on": len(on), "nb": len(lampes),
                        "luminosite": round(sum(lum) / len(lum)) if lum else None,
                        "variable": any(l["variable"] for l in lampes),
                        "texte": "Pas de lumière pilotée" if not lampes else ("Éteinte" if not on else
                                 ("Allumée" if len(lampes) == 1 else f"{len(on)} sur {len(lampes)}"))}
        v = p.get("ventilation")
        if v:
            d["ventilation"] = {"on": etat(v["entite"]) == "on", "ko": etat(v["entite"]) in INDISPO,
                                "maintien_min": v.get("maintien_min", 30), "arret_auto": v.get("arret_auto", ""),
                                "reste": reste_minuterie(f"vmc:{p['id']}")}
        pieces.append(d)
    M = CFG["meteo"]
    ext = num(M.get("temperature_exterieure"))
    if ext is None:
        ext = attr(M.get("entite"), "temperature")
    pre = etat(CFG.get("prechauffage"))
    return {"pieces": pieces, "ambiances": CFG.get("ambiances") or [],
            "exterieur": {"t": fmt(ext) if isinstance(ext, (int, float)) else None,
                          "condition": CONDITIONS.get(etat(M.get("entite")), etat(M.get("entite"))), "lieu": M.get("lieu", "")},
            "prechauffage": None if pre in INDISPO else pre == "on"}


def prises(CFG):
    """État des prises, en lecture seule."""
    S = CFG["seuils"]
    groupes, n = [], {"on": 0, "off": 0, "ko": 0}
    for g in CFG.get("prises") or []:
        lignes = []
        for p in g["prises"]:
            st, w = etat(p["entite"]), num(p.get("puissance"))
            if st in INDISPO:
                e, txt = "ko", "Ne répond pas"
            elif st == "on":
                e = "on"
                txt = "Allumée" if w is None else (f"En marche, {fmt(w, 0)} W" if w >= S["puissance_min_chauffe"] else f"En veille, {fmt(w, 0)} W")
            else:
                e, txt = "off", "Coupée"
            n[e] += 1
            lignes.append({"nom": p["nom"], "etat": e, "texte": txt})
        groupes.append({"groupe": g["groupe"], "prises": lignes})
    return {"groupes": groupes, "compte": n}


# ---------------------------------------------------------------- actions
def refuse(msg="Action non autorisée"):
    return 403, {"ok": False, "message": msg}


def resultat(ok, msg_ko="Home Assistant n'a pas accepté la commande."):
    return 200, ({"ok": True} if ok else {"ok": False, "message": msg_ko})


def _allumer(l, pct=None):
    eid = l["entite"]
    if pct is not None and eid.startswith("light."):
        return basculer(eid, True, brightness_pct=max(1, min(100, int(pct))))
    return basculer(eid, True)


def action(CFG, q):
    """Toutes les commandes passent ici. On n'accepte que des identifiants décrits dans
    entities.yaml : jamais un identifiant d'entité venu du navigateur. Les prises ne sont
    jamais commandables depuis le portail."""
    T = q.get("type")
    P = pieces_cfg(CFG)
    p = P.get(q.get("piece")) if q.get("piece") else None

    if T == "mode":
        c = (p or {}).get("convecteur")
        if not c or q.get("valeur") not in CFG["modes"]:
            return refuse()
        ok = service("select", "select_option", {"entity_id": c["mode"], "option": q["valeur"]})
        return resultat(ok and verifier(c["mode"], q["valeur"]), "Le radiateur n'a pas répondu. Vérifiez qu'il est sous tension.")

    if T == "lampe":
        p, l = lampe_cfg(CFG, q.get("piece"), q.get("lampe"))
        if not l:
            return refuse()
        val = q.get("valeur")
        if val == "on":
            ok = _allumer(l, q.get("luminosite"))
            if q.get("minutes") and l.get("minuterie_min"):
                _minuterie(f"lampe:{p['id']}:{l['id']}", int(l["minuterie_min"]), None, lambda: basculer(l["entite"], False))
        elif val == "off":
            ok = basculer(l["entite"], False)
            m = MINUTERIES.get(f"lampe:{p['id']}:{l['id']}")
            if m:
                m["annule"] = True
        else:
            return refuse()
        return resultat(ok and verifier(l["entite"], "on" if val == "on" else "off"),
                        f"{l['nom']} n'a pas répondu. La lampe est peut-être coupée à l'interrupteur mural : remettez-le en position allumée.")

    if T == "piece_lumiere":
        if not p or not p.get("lampes"):
            return refuse()
        val, ok = q.get("valeur"), True
        if val == "off":
            for l in p["lampes"]:
                ok &= basculer(l["entite"], False)
        elif val == "on":
            for l in p["lampes"]:
                ok &= _allumer(l)
        elif val == "luminosite" and isinstance(q.get("pct"), (int, float)):
            for l in p["lampes"]:
                ok &= _allumer(l, q["pct"])
        elif val == "ambiance":
            a = next((a for a in CFG.get("ambiances") or [] if a["id"] == q.get("ambiance")), None)
            if not a:
                return refuse()
            for l in p["lampes"]:
                ok &= _allumer(l, a["pct"])
        else:
            return refuse()
        return resultat(ok)

    if T == "maison_lumiere":
        val = q.get("valeur")
        if val not in ("off", "veilleuse"):
            return refuse()
        pct = next((a["pct"] for a in CFG.get("ambiances") or [] if a["id"] == "veilleuse"), 15)
        for _, l in toutes_lampes(CFG):
            if etat(l["entite"]) == "on":
                basculer(l["entite"], False) if val == "off" else _allumer(l, pct)
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
            _minuterie(cle, int(v.get("maintien_min", 30)), lambda: etat(eid) != "on" and basculer(eid, True),
                       lambda: basculer(eid, False))
            return resultat(True)
        return refuse()

    return 400, {"ok": False, "message": "Action inconnue"}


# ---------------------------------------------------------------- météo
def _tz():
    try:
        from zoneinfo import ZoneInfo
        import os
        return ZoneInfo(os.environ.get("TZ") or "Europe/Paris")
    except Exception:
        return None


def maintenant():
    return datetime.now(_tz()) if _tz() else datetime.now().astimezone()


def _instant(x):
    if isinstance(x, (int, float)):
        return datetime.fromtimestamp(x / 1000 if x > 1e11 else x, maintenant().tzinfo)
    return datetime.fromisoformat(str(x).replace("Z", "+00:00")).astimezone(maintenant().tzinfo)


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
