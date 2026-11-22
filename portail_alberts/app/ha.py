"""Accès à Home Assistant : API REST (états, services) et WebSocket (statistiques,
prévisions météo). Bibliothèque standard uniquement."""
import base64, json, os, socket, struct, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse

S6 = Path("/run/s6/container_environment/SUPERVISOR_TOKEN")


def _jeton():
    t = os.environ.get("SUPERVISOR_TOKEN")
    if not t and S6.exists():
        t = S6.read_text().strip()
    return t


if _jeton():                                   # dans l'add-on : proxy du Supervisor
    REST, WS_URL, TOKEN = "http://supervisor/core/api", "ws://supervisor/core/websocket", _jeton()
else:                                          # dev sur le PI500 : HA_URL + HA_TOKEN
    _b = os.environ.get("HA_URL", "").rstrip("/")
    REST, TOKEN = f"{_b}/api", os.environ.get("HA_TOKEN", "")
    WS_URL = _b.replace("http", "ws", 1) + "/api/websocket" if _b else ""


def rest(methode, chemin, corps=None, timeout=6):
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(f"{REST}{chemin}", data=data, method=methode,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class WebSocket:
    """Client WebSocket minimal (texte, masquage, fragments, ping)."""

    def __init__(self, url, timeout=15):
        u = urlparse(url)
        self.s = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
        cle = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {u.path or '/'} HTTP/1.1\r\nHost: {u.hostname}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {cle}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        tete = b""
        while b"\r\n\r\n" not in tete:
            bloc = self.s.recv(1024)
            if not bloc:
                raise ConnectionError("WebSocket fermé pendant la poignée de main")
            tete += bloc
        if b" 101 " not in tete.split(b"\r\n")[0]:
            raise ConnectionError(tete.split(b"\r\n")[0].decode(errors="replace"))
        self.reste = tete.split(b"\r\n\r\n", 1)[1]

    def _lire(self, n):
        while len(self.reste) < n:
            bloc = self.s.recv(65536)
            if not bloc:
                raise ConnectionError("WebSocket fermé")
            self.reste += bloc
        d, self.reste = self.reste[:n], self.reste[n:]
        return d

    def _trame(self, op, data):
        tete = bytes([0x80 | op])
        n = len(data)
        if n < 126:
            tete += bytes([0x80 | n])
        elif n < 65536:
            tete += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            tete += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masque = os.urandom(4)
        self.s.sendall(tete + masque + bytes(b ^ masque[i % 4] for i, b in enumerate(data)))

    def envoyer(self, obj):
        self._trame(1, json.dumps(obj).encode())

    def recevoir(self):
        morceaux = b""
        while True:
            b1, b2 = self._lire(2)
            fin, op, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._lire(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._lire(8))[0]
            masque = self._lire(4) if b2 & 0x80 else None
            data = self._lire(n)
            if masque:
                data = bytes(b ^ masque[i % 4] for i, b in enumerate(data))
            if op == 9:
                self._trame(10, data); continue
            if op == 8:
                raise ConnectionError("WebSocket fermé par HA")
            if op in (0, 1):
                morceaux += data
                if fin:
                    return json.loads(morceaux)

    def fermer(self):
        try:
            self.s.close()
        except OSError:
            pass


def ws_requetes(requetes):
    """Ouvre une connexion, s'authentifie, envoie les requêtes, renvoie leurs résultats."""
    ws = WebSocket(WS_URL)
    try:
        if ws.recevoir().get("type") != "auth_required":
            raise ConnectionError("Réponse inattendue de HA")
        ws.envoyer({"type": "auth", "access_token": TOKEN})
        if ws.recevoir().get("type") != "auth_ok":
            raise PermissionError("Jeton refusé par HA")
        res = {}
        for i, q in enumerate(requetes, start=1):
            ws.envoyer(dict(q, id=i))
        while len(res) < len(requetes):
            m = ws.recevoir()
            if m.get("type") == "result":
                res[m["id"]] = m.get("result") if m.get("success") else {"erreur": m.get("error")}
        return [res[i] for i in range(1, len(requetes) + 1)]
    finally:
        ws.fermer()


class Cache:
    """Petit cache à durée de vie, pour ménager le Pi."""

    def __init__(self):
        self.d = {}

    def get(self, cle, duree, calcul):
        v = self.d.get(cle)
        if v and time.time() - v[0] < duree:
            return v[1]
        r = calcul()
        self.d[cle] = (time.time(), r)
        return r
