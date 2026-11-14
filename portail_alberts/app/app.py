"""Portail voyageurs Les Alberts - v0.1.0
Bibliothèque standard Python + PyYAML uniquement (pas de Flask) : moins de
dépendances = moins de casse quand l'image de base de HA évolue.

Lancement :
  - Add-on HA : jeton fourni par le Supervisor (lu via s6).
  - Dev PI500 : HA_URL=http://ip:8123 HA_TOKEN=xxx python3 app.py
  - Démo      : DEMO=1 python3 app.py
"""
import json, os, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import yaml

VERSION = "0.1.1"
ICI = Path(__file__).parent
DEMO = os.environ.get("DEMO") == "1"
S6 = Path("/run/s6/container_environment/SUPERVISOR_TOKEN")


def _jeton():
    t = os.environ.get("SUPERVISOR_TOKEN")
    if not t and S6.exists():
        t = S6.read_text().strip()
    return t


if _jeton():
    HA_URL, TOKEN = "http://supervisor/core", _jeton()
else:
    HA_URL, TOKEN = os.environ.get("HA_URL", "").rstrip("/"), os.environ.get("HA_TOKEN", "")

CACHE = {"etats": {}, "horodatage": 0, "erreur": None}


def charger_config():
    """Relu à chaque requête : une modif du YAML s'applique sans redémarrer."""
    p = Path("/config/entities.yaml")
    if not p.exists():
        p = ICI / "entities.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")), str(p)


# ---------- Accès Home Assistant ----------
def _ha(methode, chemin, corps=None):
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(f"{HA_URL}/api{chemin}", data=data, method=methode,
                                 headers={"Authorization": f"Bearer {TOKEN}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def lire_etats():
    if DEMO:
        if not CACHE["etats"]:
            from demo import ETATS_DEMO
            CACHE["etats"] = ETATS_DEMO
        CACHE["horodatage"] = time.time()
        return True
    try:
        CACHE["etats"] = {e["entity_id"]: e for e in _ha("GET", "/states")}
        CACHE["horodatage"], CACHE["erreur"] = time.time(), None
        return True
    except Exception as exc:
        CACHE["erreur"] = str(exc)
        print(f"HA injoignable : {exc}", flush=True)
        return False


def appel_service(domaine, service, data):
    if DEMO:
        e = CACHE["etats"].setdefault(data["entity_id"], {"state": None, "attributes": {}})
        e["state"] = data["option"] if service == "select_option" else "on"
        return True
    try:
        _ha("POST", f"/services/{domaine}/{service}", data)
        return True
    except Exception as exc:
        print(f"Action refusée par HA : {exc}", flush=True)
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


# ---------- Règles : alertes et conseils ----------
def analyser(CFG):
    S = CFG["seuils"]
    alertes, pieces = [], []
    for p in CFG["pieces"]:
        t, h = num(p.get("temperature")), num(p.get("humidite"))
        mode, w = etat(p.get("mode")), num(p.get("puissance"))
        diag = None
        inter = p.get("interrupteur")
        if inter and etat(inter) == "off":
            diag = "coupé"
            alertes.append({"niveau": "orange", "titre": f"Convecteur coupé : {p['nom']}",
                "texte": "Le convecteur est hors tension, il ne peut pas chauffer.",
                "action": {"type": "allumer", "entite": inter, "libelle": "Remettre sous tension"}})
        elif mode in CFG["modes_chauffe"]:
            if w is not None and w >= S["puissance_min_chauffe"]:
                diag = "chauffe"
            elif t is not None and t < S["temp_chauffe_attendue"]:
                diag = "anomalie"
                alertes.append({"niveau": "orange", "titre": f"{p['nom']} ne chauffe pas",
                    "texte": f"{t:.1f} °C alors que le convecteur est en confort. Vérifiez qu'il est "
                             "allumé (interrupteur sur le côté), sinon voyez la fiche dédiée.",
                    "fiche": "fiche-chauffage"})
            else:
                diag = "à température"
        if t is not None and t < S["temp_gel"]:
            alertes.append({"niveau": "rouge", "titre": f"Risque de gel : {p['nom']}",
                "texte": f"{t:.1f} °C. Mettez la pièce en Confort et prévenez le propriétaire."})
        elif t is not None and t < S["temp_froide"] and diag != "anomalie":
            alertes.append({"niveau": "jaune", "titre": f"{p['nom']} est froide",
                "texte": f"{t:.1f} °C. Passez en Confort ; comptez 1 à 2 h pour gagner quelques degrés."})
        if h is not None and h > S["humidite_max"]:
            a = {"niveau": "orange", "titre": f"Humidité élevée : {p['nom']}",
                 "texte": f"{h:.0f} %. Laissez la porte ouverte après la douche et aérez 10 minutes."}
            aide = p.get("aide_humidite")
            if aide and etat(aide["entite"]) != "on":
                a["texte"] = f"{h:.0f} %. " + a["texte"]
                a["action"] = {"type": "allumer", "entite": aide["entite"], "libelle": aide["libelle"]}
            alertes.append(a)
        options = attr(p.get("mode"), "options") or list(CFG["modes_autorises"])
        pieces.append({"nom": p["nom"], "temperature": t, "humidite": h, "mode": mode,
            "puissance": w, "diag": diag, "entite_mode": p.get("mode"),
            "modes": [{"valeur": k, "libelle": v} for k, v in CFG["modes_autorises"].items() if k in options]})

    ext = CFG["exterieur"]
    am = etat(ext.get("alerte"))
    if am and am.lower() not in ("vert", "green", "unknown", "unavailable"):
        alertes.append({"niveau": "jaune", "titre": f"Vigilance météo {am.lower()}",
            "texte": "Consultez la météo avant de prendre la route ; pneus neige ou chaînes en saison."})

    allumees = [attr(l, "friendly_name") or l for l in CFG["lumieres"] if etat(l) == "on"]
    ouvertes = [d["nom"] for d in CFG.get("portes") or [] if etat(d["entite"]) in ("on", "open", "unlocked")]
    pas_eco = [p["nom"] for p in pieces if p["mode"] and p["mode"] not in CFG["mode_depart"]]
    depart = [
        {"texte": "Chauffage en Éco ou Hors-gel dans toutes les pièces", "ok": not pas_eco, "detail": pas_eco},
        {"texte": "Toutes les lumières éteintes", "ok": not allumees, "detail": allumees},
        {"texte": "Portes fermées", "ok": not ouvertes, "detail": ouvertes},
    ]
    niveaux = [a["niveau"] for a in alertes]
    statut = next((n for n in ("rouge", "orange", "jaune") if n in niveaux), "vert")
    ordre = {"rouge": 0, "orange": 1, "jaune": 2}
    return {"statut": statut, "alertes": sorted(alertes, key=lambda a: ordre[a["niveau"]]),
            "pieces": pieces, "depart": depart,
            "indisponibles": [e for e in _entites(CFG) if etat(e) == "unavailable"],
            "absentes": [e for e in _entites(CFG) if e not in CACHE["etats"]],
            "exterieur": {"temperature": num(ext.get("temperature")), "alerte": am}}


def _entites(CFG):
    ids = [CFG["exterieur"].get(k) for k in ("temperature", "meteo", "alerte")]
    for p in CFG["pieces"]:
        ids += [p.get(k) for k in ("mode", "puissance", "temperature", "humidite", "interrupteur")]
        ids += [p["aide_humidite"]["entite"]] if p.get("aide_humidite") else []
    ids += CFG["lumieres"] + [d["entite"] for d in CFG.get("portes") or []]
    return [i for i in ids if i]


def action(CFG, q):
    """Liste blanche stricte."""
    eid = q.get("entite", "")
    if q.get("type") == "mode":
        if eid not in {p.get("mode") for p in CFG["pieces"]} or q.get("valeur") not in CFG["modes_autorises"]:
            return 403, {"ok": False, "message": "Action non autorisée"}
        return 200, {"ok": appel_service("select", "select_option", {"entity_id": eid, "option": q["valeur"]})}
    if q.get("type") == "allumer":
        autorises = {p.get("interrupteur") for p in CFG["pieces"]} | \
                    {p["aide_humidite"]["entite"] for p in CFG["pieces"] if p.get("aide_humidite")}
        if not eid or eid not in autorises:
            return 403, {"ok": False, "message": "Action non autorisée"}
        return 200, {"ok": appel_service(eid.split(".")[0], "turn_on", {"entity_id": eid})}
    return 400, {"ok": False, "message": "Action inconnue"}


# ---------- Serveur HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def _envoyer(self, code, corps, type_="application/json"):
        if not isinstance(corps, bytes):
            corps = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{type_}; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        chemin = self.path.split("?")[0]
        if chemin in ("/", "/index.html"):
            return self._envoyer(200, (ICI / "index.html").read_bytes(), "text/html")
        try:
            CFG, src = charger_config()
        except Exception as exc:
            return self._envoyer(500, {"erreur": f"entities.yaml illisible : {exc}"})
        if chemin == "/api/etat":
            frais = lire_etats()
            if not CACHE["etats"]:
                return self._envoyer(503, {"erreur": "La maison ne répond pas encore. Réessayez dans une minute."})
            d = analyser(CFG)
            d.update(horodatage=CACHE["horodatage"], a_jour=frais)
            return self._envoyer(200, d)
        if chemin == "/sante":
            lire_etats()
            return self._envoyer(200 if not CACHE["erreur"] else 503, {
                "version": VERSION, "jeton_present": bool(TOKEN), "config": src,
                "erreur_ha": CACHE["erreur"], "nb_entites_ha": len(CACHE["etats"]),
                "entites_absentes": [e for e in _entites(CFG) if e not in CACHE["etats"]]})
        self._envoyer(404, {"erreur": "introuvable"})

    def do_POST(self):
        if self.path != "/api/action":
            return self._envoyer(404, {"erreur": "introuvable"})
        try:
            q = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
            CFG, _ = charger_config()
        except Exception:
            return self._envoyer(400, {"ok": False, "message": "Requête invalide"})
        self._envoyer(*action(CFG, q))

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Portail Les Alberts {VERSION} - {'DÉMO' if DEMO else HA_URL} - port 8099", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
