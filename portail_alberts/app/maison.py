"""Modèle de la maison (version simple) : lecture des états, actions en liste blanche
sur les lumières, le chauffage et la ventilation. Les prises sont en lecture seule."""
import threading, time
from datetime import datetime, timedelta

import ha

DEMO = False                 # positionné par app.py
CACHE = {"etats": {}, "horodatage": 0, "erreur": None, "direct": False}
INDISPO = (None, "unavailable", "unknown")
MARCHE_ARRET = {"switch", "input_boolean", "light", "fan"}
APPUI = {"button", "input_button"}
VERROU = threading.Lock()


# ---------------------------------------------------------------- états
# Les états arrivent en direct par une connexion WebSocket permanente avec Home Assistant :
# plus besoin de relire toutes les entités à chaque affichage (c'était la cause de la lenteur).
CHANGEMENT = threading.Condition()


def _abonnement():
    while True:
        ws = None
        try:
            ws = ha.WebSocket(ha.WS_URL)
            if ws.recevoir().get("type") != "auth_required":
                raise ConnectionError("réponse inattendue")
            ws.envoyer({"type": "auth", "access_token": ha.TOKEN})
            if ws.recevoir().get("type") != "auth_ok":
                raise PermissionError("jeton refusé")
            ws.envoyer({"id": 1, "type": "get_states"})
            ws.envoyer({"id": 2, "type": "subscribe_events", "event_type": "state_changed"})
            ws.s.settimeout(None)

            def ping():
                n = 100
                while CACHE["direct"] is not None:
                    time.sleep(30)
                    n += 1
                    try:
                        ws.envoyer({"id": n, "type": "ping"})
                    except Exception:
                        ws.fermer()
                        return
            threading.Thread(target=ping, daemon=True).start()
            while True:
                msg = ws.recevoir()
                if msg.get("id") == 1 and msg.get("type") == "result":
                    CACHE["etats"] = {e["entity_id"]: e for e in msg.get("result") or []}
                    CACHE["horodatage"], CACHE["erreur"], CACHE["direct"] = time.time(), None, True
                    print(f"Connecté en direct à Home Assistant ({len(CACHE['etats'])} entités)", flush=True)
                elif msg.get("type") == "event":
                    d = msg["event"]["data"]
                    if d.get("new_state") is None:
                        CACHE["etats"].pop(d["entity_id"], None)
                    else:
                        CACHE["etats"][d["entity_id"]] = d["new_state"]
                    CACHE["horodatage"] = time.time()
                    with CHANGEMENT:
                        CHANGEMENT.notify_all()
        except Exception as exc:
            CACHE["direct"], CACHE["erreur"] = False, f"connexion directe perdue : {exc}"
            print(f"WebSocket HA : {exc}. Nouvel essai dans 5 s.", flush=True)
        finally:
            if ws:
                ws.fermer()
        time.sleep(5)


def demarrer_abonnement():
    if not DEMO and ha.WS_URL:
        threading.Thread(target=_abonnement, daemon=True).start()


def lire_etats():
    if CACHE["direct"]:
        return True
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
    """État le plus récent. Avec la connexion directe, le cache EST à jour."""
    if DEMO or CACHE["direct"]:
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


def verifier(eid, attendu, delai=3.0):
    """Attend que l'entité prenne l'état attendu. Faux si elle ne répond pas.
    En direct : réveillé à chaque changement d'état, donc réponse quasi immédiate."""
    fin = time.time() + delai
    while time.time() < fin:
        if etat_direct(eid) == attendu:
            return True
        if CACHE["direct"]:
            with CHANGEMENT:
                CHANGEMENT.wait(timeout=0.3)
        else:
            time.sleep(0.4)
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
    MC = CFG.get("maison_chauffage") or {}
    ids = [MC.get("menu"), CFG.get("veille_si_coupee")]
    ids += [CFG["meteo"].get(k) for k in ("entite", "vigilance", "temperature_exterieure", "humidite_exterieure", "risque_gel", "soleil")]
    for p in CFG["pieces"]:
        ids += [p.get("temperature"), p.get("humidite")]
        c = p.get("convecteur") or {}
        ids += [c.get(k) for k in ("mode", "puissance", "interrupteur")]
        ids += [(p.get("poele") or {}).get("prise"), (p.get("ventilation") or {}).get("entite")]
        pe = (p.get("porte") or {}).get("entite")
        ids += pe if isinstance(pe, list) else [pe]
        ids += [l["entite"] for l in p.get("lampes") or []]
        ids += [s["entite"] for g in p.get("scenes") or [] for s in g["liste"]]
        ids += [x for i in p.get("infos") or [] for x in (i.get("entite"), i.get("mesure"), i.get("mesure2"))]
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
        out.append({"id": l["id"], "nom": l["nom"], "note": l.get("note", ""), "groupe": l.get("groupe", ""),
                    "on": st == "on", "sans_courant": sans_courant,
                    "ko": st in INDISPO and not sans_courant,
                    "variable": l["entite"].startswith("light.") and any(x != "onoff" for x in modes),
                    "luminosite": round(br * 100 / 255) if br else None,
                    "minuterie_min": l.get("minuterie_min"), "reste": reste_minuterie(f"lampe:{p['id']}:{l['id']}")})
    return out


# Fiche du guide ouverte par le picto (i) de chaque section, selon le type de pièce.
# Une pièce peut les remplacer avec « guide: {chauffage: …, lumieres: …, ventilation: …, porte: …} ».
GUIDE_DEFAUT = {"poele": {"chauffage": "poele-ecran"},
                "convecteur": {"chauffage": "mozart-choisir"},
                "non_pilote": {"chauffage": "mozart-choisir"}}


def analyser(CFG):
    S, modes = CFG["seuils"], CFG["modes"]
    pieces = []
    for p in CFG["pieces"]:
        t, h = num(p.get("temperature")), num(p.get("humidite"))
        d = {"id": p["id"], "nom": p["nom"], "type": p.get("type", "sans_chauffage"),
             "t": fmt(t), "h": None if h is None else f"{h:.0f} %", "humide": h is not None and h > S["humidite_max"],
             "conseils": p.get("conseils") or [],
             "guide": dict(GUIDE_DEFAUT.get(p.get("type"), {}), **(p.get("guide") or {}))}
        c = p.get("convecteur")
        if c:
            mode, w = etat(c.get("mode")), num(c.get("puissance"))
            options = attr(c.get("mode"), "options") or list(modes)
            chauffe = w is not None and w >= S["puissance_min_chauffe"]
            if mode in INDISPO:
                diag, txt = "ko", "Ne répond pas"
            elif chauffe:
                diag, txt = "chauffe", f"Chauffe en ce moment, {fmt(w, 0)} W"
            elif mode in CFG["modes_chauffe"] and t is not None and t < S["temp_chauffe_attendue"]:
                diag, txt = "panne", "Ne chauffe pas"
            elif mode in CFG["modes_chauffe"]:
                diag, txt = "ok", "À température"
            elif mode == "Eco":
                diag, txt = "eco", "En économie"
            elif mode == "FrostProtection":
                diag, txt = "horsgel", "Hors-gel"
            else:
                diag, txt = "arret", "À l’arrêt"
            d["chauffage"] = {"type": "radiateur", "mode": mode, "dispo": mode not in INDISPO, "diag": diag, "etat": txt,
                              "libelle": modes.get(mode, {}).get("libelle", "Autre réglage" if mode not in INDISPO else "Ne répond pas"),
                              "panne": diag == "panne", "aide": modes.get(mode, {}).get("aide", ""),
                              "modes": [{"valeur": k, "libelle": v["libelle"], "sous": v.get("sous", ""), "icone": v.get("icone", "")}
                                        for k, v in modes.items() if k in options]}
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
        elif p.get("type") == "non_pilote":
            d["chauffage"] = {"type": "non_pilote", "libelle": "Non piloté"}
        lampes = _lampes(p)
        d["lampes"] = lampes
        on = [l for l in lampes if l["on"]]
        lum = [l["luminosite"] for l in on if l["luminosite"]]
        d["lumiere"] = {"etat": "none" if not lampes else ("on" if on else "off"),
                        "nb_on": len(on), "nb": len(lampes), "nb_indispo": sum(1 for l in lampes if l["ko"] or l["sans_courant"]),
                        "luminosite": round(sum(lum) / len(lum)) if lum else None,
                        "variable": any(l["variable"] for l in lampes),
                        "texte": "Pas de lumière pilotée" if not lampes else ("Éteinte" if not on else
                                 ("Allumée" if len(lampes) == 1 else f"{len(on)} sur {len(lampes)}"))}
        d["scenes"] = [{"titre": g.get("titre", "Scènes"), "liste": [{"id": f"{gi}-{si}", "nom": s["nom"]} for si, s in enumerate(g["liste"])]}
                       for gi, g in enumerate(p.get("scenes") or [])]
        infos = []
        for i in p.get("infos") or []:
            if i.get("mesure"):
                v1, v2 = num(i["mesure"]), num(i.get("mesure2"))
                txt = " · ".join(x for x in (f"{fmt(v1)} {i.get('unite', '')}" if v1 is not None else None,
                                             f"{fmt(v2, 0)} {i.get('unite2', '')}" if v2 is not None else None) if x) or "—"
                infos.append({"nom": i["nom"], "icone": i.get("icone", ""), "texte": txt, "etat": "mesure", "aide": i.get("aide", ""), "guide": i.get("guide")})
            else:
                st = etat(i["entite"])
                e = "ko" if st in INDISPO else ("on" if st == "on" else "off")
                txt = i.get("indispo", "Indisponible") if e == "ko" else i.get(e, "En marche" if e == "on" else "Arrêté")
                infos.append({"nom": i["nom"], "icone": i.get("icone", ""), "texte": txt, "etat": e, "aide": i.get("aide", ""), "guide": i.get("guide")})
        d["infos"] = infos
        po = p.get("porte")
        if po:
            ids = po.get("entite") or []
            sts = [etat(i) for i in (ids if isinstance(ids, list) else [ids])]
            connus = [x for x in sts if x not in INDISPO]
            d["porte"] = {"nom": po.get("nom", "Porte"),
                          "etat": "inconnu" if not connus else ("ouverte" if any(x in ("on", "open") for x in connus) else "fermee")}
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
    MC = CFG.get("maison_chauffage") or {}
    menu = etat(MC.get("menu"))
    hext, gel = num(M.get("humidite_exterieure")), num(M.get("risque_gel"))
    vs = CFG.get("veille_si_coupee")
    return {"pieces": pieces,
            "veille": bool(vs) and etat(vs) != "on",
            "maison_chauffage": {"options": list((MC.get("options") or {}).keys()), "mode": None if menu in INDISPO else menu} if MC else None,
            "exterieur": {"t": fmt(ext) if isinstance(ext, (int, float)) else None, "h": None if hext is None else f"{hext:.0f} %",
                          "gel": None if gel is None else round(gel),
                          "condition": CONDITIONS.get(etat(M.get("entite")), etat(M.get("entite"))), "lieu": M.get("lieu", "")}}


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

    if T == "scene":
        try:
            gi, si = (int(x) for x in str(q.get("scene", "")).split("-"))
            s = (p or {}).get("scenes")[gi]["liste"][si]
        except (ValueError, TypeError, IndexError, KeyError):
            return refuse()
        return resultat(service("scene", "turn_on", {"entity_id": s["entite"]}), "La scène n'a pas pu être lancée. L'éclairage est peut-être en veille.")

    if T == "maison_mode":
        MC = CFG.get("maison_chauffage") or {}
        mode = (MC.get("options") or {}).get(q.get("valeur"))
        if not mode:
            return refuse()
        ok = service("input_select", "select_option", {"entity_id": MC["menu"], "option": q["valeur"]})
        for pc in CFG["pieces"]:
            c = pc.get("convecteur")
            if c and c.get("mode") and mode in (attr(c["mode"], "options") or [mode]):
                ok &= service("select", "select_option", {"entity_id": c["mode"], "option": mode})
        return resultat(ok)

    if T == "lampe":
        p, l = lampe_cfg(CFG, q.get("piece"), q.get("lampe"))
        if not l:
            return refuse()
        val = q.get("valeur")
        if val == "on" and l.get("alimentation") and etat(l["alimentation"]) != "on":
            return 200, {"ok": False, "message": f"{l['nom']} est indisponible : sa prise est coupée (maison en veille)."}
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
