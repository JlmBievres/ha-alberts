"""Portail voyageurs Les Alberts.
Bibliothèque standard Python + PyYAML uniquement : moins de dépendances,
moins de casse quand l'image de base de Home Assistant évolue.

Lancement :
  - Application HA : jeton fourni par le Supervisor.
  - Dev PI500      : HA_URL=http://ip:8123 HA_TOKEN=xxx python3 app.py
  - Démo           : DEMO=1 python3 app.py
"""
import json, mimetypes, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

import guide
import ha
import maison

VERSION = "0.5.0"
ICI = Path(__file__).parent
STATIC = ICI / "static"
maison.DEMO = os.environ.get("DEMO") == "1"
CACHE = ha.Cache()
for _ext, _t in ((".woff2", "font/woff2"), (".js", "application/javascript"), (".css", "text/css"), (".svg", "image/svg+xml"), (".webp", "image/webp")):
    mimetypes.add_type(_t, _ext)
_CFG = {"cle": None, "cfg": None, "src": None, "alerte": None}


def charger_config():
    """/config/entities.yaml s'il existe et est au format 2, sinon le modèle livré."""
    p = Path("/config/entities.yaml")
    if not p.exists():
        p = ICI / "entities.yaml"
    cle = (str(p), p.stat().st_mtime)
    if _CFG["cle"] != cle:
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        _CFG["alerte"] = None
        if cfg.get("version") != 4:
            _CFG["alerte"] = f"{p} est à l'ancien format : modèle livré utilisé à la place. Reprendre le modèle 0.4."
            print(_CFG["alerte"], flush=True)
            p = ICI / "entities.yaml"
            cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
        _CFG.update(cle=cle, cfg=cfg, src=str(p))
    return _CFG["cfg"], _CFG["src"]


def _etats_frais():
    """En direct (WebSocket) : rien à relire. Sinon, relecture complète au plus toutes les 5 s."""
    if maison.CACHE["direct"]:
        return True
    if time.time() - maison.CACHE["horodatage"] > 5:
        return maison.lire_etats()
    return True


class Handler(BaseHTTPRequestHandler):
    server_version = "PortailAlberts"

    def _envoyer(self, code, corps, type_="application/json", cache=False):
        if not isinstance(corps, bytes):
            corps = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", f"{type_}; charset=utf-8" if type_.startswith(("text", "application/json", "application/javascript")) else type_)
        self.send_header("Cache-Control", "max-age=86400" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(corps)

    def _fichier(self, f, cache=False):
        if not f or not f.is_file():
            return self._envoyer(404, {"erreur": "introuvable"})
        t = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        return self._envoyer(200, f.read_bytes(), t, cache)

    def do_GET(self):
        u = urlparse(self.path)
        chemin, q = u.path, {k: v[0] for k, v in parse_qs(u.query).items()}
        if chemin in ("/", "/index.html"):
            return self._fichier(STATIC / "index.html")
        if chemin.startswith("/static/"):
            f = (STATIC / chemin[len("/static/"):]).resolve()
            if STATIC.resolve() not in f.parents:
                return self._envoyer(404, {"erreur": "introuvable"})
            return self._fichier(f, cache=chemin.startswith("/static/fonts/"))
        if chemin.startswith("/guide/photos/"):
            return self._fichier(guide.photo(chemin.rsplit("/", 1)[-1]), cache=True)
        try:
            CFG, src = charger_config()
        except Exception as exc:
            return self._envoyer(500, {"erreur": f"entities.yaml : {exc}"})

        if chemin == "/api/etat":
            frais = _etats_frais()
            if not maison.CACHE["etats"]:
                return self._envoyer(503, {"erreur": "La maison ne répond pas encore."})
            d = maison.analyser(CFG)
            d.update(version=VERSION, horodatage=maison.CACHE["horodatage"], a_jour=frais)
            return self._envoyer(200, d)
        if chemin == "/api/prises":
            _etats_frais()
            return self._envoyer(200, maison.prises(CFG))
        if chemin == "/api/meteo":
            _etats_frais()
            return self._json_calcul(lambda: CACHE.get("meteo", 900, lambda: maison.meteo(CFG)))
        if chemin == "/api/guide":
            return self._json_calcul(guide.charger)
        if chemin == "/sante":
            ok = maison.lire_etats()
            ids = maison.entites(CFG)
            # (« direct » : états reçus en temps réel par WebSocket)
            return self._envoyer(200 if ok else 503, {
                "version": VERSION, "demo": maison.DEMO, "direct": maison.CACHE["direct"], "jeton_present": bool(ha.TOKEN), "config": src, "alerte_config": _CFG["alerte"],
                "erreur_ha": maison.CACHE["erreur"], "nb_entites_ha": len(maison.CACHE["etats"]),
                "entites_absentes": [e for e in ids if e not in maison.CACHE["etats"]],
                "entites_indisponibles": [e for e in ids if maison.etat(e) == "unavailable"],
                "guide": dict(guide.ETAT)})
        self._envoyer(404, {"erreur": "introuvable"})

    def _json_calcul(self, f):
        try:
            r = f()
            return self._envoyer(200 if r is not None else 404, r if r is not None else {"erreur": "introuvable"})
        except Exception as exc:
            print(f"Calcul impossible ({self.path}) : {exc}", flush=True)
            return self._envoyer(503, {"erreur": "Donnée indisponible pour le moment."})

    def do_POST(self):
        if urlparse(self.path).path != "/api/action":
            return self._envoyer(404, {"erreur": "introuvable"})
        try:
            n = int(self.headers.get("Content-Length", 0) or 0)
            if n > 4096:
                raise ValueError("trop long")
            q = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(q, dict):
                raise ValueError("format")
            CFG, _ = charger_config()
        except Exception:
            return self._envoyer(400, {"ok": False, "message": "Requête invalide"})
        if not maison.CACHE["etats"]:
            maison.lire_etats()
        code, r = maison.action(CFG, q)
        if not maison.CACHE["direct"]:
            maison.CACHE["horodatage"] = 0      # sans connexion directe : relire à la prochaine demande
        print(f"Action {q.get('type')} {q.get('piece') or q.get('id') or ''} -> {'ok' if r.get('ok') else r.get('message')}", flush=True)
        self._envoyer(code, r)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Portail Les Alberts {VERSION} - {'DÉMO' if maison.DEMO else ha.REST} - port 8099", flush=True)
    if not maison.DEMO:
        maison.demarrer_abonnement()
        guide.demarrer_synchro()
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
