"""Données de démonstration (DEMO=1) : valeurs relevées le 14/11/2026, plus des
statistiques et prévisions simulées. Permet de tester le portail sans Home Assistant."""
import math, random
from datetime import datetime, timedelta


def _e(state, **attributes):
    return {"state": state, "attributes": attributes}


OPTS = ["Comfort", "ComfortMinus1", "ComfortMinus2", "Eco", "FrostProtection", "Off"]
DIM = {"supported_color_modes": ["brightness"]}


def etats():
    E = {
        "select.convecteur_chambre_meije_mode_du_fil_pilote": _e("ComfortMinus1", options=OPTS),
        "sensor.convecteur_chambre_meije_demande_instantanee": _e("2.0"), "switch.convecteur_chambre_meije": _e("on"),
        "sensor.capteur_ch_meije_temperature": _e("15.1"), "sensor.capteur_ch_meije_humidite": _e("49.43"),
        "select.convecteur_ecrins_mode_du_fil_pilote": _e("ComfortMinus1", options=OPTS),
        "sensor.convecteur_ecrins_demande_instantanee": _e("0.0"), "switch.convecteur_ecrins": _e("on"),
        "sensor.capteur_ch_parents_temperature": _e("17.4"), "sensor.capteur_ch_parents_humidite": _e("51.81"),
        "select.convecteur_entree_bas_mode_du_fil_pilote": _e("Comfort", options=OPTS),
        "sensor.convecteur_entree_bas_demande_instantanee": _e("0.0"), "switch.convecteur_entree_bas": _e("on"),
        "sensor.capteur_entree_temperature": _e("17.42"), "sensor.capteur_entree_humidite": _e("63.52"),
        "select.convecteur_atelier_mode_du_fil_pilote": _e("Comfort", options=OPTS),
        "sensor.convecteur_atelier_demande_instantanee": _e("904"), "switch.convecteur_atelier": _e("on"),
        "sensor.capteur_atelier_temperature": _e("15.11"), "sensor.capteur_atelier_humidity": _e("64.05"),
        "select.convecteur_sdb_cave_mode_du_fil_pilote": _e("ComfortMinus1", options=OPTS),
        "sensor.convecteur_sdb_cave_demande_instantanee": _e("0.0"), "switch.convecteur_sdb_cave": _e("on"),
        "sensor.capteur_sdbcave_temperature": _e("17.76"), "sensor.capteur_sdbcave_humidity": _e("78.19"),
        "sensor.capteur_sejour_temperature": _e("18.61"), "sensor.capteur_sejour_humidity": _e("49.73"),
        "sensor.capteur_salon_temperature": _e("19.2"), "sensor.capteur_salon_humidity": _e("61.26"),
        "sensor.capteur_douche_etage_temperature": _e("18.18"), "sensor.capteur_douche_etage_humidity": _e("50.92"),
        "sensor.capteur_ch_refuge_temperature": _e("17.44"), "sensor.capteur_ch_refuge_humidite": _e("41.05"),
        "sensor.capteur_exterieur_temperature": _e("3.75"),
        "weather.val_des_pres": _e("rainy", temperature=4.1, humidity=90, pressure=1007.5, wind_speed=10.8, wind_bearing=202, cloud_coverage=90),
        "sensor.05_weather_alert": _e("Jaune"),
        "sun.sun": _e("below_horizon", next_dawn=_iso(7, 0), next_rising=_iso(7, 32), next_noon=_iso(12, 20),
                      next_setting=_iso(17, 8), next_dusk=_iso(17, 40)),
        "input_boolean.booleen_convecteur_tarif_nuit": _e("on"),
        "switch.atelier_chauffe_eau": _e("on"),
        "switch.prise_chauffe_eau_switch_3": _e("on"),
        "switch.prise_wi_fi_tableau_commutateur": _e("on"),
        "switch.prise_wi_fi_sejour_commutateur": _e("on"),
        "switch.prise_television_switch_3": _e("on"),
        "switch.livebox_nautilus_wifi": _e("on"), "switch.livebox_nautilus_guest_wifi": _e("on"),
        "sensor.prise_poele_salon_active_power_3": _e("42.0"), "sensor.tz3000_2putqrmw_ts011f_active_power": _e("0.0"),
        "switch.prise_poele_salon_switch_3": _e("on"),
        "switch.tz3000_2putqrmw_ts011f_switch": _e("off"),
        "switch.prise_entree_basse_switch": _e("off"),
        "switch.prise_wi_fi_salon_commutateur": _e("off"),
        "light.escalier": _e("off", **DIM),
        "light.chambre_refuge_groupe": _e("on", brightness=180, **DIM),
        "light.chambre_a_coucher": _e("on", brightness=255, **DIM),
        "light.sejour": _e("on", brightness=200, **DIM),
        "light.salon": _e("off", **DIM),
        "light.salle_de_bain_cave": _e("on", brightness=180, **DIM),
        "light.strip_entree_lumiere": _e("off", **DIM),
        "light.strip_bureau_light": _e("unavailable"),
        "light.hue_go_1": _e("off", **DIM),
        "light.hue_lightstrip_1": _e("off", **DIM),
        "light.commande_vmc": _e("off", supported_color_modes=["onoff"]),
        "binary_sensor.ouverture_haut_ouverture": _e("off"), "binary_sensor.ouverture_haut_ouverture_2": _e("off"),
        "binary_sensor.ouverture_bas_ouverture": _e("on"), "binary_sensor.ouverture_bas_ouverture_2": _e("unavailable"),
        "switch.prise_deshumidificateur_switch_3": _e("off"), "switch.atelier_chauffe_eau": _e("on"),
    }
    return E


def _iso(h, m):
    d = datetime.now().astimezone().replace(hour=h, minute=m, second=0, microsecond=0)
    if d < datetime.now().astimezone():
        d += timedelta(days=1)
    return d.isoformat()


def service(E, dom, nom, data):
    eid = data["entity_id"]
    e = E.setdefault(eid, {"state": None, "attributes": {}})
    if e["state"] == "unavailable":
        return                                   # simule une lampe coupée au mur
    if nom == "select_option":
        e["state"] = data["option"]
    elif nom in ("turn_on", "turn_off"):
        e["state"] = "on" if nom == "turn_on" else "off"
        if "brightness_pct" in data:
            e["attributes"]["brightness"] = round(data["brightness_pct"] * 255 / 100)


def stats(ids, debut, fin, periode, types):
    pas = {"5minute": timedelta(minutes=5), "hour": timedelta(hours=1), "day": timedelta(days=1)}[periode]
    out = {}
    for n, eid in enumerate(ids):
        rnd = random.Random(eid)
        rows, t = [], debut
        while t < fin:
            if "mean" in types:
                cyc = (t.hour * 60 + t.minute) / 60
                on = (int(cyc * 3 + n) % 4 == 0) and not (eid.endswith("meije_demande_instantanee") and t > fin - timedelta(hours=10))
                rows.append({"start": t.timestamp() * 1000, "mean": 1000 * on + rnd.random() * 5})
            else:
                base = 0.35 if t.hour < 6 or t.hour >= 22 else 0.15
                k = base * (1 + 0.6 * math.sin(n + t.day)) * (24 if periode == "day" else 1)
                rows.append({"start": t.timestamp() * 1000, "change": max(0, k + rnd.random() * 0.1)})
            t += pas
        out[eid] = rows
    return out


def previsions():
    now = datetime.now().astimezone().replace(minute=0, second=0, microsecond=0)
    heures = [{"datetime": (now + timedelta(hours=i + 1)).isoformat(), "condition": "rainy", "temperature": 4.4 + i * 0.3,
               "precipitation": [1.6, 1.4, 1.9, 0.9, 0.1, 0.0][i]} for i in range(6)]
    jours = [{"datetime": (now + timedelta(days=i)).isoformat(), "condition": c, "temperature": mx, "templow": mn, "precipitation": mm}
             for i, (c, mx, mn, mm) in enumerate([("rainy", 6.1, -1.4, 15.4), ("cloudy", 3.6, -0.9, 0.4),
                                                  ("rainy", 7.1, -3.1, 4.8), ("snowy", 2.3, -1.1, 24.1), ("partlycloudy", 4.0, -4.2, 0.0)])]
    return {"hourly": heures, "daily": jours}
