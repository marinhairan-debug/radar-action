# -*- coding: utf-8 -*-
"""
Module MACRO — « météo économique » à partir des données officielles de la Fed de Saint-Louis (FRED).
Gratuit, sans clé, fiable depuis un serveur.

Chaque indicateur donne un signal : +1 (favorable aux actions), 0 (neutre), -1 (défavorable),
avec une explication en français. La synthèse sert à ajuster les notes du radar.
"""
import datetime as dt
import io
import urllib.request

import numpy as np
import pandas as pd

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={debut}"

SERIES = {
    # États-Unis
    "T10Y2Y": "Écart de taux 10 ans - 2 ans (US)",
    "BAMLH0A0HYM2": "Prime de risque des obligations à haut rendement (US)",
    "NFCI": "Conditions financières (Fed de Chicago)",
    "ICSA": "Nouvelles inscriptions au chômage (US, hebdo)",
    "UNRATE": "Taux de chômage (US)",
    "CPIAUCSL": "Inflation (US)",
    "DFF": "Taux directeur de la Fed",
    "DGS10": "Taux 10 ans (US)",
    "VIXCLS": "VIX (peur des marchés)",
    # Zone euro
    "ECBDFR": "Taux directeur de la BCE (dépôt)",
    "BAMLHE00EHYIOAS": "Prime de risque haut rendement (zone euro)",
    "CP0000EZ19M086NEST": "Inflation (zone euro)",
}


def telecharger_fred(ids=None, annees=6, demo=False):
    ids = ids or list(SERIES)
    debut = (dt.date.today() - dt.timedelta(days=365 * annees)).isoformat()
    out = {}
    for s in ids:
        if demo:
            idx = pd.date_range(end=pd.Timestamp.today(), periods=annees * 52, freq="W")
            out[s] = pd.Series(np.cumsum(np.random.default_rng(len(s)).normal(0, 0.05, len(idx))) + 2, index=idx)
            continue
        try:
            with urllib.request.urlopen(URL.format(id=s, debut=debut), timeout=30) as r:
                df = pd.read_csv(io.StringIO(r.read().decode()))
            df.columns = ["date", "v"]
            ser = pd.to_numeric(df.v, errors="coerce")
            ser.index = pd.to_datetime(df.date)
            out[s] = ser.dropna()
        except Exception as e:  # noqa
            print("   ! FRED", s, e)
    return out


def _val(s, jours_avant=0):
    """Valeur à 'jours_avant' jours calendaires de la dernière observation."""
    if s is None or s.empty:
        return np.nan
    if jours_avant == 0:
        return float(s.iloc[-1])
    cible = s.index[-1] - pd.Timedelta(days=jours_avant)
    av = s[s.index <= cible]
    return float(av.iloc[-1]) if len(av) else np.nan


def _yoy(s):
    return (_val(s) / _val(s, 365) - 1) * 100 if s is not None and len(s) > 13 else np.nan


def indicateurs(f):
    """Retourne une liste d'indicateurs : dict(zone, nom, valeur, signal, texte)."""
    L = []

    def add(zone, nom, valeur, signal, texte):
        L.append({"zone": zone, "nom": nom, "valeur": valeur, "signal": signal, "texte": texte})

    # 1. Courbe des taux
    s = f.get("T10Y2Y")
    if s is not None and len(s):
        v = _val(s)
        min12 = float(s[s.index >= s.index[-1] - pd.Timedelta(days=365)].min())
        if v < 0:
            add("US", "Courbe des taux", f"{v:+.2f} pt", -1, "Inversée (taux courts > taux longs) : signal historique de récession dans les 6 à 24 mois.")
        elif min12 < 0:
            add("US", "Courbe des taux", f"{v:+.2f} pt", -1, "Se redresse après une inversion : historiquement, c'est souvent dans cette phase que la récession arrive.")
        else:
            add("US", "Courbe des taux", f"{v:+.2f} pt", 1, "Normale (taux longs > taux courts) : pas de signal de récession.")

    # 2. Prime de risque haut rendement US et euro
    for code, zone in (("BAMLH0A0HYM2", "US"), ("BAMLHE00EHYIOAS", "Europe")):
        s = f.get(code)
        if s is None or not len(s):
            continue
        v, d3 = _val(s), _val(s) - _val(s, 91)
        if v > 6 or d3 > 1.0:
            add(zone, "Stress du crédit", f"{v:.2f} % ({d3:+.2f} sur 3 mois)", -1,
                "Les entreprises fragiles paient beaucoup plus cher pour emprunter : les investisseurs ont peur, souvent avant les baisses des actions.")
        elif v < 4 and d3 <= 0.2:
            add(zone, "Stress du crédit", f"{v:.2f} % ({d3:+.2f} sur 3 mois)", 1, "Crédit détendu : les marchés financent facilement les entreprises.")
        else:
            add(zone, "Stress du crédit", f"{v:.2f} % ({d3:+.2f} sur 3 mois)", 0, "Niveau intermédiaire, à surveiller.")

    # 3. Conditions financières
    s = f.get("NFCI")
    if s is not None and len(s):
        v = _val(s)
        sig = -1 if v > 0 else (1 if v < -0.3 else 0)
        add("US", "Conditions financières", f"{v:+.2f}", sig,
            "Plus serrées que la moyenne (argent plus cher et plus rare)." if v > 0 else
            "Plus souples que la moyenne : environnement porteur pour les actifs risqués." if v < -0.3 else "Proches de la moyenne.")

    # 4. Inscriptions au chômage
    s = f.get("ICSA")
    if s is not None and len(s) > 60:
        m4 = s.rolling(4).mean()
        bas = float(m4.iloc[-52:].min())
        hausse = (float(m4.iloc[-1]) / bas - 1) * 100
        sig = -1 if hausse > 20 else (1 if hausse < 10 else 0)
        add("US", "Inscriptions au chômage", f"{float(m4.iloc[-1]) / 1000:.0f} k/sem. ({hausse:+.0f} % vs plus bas 1 an)", sig,
            "Hausse marquée : le marché du travail se dégrade." if sig < 0 else
            "Stables : le marché du travail tient." if sig > 0 else "Légère remontée, à surveiller.")

    # 5. Règle de Sahm (chômage)
    s = f.get("UNRATE")
    if s is not None and len(s) > 16:
        m3 = s.rolling(3).mean()
        sahm = float(m3.iloc[-1] - m3.iloc[-13:-1].min())
        sig = -1 if sahm >= 0.5 else (0 if sahm >= 0.3 else 1)
        add("US", "Chômage (règle de Sahm)", f"{_val(s):.1f} % (Sahm {sahm:+.2f})", sig,
            "Seuil de 0,5 atteint : ce signal a précédé ou accompagné toutes les récessions américaines depuis 1970." if sig < 0 else
            "Le chômage remonte, on approche du seuil d'alerte." if sig == 0 else "Pas de dégradation notable du chômage.")

    # 6. Inflation
    for code, zone in (("CPIAUCSL", "US"), ("CP0000EZ19M086NEST", "Europe")):
        s = f.get(code)
        if s is None or len(s) < 15:
            continue
        y, y_prec = _yoy(s), (_val(s, 90) / _val(s, 455) - 1) * 100
        sig = -1 if (y > 4 or (y > 3 and y > y_prec + 0.3)) else (1 if y < 3 else 0)
        add(zone, "Inflation", f"{y:.1f} % sur 1 an ({'en hausse' if y > y_prec + 0.1 else 'en baisse' if y < y_prec - 0.1 else 'stable'})", sig,
            "Élevée ou en accélération : risque de hausse des taux." if sig < 0 else
            "Maîtrisée : laisse de la marge aux banques centrales." if sig > 0 else "Un peu au-dessus de l'objectif de 2 %.")

    # 7. Politique monétaire
    for code, zone, nom in (("DFF", "US", "Fed"), ("ECBDFR", "Europe", "BCE")):
        s = f.get(code)
        if s is None or not len(s):
            continue
        d6 = _val(s) - _val(s, 182)
        sig = 1 if d6 < -0.2 else (-1 if d6 > 0.2 else 0)
        add(zone, f"Taux directeur {nom}", f"{_val(s):.2f} % ({d6:+.2f} sur 6 mois)", sig,
            "En baisse : la banque centrale soutient l'économie." if sig > 0 else
            "En hausse : la banque centrale freine l'économie." if sig < 0 else "Stable.")

    # 8. VIX
    s = f.get("VIXCLS")
    if s is not None and len(s):
        v = _val(s)
        sig = -1 if v > 30 else (1 if v < 18 else 0)
        add("US", "Peur des marchés (VIX)", f"{v:.1f}", sig,
            "Panique : forte volatilité, les stops sautent facilement." if v > 30 else
            "Calme." if v < 18 else "Nervosité modérée.")
    return L


def synthese(L, zone):
    sel = [i for i in L if i["zone"] == zone or (zone == "Europe" and i["nom"] in ("Peur des marchés (VIX)", "Conditions financières"))]
    if not sel:
        return {"etat": "inconnu", "score": 0.0, "n": 0}
    sc = float(np.mean([i["signal"] for i in sel]))
    etat = "favorable" if sc >= 0.34 else ("défavorable" if sc <= -0.2 else "neutre")
    return {"etat": etat, "score": sc, "n": len(sel)}


def tendance_taux(f):
    """Indication sectorielle (non validée par backtest) selon la direction du taux 10 ans US."""
    s = f.get("DGS10")
    if s is None or not len(s):
        return None
    d = _val(s) - _val(s, 91)
    if d < -0.3:
        return f"Taux 10 ans US en baisse ({d:+.2f} pt sur 3 mois) : contexte historiquement plus favorable aux valeurs de croissance (tech) et aux secteurs endettés (immobilier, services aux collectivités)."
    if d > 0.3:
        return f"Taux 10 ans US en hausse ({d:+.2f} pt sur 3 mois) : contexte historiquement plus favorable aux banques et assurances, plus difficile pour les valeurs de croissance chères."
    return f"Taux 10 ans US stable ({d:+.2f} pt sur 3 mois) : pas de biais sectoriel marqué."


def meteo(demo=False):
    f = telecharger_fred(demo=demo)
    L = indicateurs(f)
    return {"indicateurs": L, "US": synthese(L, "US"), "Europe": synthese(L, "Europe"),
            "taux": tendance_taux(f), "date": dt.date.today().isoformat()}


def html_meteo(m):
    import html as h
    couleur = {1: "#1a9a4b", 0: "#d58a00", -1: "#c62828"}
    pastille = {1: "🟢", 0: "🟠", -1: "🔴"}
    out = ["<div class='card'><h2>Météo économique</h2><div class='grid'>"]
    for z in ("US", "Europe"):
        s = m[z]
        out.append(f"<div class='kpi'><span>{'États-Unis' if z == 'US' else 'Zone euro'}</span><b>{s['etat'].capitalize()}</b>"
                   f"<span>score {s['score']:+.2f} sur {s['n']} indicateurs</span></div>")
    out.append("</div><table><tr><th>Zone</th><th>Indicateur</th><th>Valeur</th><th>Signal</th><th>Ce que ça veut dire</th></tr>")
    for i in m["indicateurs"]:
        out.append(f"<tr><td>{i['zone']}</td><td><b>{h.escape(i['nom'])}</b></td><td>{h.escape(i['valeur'])}</td>"
                   f"<td style='color:{couleur[i['signal']]}'>{pastille[i['signal']]}</td><td>{h.escape(i['texte'])}</td></tr>")
    out.append("</table>")
    if m.get("taux"):
        out.append(f"<p style='font-size:14px'><b>Taux et secteurs :</b> {h.escape(m['taux'])} "
                   "<span class='muted'>(tendance historique, pas une règle garantie)</span></p>")
    out.append("<p class='small muted'>Source : FRED, Fed de Saint-Louis. La macro sert à régler l'agressivité "
               "(nombre et taille des positions), pas à choisir une action à elle seule.</p></div>")
    return "".join(out)
