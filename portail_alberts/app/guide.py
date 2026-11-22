"""Guide de la maison : lecture seule dans le portail.

Source, par ordre de priorité :
  1. /data/guide/guide.yaml   copie du dépôt GitHub PRIVÉ, synchronisée au démarrage
                               de l'application puis chaque nuit (option guide_depot)
  2. /config/guide.yaml       fichier déposé à la main dans /addon_configs/<id>_portail_alberts/
  3. guide_exemple.yaml       exemple livré avec l'application (sans contenu privé)

Les informations sensibles ne sont jamais dans le dépôt : le guide contient des repères
comme {telephone_proprietaire}, remplacés par les valeurs de /config/secrets.yaml,
fichier qui reste sur le Pi.
"""
import json, os, re, shutil, subprocess, threading, time
from pathlib import Path
import yaml

ICI = Path(__file__).parent
DATA, CONFIG = Path("/data"), Path("/config")
CLONE = DATA / "guide"
OPTIONS = DATA / "options.json"
ETAT = {"source": None, "synchro": None, "erreur": None, "version": None}
REPERE = re.compile(r"\{([a-z0-9_]+)\}")


def options():
    try:
        return json.loads(OPTIONS.read_text())
    except Exception:
        return {}


def _secrets():
    p = CONFIG / "secrets.yaml"
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {} if p.exists() else {}
    except Exception as exc:
        print(f"secrets.yaml illisible : {exc}", flush=True)
        return {}


def _remplacer(x, S):
    if isinstance(x, str):
        return REPERE.sub(lambda m: str(S.get(m.group(1), "• • •")), x)
    if isinstance(x, list):
        return [_remplacer(v, S) for v in x]
    if isinstance(x, dict):
        return {k: _remplacer(v, S) for k, v in x.items()}
    return x


def _fichier():
    for p, src in ((CLONE / "guide.yaml", "dépôt privé"), (CONFIG / "guide.yaml", "fichier local"),
                   (ICI / "guide_exemple.yaml", "exemple livré")):
        if p.exists():
            return p, src
    return None, None


_MEMO = {"mtime": None, "guide": None}


def charger():
    p, src = _fichier()
    if not p:
        return {"themes": [], "depannages": []}
    sec = CONFIG / "secrets.yaml"
    cle = (str(p), p.stat().st_mtime, sec.stat().st_mtime if sec.exists() else 0)
    if _MEMO["mtime"] != cle:
        g = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        _MEMO.update(mtime=cle, guide=_remplacer(g, _secrets()))
        ETAT["source"] = src
    return _MEMO["guide"]


def photo(nom):
    """Photo d'une fiche : uniquement des noms simples dans le dossier photos/ du guide."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(jpg|jpeg|png|webp)", nom or ""):
        return None
    for base in (CLONE / "photos", CONFIG / "photos"):
        f = base / nom
        if f.is_file():
            return f
    return None


# ------------------------------------------------------------ synchronisation git
def synchroniser():
    o = options()
    depot, branche = (o.get("guide_depot") or "").strip(), (o.get("guide_branche") or "main").strip()
    if not depot:
        ETAT.update(synchro="non configurée", erreur=None)
        return
    cle_src = CONFIG / "guide_deploy_key"
    if not cle_src.exists():
        ETAT.update(synchro="échec", erreur="Clé de déploiement absente : /addon_configs/<id>_portail_alberts/guide_deploy_key")
        return
    cle = DATA / "deploy_key"
    shutil.copyfile(cle_src, cle)
    os.chmod(cle, 0o600)
    env = dict(os.environ, GIT_SSH_COMMAND=f"ssh -i {cle} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new "
                                           f"-o UserKnownHostsFile={DATA / 'known_hosts'}")
    try:
        if (CLONE / ".git").exists():
            cmds = [["git", "-C", str(CLONE), "fetch", "--depth", "1", "origin", branche],
                    ["git", "-C", str(CLONE), "reset", "--hard", f"origin/{branche}"]]
        else:
            shutil.rmtree(CLONE, ignore_errors=True)
            cmds = [["git", "clone", "--depth", "1", "--branch", branche, depot, str(CLONE)]]
        for c in cmds:
            r = subprocess.run(c, env=env, capture_output=True, text=True, timeout=120)
            if r.returncode:
                raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1])
        v = subprocess.run(["git", "-C", str(CLONE), "log", "-1", "--format=%h %cd", "--date=short"],
                           capture_output=True, text=True).stdout.strip()
        ETAT.update(synchro=time.strftime("%d/%m %H:%M"), erreur=None, version=v)
        _MEMO["mtime"] = None
        print(f"Guide synchronisé : {v}", flush=True)
    except Exception as exc:
        ETAT.update(synchro="échec", erreur=str(exc))
        print(f"Synchronisation du guide impossible : {exc}", flush=True)


def demarrer_synchro():
    """Au démarrage puis chaque nuit à l'heure guide_heure (4 h par défaut)."""
    def boucle():
        synchroniser()
        while True:
            h = int(options().get("guide_heure", 4))
            t = time.localtime()
            attente = ((h - t.tm_hour) % 24 or 24) * 3600 - t.tm_min * 60 - t.tm_sec
            time.sleep(max(60, attente))
            synchroniser()
    threading.Thread(target=boucle, daemon=True).start()
