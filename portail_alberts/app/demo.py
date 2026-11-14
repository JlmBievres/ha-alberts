"""Valeurs relevées sur les captures HA du 13/11/2026, pour tester sans Home Assistant."""
def _e(state, **attributes):
    return {"state": state, "attributes": attributes}

OPTS = ["Comfort", "ComfortMinus1", "ComfortMinus2", "Eco", "FrostProtection", "Off"]
ETATS_DEMO = {
    "select.convecteur_meije_fil_pilote": _e("ComfortMinus1", options=OPTS),
    "sensor.convecteur_meije_puissance": _e("2.0"),
    "sensor.meije_temperature": _e("15.0"), "sensor.meije_humidite": _e("51.12"),
    "select.convecteur_ecrins_fil_pilote": _e("ComfortMinus1", options=OPTS),
    "sensor.convecteur_ecrins_puissance": _e("1374.0"),
    "sensor.ecrins_temperature": _e("17.1"), "sensor.ecrins_humidite": _e("49.62"),
    "select.convecteur_entree_bas_fil_pilote": _e("Comfort", options=OPTS),
    "sensor.convecteur_entree_bas_puissance": _e("0.0"),
    "sensor.entree_bas_temperature": _e("17.1"), "sensor.entree_bas_humidite": _e("66.03"),
    "select.convecteur_atelier_fil_pilote": _e("Comfort", options=OPTS),
    "sensor.convecteur_atelier_puissance": _e("957.0"),
    "sensor.atelier_temperature": _e("15.2"), "sensor.atelier_humidite": _e("64.83"),
    "select.convecteur_sdb_cave_fil_pilote": _e("ComfortMinus1", options=OPTS),
    "sensor.convecteur_sdb_cave_puissance": _e("684.0"),
    "sensor.sdb_cave_temperature": _e("17.8"), "sensor.sdb_cave_humidite": _e("74.28"),
    "sensor.sejour_temperature": _e("18.7"), "sensor.sejour_humidite": _e("50.79"),
    "sensor.salon_temperature": _e("19.9"), "sensor.salon_humidite": _e("61.53"),
    "sensor.exterieur_temperature": _e("7.2"),
    "weather.les_alberts": _e("rainy"),
    "sensor.05_weather_alert": _e("Jaune"),
    "switch.extracteur_salle_de_bain_cave": _e("off"),
    "switch.deshumidificateur": _e("off"),
    "light.escalier": _e("off", friendly_name="Escalier"),
    "light.chambre_refuge": _e("on", friendly_name="Chambre Refuge"),
    "light.sejour": _e("off", friendly_name="Séjour"),
    "light.salon": _e("off", friendly_name="Salon"),
    "light.salle_de_bain_cave": _e("off", friendly_name="Salle de bain cave"),
    "light.chevet": _e("on", friendly_name="Chevet"),
    "binary_sensor.porte_haut": _e("off"), "binary_sensor.porte_bas": _e("off"),
}
