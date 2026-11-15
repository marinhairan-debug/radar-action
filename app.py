# -*- coding: utf-8 -*-
"""
Radar actions — version web (Streamlit).

Le gros calcul (5 000+ actions) est fait chaque nuit par GitHub Actions (radar_actions.py preparer).
L'appli lit simplement le résultat : elle s'ouvre en quelques secondes, depuis n'importe quel PC.
"""
import os
import types

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Radar actions", page_icon="📈", layout="wide")


def secret(nom, defaut=""):
    try:
        return st.secrets.get(nom, defaut) or defaut
    except Exception:
        return os.environ.get(nom, defaut)


if secret("EODHD_API_KEY"):
    os.environ["EODHD_API_KEY"] = secret("EODHD_API_KEY")

import radar_actions as ra  # noqa: E402
import macro  # noqa: E402

DEMO = os.environ.get("RADAR_DEMO") == "1"
SOURCE = secret("RESULTATS_URL") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultats", "resultats.json.gz")

# ---------------------------------------------------------------- mot de passe
mdp = secret("MOT_DE_PASSE")
if mdp and not st.session_state.get("ok"):
    st.title("📈 Radar actions")
    saisie = st.text_input("Mot de passe", type="password")
    if saisie == mdp:
        st.session_state.ok = True
        st.rerun()
    elif saisie:
        st.error("Mot de passe incorrect")
    st.stop()


# ---------------------------------------------------------------- données
@st.cache_data(ttl=1800, show_spinner=False)
def resultats(source):
    try:
        return ra.charger_resultats(source)
    except Exception as e:
        return {"erreur": str(e)}


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def donnees(tickers, annees=10):
    return ra.telecharger(list(tickers), annees=annees, demo=DEMO)


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def meteo_live():
    return ra.meteo_macro(DEMO)


@st.cache_data(show_spinner=False)
def univers_df():
    return ra._lire_univers()


def afficher(corps, regimes=None):
    st.html(f"<style>{ra.CSS} .wrap{{padding:0}}</style><div class='wrap'>{ra.html_regimes(regimes or [])}{corps}</div>")


R = resultats(SOURCE)
pret = "erreur" not in R
U = univers_df()

# ---------------------------------------------------------------- barre latérale
with st.sidebar:
    st.header("⚙️ Réglages")
    univers = st.selectbox("Univers", list(ra.UNIVERS_CHOIX),
                           format_func=lambda c: f"{ra.UNIVERS_CHOIX[c]} ({len(ra.filtrer_univers(U, c))})" if U is not None else ra.UNIVERS_CHOIX[c])
    tailles = st.multiselect("Taille des sociétés", ["Géante", "Grande", "Moyenne", "Petite"],
                             default=["Géante", "Grande", "Moyenne", "Petite"])
    secteurs_dispo = sorted(x for x in U.secteur.unique() if x) if U is not None else []
    secteurs = st.multiselect("Secteurs (vide = tous)", secteurs_dispo, default=[])
    capital = st.number_input("Capital (€)", 500, 10_000_000, 10_000, step=500)
    risque = st.slider("Risque par trade (% du capital)", 0.25, 3.0, 1.0, 0.25)
    top = st.slider("Nombre d'actions dans le classement", 5, 40, 15)
    st.divider()
    if pret:
        st.caption(f"Calcul du **{R['date']}** · {R['n_notees']} actions notées sur {R['n_univers']}. "
                   "Recalculé automatiquement chaque soir de bourse.")
    else:
        st.caption("Pas encore de calcul nocturne disponible : mode direct sur la liste courte.")
    if st.button("🔄 Recharger"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Outil d'aide à la décision, pas un conseil en investissement.")

params = R.get("params", {}) if pret else {}
opts = types.SimpleNamespace(univers=univers, top=top, capital=capital, risque=risque,
                             objectif=params.get("objectif", 20), horizon=params.get("horizon", 40), demo=DEMO, debut="2012-01-01")

st.title("📈 Radar actions")
o_macro, o_class, o_analyse, o_bt = st.tabs(["🌍 Météo économique", "📊 Classement du jour",
                                             "🔎 Analyser mes actions", "🧪 Vérifier le score"])

# ---------------------------------------------------------------- macro
with o_macro:
    mt = R.get("meteo") if pret else None
    if not mt:
        with st.spinner("Lecture des indicateurs économiques (FRED)…"):
            mt = meteo_live()
    afficher(macro.html_meteo(mt)) if mt else st.warning("Données macro indisponibles pour le moment.")

# ---------------------------------------------------------------- classement
with o_class:
    if pret:
        fin = pd.DataFrame([{k: m.get(k) for k in ("ticker", "region", "pea", "secteur", "taille")} for m in R["finalistes"]])
        if U is not None and len(fin):
            fin["coeur"] = fin.ticker.map(dict(zip(U.ticker, U.coeur))).fillna("0")
        garde = set(ra.filtrer_univers(fin, univers).ticker) if len(fin) else set()
        sel = [ra.recalculer_taille(dict(m), capital, risque) for m in R["finalistes"]
               if m["ticker"] in garde and (m.get("taille") in tailles or not m.get("taille"))
               and (not secteurs or m.get("secteur") in secteurs)]
        sel.sort(key=lambda m: -m["note"])
        regimes = [R["regimes"][i] for i in ([ra.INDICE_EUROPE] if univers in ("pea", "europe") else
                                             [ra.INDICE_US] if univers == "us" else [ra.INDICE_EUROPE, ra.INDICE_US])]
        if not sel:
            st.info("Aucune action pour ce filtre.")
        else:
            afficher(ra.html_scan({"top": sel[:top], "regimes": regimes, "meteo": None}, opts), regimes)
        with st.expander(f"📋 Toutes les actions notées ({univers}) — tri et export"):
            tab = R["table"].copy()
            if U is not None:
                tab["coeur"] = tab.ticker.map(dict(zip(U.ticker, U.coeur))).fillna("0")
            tab = ra.filtrer_univers(tab, univers)
            tab = tab[tab.taille.isin(tailles) | (tab.taille == "")]
            if secteurs:
                tab = tab[tab.secteur.isin(secteurs)]
            cols = ["ticker", "nom", "note", "verdict", "taille", "secteur", "pays", "prix", "r6m", "r12_1", "dist52", "vol", "rsi"]
            vue = tab[cols].sort_values("note", ascending=False)
            st.dataframe(vue, hide_index=True)
            st.download_button("⬇️ Télécharger (Excel/CSV)", vue.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
                               "toutes_les_actions.csv", "text/csv")
            st.caption("Note rapide (cours et volumes). Probabilités et fondamentaux seulement pour les meilleures, "
                       "ou à la demande dans l'onglet « Analyser mes actions ».")
    else:
        st.warning("Le calcul nocturne n'est pas encore en place (voir LISEZMOI.md, étape GitHub Actions). "
                   "En attendant, classement en direct sur la liste courte (≈ 1 000 valeurs).")
        if st.button("Lancer le classement en direct"):
            with st.spinner("Téléchargement et calcul… (quelques minutes)"):
                o = types.SimpleNamespace(**{**vars(opts), "univers": "coeur" if univers in ("tout", "petites") else univers})
                univ = ra.charger_univers(o.univers)
                if univers != "coeur" and U is not None:
                    univ = {t: n for t, n in univ.items() if t in set(U[U.coeur == "1"].ticker)}
                data = donnees(tuple(list(univ) + ra.INDICES_AUX))
                r = ra.scan(o, data=data, meteo=meteo_live())
            afficher(ra.html_scan(r, o), r["regimes"])

# ---------------------------------------------------------------- analyse à la demande
with o_analyse:
    st.write("Propose une ou plusieurs actions : ticker Yahoo (**NVDA**, **MC.PA**, **SAP.DE**, **ASML.AS**…) "
             "ou nom (**Schneider Electric**), séparés par des virgules.")
    saisie = st.text_input("Actions à analyser", placeholder="NVDA, ASML.AS, Schneider Electric")
    if st.button("Analyser", type="primary") and saisie.strip():
        requetes = [x.strip() for x in saisie.split(",") if x.strip()]
        with st.spinner("Analyse en cours…"):
            res = ra.analyse(opts, requetes, data_fn=lambda tk: donnees(tuple(tk)), meteo=mt)
        for e in res["erreurs"]:
            st.warning(e)
        if res["actions"]:
            afficher(ra.html_analyse(res, opts), res["regimes"])

# ---------------------------------------------------------------- backtest
with o_bt:
    st.write("Rejoue le score depuis 2012 sur la liste courte : chaque fin de mois, achat des 15 meilleures actions à poids égal, "
             "liquidités quand l'indice est sous sa moyenne 200 jours, frais inclus. "
             "Si le score ne bat pas nettement l'indice **et** « toutes les actions à poids égal », il n'apporte rien.")
    b = R.get("backtest") if pret else None
    if b:
        st.caption("Backtest recalculé automatiquement chaque samedi.")
        afficher(ra.html_backtest(b))
    elif st.button("Lancer le backtest (quelques minutes)"):
        with st.spinner("Calcul sur 15 ans d'historique…"):
            try:
                o = types.SimpleNamespace(**{**vars(opts), "univers": "coeur", "top": 15})
                univ = ra.charger_univers("coeur")
                data = donnees(tuple(list(univ) + [ra.INDICE_US]), annees=16)
                afficher(ra.html_backtest(ra.backtest(o, data=data)))
            except Exception as e:
                st.error(f"Backtest impossible : {e}")
