# -*- coding: utf-8 -*-
"""
Suivi de MES actions : chaque jour, une note et un avis (garder, alléger, vendre…) pour chaque position.

Les positions sont gardées dans un dépôt GitHub PRIVÉ (portefeuille.json + historique.json),
pour qu'elles ne soient jamais visibles publiquement. Sans dépôt configuré, l'appli garde le
portefeuille le temps de la session (avec export / import d'un fichier).

Ligne de commande (lancée chaque soir par GitHub Actions, après « preparer ») :
    python portefeuille.py suivi
Variables d'environnement : PORTEFEUILLE_TOKEN (jeton GitHub), PORTEFEUILLE_REPO (ex. pseudo/radar-portefeuille)
"""
import base64
import datetime as dt
import json
import math
import os
import types
import urllib.error
import urllib.request
import uuid

import numpy as np
import pandas as pd

import radar_actions as ra

FLAT_TAX = 0.314          # prélèvement forfaitaire 2026 sur les plus-values du compte-titres
FICHIER_PF = "portefeuille.json"
FICHIER_HIST = "historique.json"


# ============================================================================
# Stockage dans un dépôt GitHub privé
# ============================================================================

class Stockage:
    def __init__(self, repo=None, token=None):
        self.repo, self.token = (repo or "").strip(), (token or "").strip()
        self.sha = {}

    @property
    def actif(self):
        return bool(self.repo and self.token)

    def _req(self, chemin, methode="GET", corps=None):
        url = f"https://api.github.com/repos/{self.repo}/contents/{chemin}"
        req = urllib.request.Request(url, method=methode, data=json.dumps(corps).encode() if corps else None,
                                     headers={"Authorization": f"Bearer {self.token}",
                                              "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "radar-actions"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def lire(self, chemin, defaut):
        try:
            j = self._req(chemin)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.sha.pop(chemin, None)
                return defaut
            raise RuntimeError(f"GitHub a refusé la lecture ({e.code}) : vérifie le jeton et le nom du dépôt") from None
        self.sha[chemin] = j["sha"]
        return json.loads(base64.b64decode(j["content"]).decode("utf-8"))

    def ecrire(self, chemin, donnees, message):
        corps = {"message": message,
                 "content": base64.b64encode(json.dumps(donnees, ensure_ascii=False, indent=1).encode("utf-8")).decode()}
        if chemin in self.sha:
            corps["sha"] = self.sha[chemin]
        try:
            j = self._req(chemin, "PUT", corps)
        except urllib.error.HTTPError as e:
            if e.code in (409, 422):        # fichier modifié entre-temps : on relit le sha et on réessaie
                self.lire(chemin, None)
                if chemin in self.sha:
                    corps["sha"] = self.sha[chemin]
                j = self._req(chemin, "PUT", corps)
            else:
                raise RuntimeError(f"GitHub a refusé l'écriture ({e.code}) : le jeton doit avoir le droit "
                                   "« Contents : Read and write » sur ce dépôt") from None
        self.sha[chemin] = j["content"]["sha"]


def portefeuille_vide():
    return {"positions": [], "ventes": []}


def nouvelle_position(ticker, nom, compte, prix_achat, quantite, date, stop=None, style="valeur"):
    return {"id": uuid.uuid4().hex[:8], "ticker": ticker, "nom": nom, "compte": compte,
            "prix_achat": float(prix_achat), "quantite": float(quantite), "date": str(date),
            "stop": float(stop) if stop else None, "style": style, "moitie_vendue": False}


# ============================================================================
# Avis sur une position
# ============================================================================

AVIS = {  # ordre de gravité, couleur
    "Vendre": "#c62828", "Alléger": "#d58a00", "Surveiller": "#1f4f99", "Garder": "#17663a", "Renforcer possible": "#0d5c2e",
}


def avis_position(pos, df, m=None):
    """pos : la position ; df : cours OHLC ; m : analyse complète de radar_actions (ou None).
    Retourne l'avis, les raisons et les chiffres utiles."""
    df = df.dropna(subset=["Close"])
    c = df.Close
    prix = float(c.iloc[-1])
    pa = pos["prix_achat"]
    a = ra.atr(df)
    atr_now = float(a.iloc[-1])
    debut = pd.Timestamp(pos["date"])
    avant = a[a.index <= debut]
    atr_achat = float(avant.iloc[-1]) if len(avant) else atr_now
    stop_init = pos.get("stop") or max(pa - 2 * atr_achat, pa * 0.88)
    depuis = df[df.index >= debut]
    plus_haut = float(max(depuis.High.max(), pa)) if len(depuis) else max(prix, pa)
    stop_suiveur = max(stop_init, plus_haut - 3 * atr_now)
    if pos.get("moitie_vendue"):
        stop_suiveur = max(stop_suiveur, pa)          # après la prise de bénéfices : on ne repasse pas en perte
    risque_unitaire = max(pa - stop_init, 1e-9)
    gain = prix / pa - 1
    gain_r = (prix - pa) / risque_unitaire
    ma50 = c.rolling(50).mean()
    sous_ma50 = bool(prix < ma50.iloc[-1])
    ma50_baisse = bool(ma50.iloc[-1] < ma50.iloc[-11])
    style = pos.get("style", "valeur")
    note = None
    if m:
        note = (m.get("styles", {}).get(style) or {}).get("note", m.get("note"))
    raisons, avis = [], "Garder"

    surchauffe = m and (m.get("z5", 0) > 2.5 or m.get("ext_atr", 0) > 4 or m.get("rsi", 0) > 80)
    res = ((m or {}).get("fonda") or {}).get("prochains_resultats")
    jours_res = None
    if isinstance(res, str) and res:
        try:
            jours_res = (pd.Timestamp(res) - pd.Timestamp.today().normalize()).days
        except Exception:
            pass

    if prix <= stop_suiveur:
        avis = "Vendre"
        raisons.append(f"Le cours ({prix:.2f}) est passé sous le stop suiveur ({stop_suiveur:.2f}) : la règle dit de sortir, "
                       "sans attendre un rebond" + (f" (tu sécurises {gain:+.1%})" if gain > 0 else ""))
    elif sous_ma50 and ma50_baisse and gain < 0:
        avis = "Vendre"
        raisons.append("Sous sa moyenne 50 jours qui baisse, et en perte : la tendance joue contre toi")
    elif note is not None and note < 35 and gain < 0:
        avis = "Vendre"
        raisons.append(f"La note est tombée à {note:.0f}/100 et la position est en perte : les raisons de l'achat ont disparu")
    elif gain_r >= 2 and not pos.get("moitie_vendue"):
        avis = "Alléger"
        raisons.append(f"Gain de {gain:+.1%}, soit {gain_r:.1f} fois le risque pris : vendre la moitié pour sécuriser, "
                       "puis coche « moitié vendue »")
    elif surchauffe and gain > 0:
        avis = "Alléger"
        raisons.append("Hausse trop rapide (surchauffe) : prendre une partie des bénéfices, les excès se corrigent souvent")
    elif note is not None and note < 45:
        avis = "Alléger"
        raisons.append(f"Note en baisse ({note:.0f}/100) : le dossier est moins attractif qu'avant")
    elif jours_res is not None and 0 <= jours_res <= 7:
        avis = "Surveiller"
        raisons.append(f"Résultats dans {jours_res} jour{'s' if jours_res > 1 else ''} ({res}) : risque de gros écart de cours")
    elif sous_ma50:
        avis = "Surveiller"
        raisons.append("Repassé sous sa moyenne 50 jours : tant que le stop tient, on garde, mais la dynamique faiblit")
    else:
        avis = "Renforcer possible" if (note is not None and note >= 70 and gain > 0) else "Garder"
        raisons.append(f"Au-dessus du stop suiveur ({stop_suiveur:.2f})" + (" et de la moyenne 50 jours" if not sous_ma50 else "")
                       + " : rien ne justifie de vendre, laisse courir")
        if avis == "Renforcer possible":
            raisons.append(f"Note élevée ({note:.0f}/100) : tu peux renforcer si la ligne reste raisonnable dans ton portefeuille")

    if jours_res is not None and 0 <= jours_res <= 7 and avis != "Surveiller":
        raisons.append(f"Attention : résultats le {res}")
    if m:
        raisons += [f"+ {x}" for x in m.get("positifs", [])[:3]]
        raisons += [f"− {x}" for x in m.get("negatifs", [])[:3]]
    q = pos["quantite"]
    pnl = (prix - pa) * q
    impot = FLAT_TAX * pnl if (pos.get("compte") == "CTO" and pnl > 0) else 0.0
    return {"avis": avis, "raisons": raisons, "prix": prix, "gain": gain, "gain_r": gain_r, "pnl": pnl,
            "impot": impot, "valeur": prix * q, "stop_suiveur": stop_suiveur, "stop_initial": stop_init,
            "plus_haut": plus_haut, "note": note, "verdict": (m or {}).get("verdict"), "devise": ra.devise_de(pos["ticker"]),
            "date": c.index[-1].date().isoformat()}


def evaluer(pf, opts, data_fn=None, meteo=None):
    """Analyse toutes les positions. data_fn(tickers, annees) -> dict de DataFrames (l'appli met en cache)."""
    pos = pf.get("positions", [])
    if not pos:
        return []
    plus_ancien = min(pd.Timestamp(p["date"]) for p in pos)
    annees = max(3.0, (pd.Timestamp.today() - plus_ancien).days / 365.25 + 1.5)
    tickers = sorted({p["ticker"] for p in pos})
    data = (data_fn or (lambda tk, an: ra.telecharger(tk, annees=an, demo=opts.demo)))(tuple(tickers + ra.INDICES_AUX), annees)
    reg = {i: ra.regime_marche(data, i) for i in ra.TOUS_INDICES}
    analyses = {}
    for t in tickers:
        if t not in data:
            continue
        iu = ra.infos_univers(t)
        try:
            m = ra.analyser(t, t, data[t], data.get(ra.indice_de(t)), opts, secteur=iu.get("secteur") or None,
                           region=iu.get("region") or None)
        except Exception:
            m = None
        if m:
            ra.ajuster_regime(m, reg[ra.indice_de(t)], ra.macro_de(meteo, t))
        analyses[t] = m
    lignes = []
    for p in pos:
        t = p["ticker"]
        if t not in data:
            lignes.append({"pos": p, "erreur": f"Pas de cours pour {t}"})
            continue
        m = analyses.get(t)
        if m:
            m = ra.appliquer_style(dict(m), p.get("style", "valeur"))
        lignes.append({"pos": p, "m": m, **avis_position(p, data[t], m)})
    return lignes


def ajouter_historique(hist, lignes, date=None):
    """Ajoute (ou remplace) le point du jour pour chaque position."""
    for l in lignes:
        if "erreur" in l:
            continue
        cle = l["pos"]["id"]
        pts = [x for x in hist.get(cle, []) if x["date"] != (date or l["date"])]
        pts.append({"date": date or l["date"], "prix": round(l["prix"], 4),
                    "note": None if l["note"] is None else round(l["note"], 1),
                    "avis": l["avis"], "stop": round(l["stop_suiveur"], 4), "gain": round(l["gain"], 4)})
        hist[cle] = sorted(pts, key=lambda x: x["date"])[-400:]
    return hist


# ============================================================================
# Affichage HTML
# ============================================================================

def _n(x, signe=False):
    """Nombre avec espaces pour les milliers (sans toucher aux virgules du texte)."""
    return (f"{x:+,.0f}" if signe else f"{x:,.0f}").replace(",", " ")


def _badge_avis(a):
    return (f'<span class="badge" style="background:{AVIS.get(a, "#555")}1a;color:{AVIS.get(a, "#555")};'
            f'border:1px solid {AVIS.get(a, "#555")}55">{a}</span>')


def html_resume(lignes):
    import html as h
    tot_val = sum(l.get("valeur", 0) for l in lignes if "erreur" not in l)
    tot_pnl = sum(l.get("pnl", 0) for l in lignes if "erreur" not in l)
    tot_imp = sum(l.get("impot", 0) for l in lignes if "erreur" not in l)
    out = [f"<div class='grid'><div class='kpi'><span>Valeur des positions</span><b>{_n(tot_val)}</b></div>"
           f"<div class='kpi'><span>Plus ou moins-value latente</span><b style='color:{'#17663a' if tot_pnl >= 0 else '#c62828'}'>"
           f"{_n(tot_pnl, True)}</b></div><div class='kpi'><span>Impôt estimé si tu vends les lignes CTO en gain (31,4 %)</span>"
           f"<b>{_n(tot_imp)}</b></div></div>"]
    out.append("<table><tr><th>Action</th><th>Compte</th><th>Prix d'achat</th><th>Cours</th><th>Résultat</th>"
               "<th>Note</th><th>Avis du jour</th><th>Stop suiveur</th></tr>")
    ordre = list(AVIS)
    for l in sorted(lignes, key=lambda l: ordre.index(l.get("avis", "Garder")) if "erreur" not in l else -1):
        p = l["pos"]
        if "erreur" in l:
            out.append(f"<tr><td><b>{h.escape(p['nom'])}</b></td><td colspan=7>{h.escape(l['erreur'])}</td></tr>")
            continue
        out.append(f"<tr><td><b>{h.escape(p['nom'])}</b><br><span class='muted'>{p['ticker']}</span></td><td>{p['compte']}</td>"
                   f"<td>{p['prix_achat']:.2f}</td><td>{l['prix']:.2f}</td>"
                   f"<td style='color:{'#17663a' if l['gain'] >= 0 else '#c62828'}'><b>{l['gain']:+.1%}</b><br>"
                   f"<span class='small'>{_n(l['pnl'], True)} {l['devise']}</span></td>"
                   f"<td>{ra._bar(l['note'])}</td><td>{_badge_avis(l['avis'])}</td><td>{l['stop_suiveur']:.2f}</td></tr>")
    out.append("</table>")
    return "".join(out)


def html_detail(l):
    import html as h
    p = l["pos"]
    items = "".join(f"<li>{h.escape(r)}</li>" for r in l["raisons"])
    fisc = (f"Si tu vends tout : impôt estimé {_n(l['impot'])} (flat tax 31,4 %)." if p["compte"] == "CTO" and l["pnl"] > 0
            else "Dans le PEA : pas d'impôt tant que l'argent reste dans l'enveloppe." if p["compte"] == "PEA" else "")
    return (f"<div class='card'><div style='display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px'>"
            f"<div><b>{h.escape(p['nom'])}</b> <span class='muted'>{p['ticker']} · {p['compte']} · acheté le {p['date']}"
            f" · {p['quantite']:g} titres à {p['prix_achat']:.2f}</span></div><div>{_badge_avis(l['avis'])}</div></div>"
            f"<ul>{items}</ul><div class='plan'>Stop de départ {l['stop_initial']:.2f} · plus haut depuis l'achat {l['plus_haut']:.2f}"
            f" · stop suiveur aujourd'hui <b>{l['stop_suiveur']:.2f}</b> (3 ATR sous le plus haut, ne descend jamais)"
            f" · gain {l['gain_r']:+.1f} R. {fisc}</div></div>")


# ============================================================================
# Ligne de commande : suivi quotidien
# ============================================================================

def suivi():
    st = Stockage(os.environ.get("PORTEFEUILLE_REPO"), os.environ.get("PORTEFEUILLE_TOKEN"))
    if not st.actif:
        print("Suivi du portefeuille ignoré : PORTEFEUILLE_REPO / PORTEFEUILLE_TOKEN non configurés.")
        return
    pf = st.lire(FICHIER_PF, portefeuille_vide())
    if not pf.get("positions"):
        print("Portefeuille vide.")
        return
    res = os.path.join("resultats", "resultats.json.gz")
    if os.path.exists(res):
        try:
            ra.charger_resultats(res)            # récupère les médianes de valorisation du jour
        except Exception:
            pass
    opts = types.SimpleNamespace(capital=10000, risque=1.0, objectif=20, horizon=40, demo=False, style="valeur")
    lignes = evaluer(pf, opts, meteo=ra.meteo_macro())
    hist = st.lire(FICHIER_HIST, {})
    hist = ajouter_historique(hist, lignes)
    st.ecrire(FICHIER_HIST, hist, f"Suivi du {dt.date.today().isoformat()}")
    # Pas de détail dans le journal : les journaux GitHub Actions d'un dépôt public sont visibles par tous
    print(f"Suivi enregistré pour {sum('erreur' not in l for l in lignes)} position(s).")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "suivi":
        suivi()
    else:
        print(__doc__)
