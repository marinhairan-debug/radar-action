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
import portefeuille as pfm  # noqa: E402

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
    style = st.radio("Ce que je cherche", list(ra.STYLES),
                     format_func=lambda k: {"valeur": "🔄 Actions sous-cotées qui se retournent",
                                            "momentum": "🚀 Actions déjà en forte tendance"}[k])
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
opts = types.SimpleNamespace(univers=univers, top=top, capital=capital, risque=risque, style=style,
                             objectif=params.get("objectif", 20), horizon=params.get("horizon", 40), demo=DEMO, debut="2012-01-01")

st.title("📈 Radar actions")
o_macro, o_class, o_pf, o_analyse, o_bt = st.tabs(["🌍 Météo économique", "📊 Classement du jour", "💼 Mon portefeuille",
                                                   "🔎 Analyser une action", "🧪 Vérifier le score"])

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
        if style == "valeur" and not any("valeur" in m.get("styles", {}) for m in R["finalistes"]):
            st.info("Le calcul de cette nuit date d'avant le nouveau score « sous-cotées ». Relance le calcul dans GitHub "
                    "(Actions → Radar actions → Run workflow) ou attends ce soir. En attendant : classement momentum.")
        fin = pd.DataFrame([{k: m.get(k, "") for k in ("ticker", "region", "pea", "cto", "secteur", "taille")} for m in R["finalistes"]])
        if U is not None and len(fin):
            fin["coeur"] = fin.ticker.map(dict(zip(U.ticker, U.coeur))).fillna("0")
        garde = set(ra.filtrer_univers(fin, univers).ticker) if len(fin) else set()
        sel = [ra.recalculer_taille(ra.appliquer_style(dict(m), style), capital, risque) for m in R["finalistes"]
               if m["ticker"] in garde and (m.get("taille") in tailles or not m.get("taille"))
               and (not secteurs or m.get("secteur") in secteurs)]
        sel.sort(key=lambda m: -m["note"])
        regimes = [R["regimes"][i] for i in ra.indices_de_univers(univers)
                   if i in R["regimes"] and (R["regimes"][i].get("etat") != "inconnu" or i in (ra.INDICE_EUROPE, ra.INDICE_US))]
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
            tab["note"] = tab["note_" + style]
            cols = [c for c in ["ticker", "nom", "note", "note_valeur", "note_momentum", "taille", "secteur", "pays", "prix",
                                "per", "pb", "dist52", "r2a", "r6m", "r12_1", "vol", "rsi", "pea", "cto"] if c in tab]
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

# ---------------------------------------------------------------- portefeuille
def onglet_portefeuille():
    stock = pfm.Stockage(secret("PORTEFEUILLE_REPO"), secret("PORTEFEUILLE_TOKEN"))
    if stock.actif and not mdp:
        st.error("Ton portefeuille est enregistré dans GitHub, mais l'appli n'a pas de mot de passe : n'importe qui "
                 "ayant le lien pourrait le voir. Ajoute MOT_DE_PASSE dans les secrets Streamlit (voir LISEZMOI, étape 4).")
        return
    if "pf" not in st.session_state:
        st.session_state.pf, st.session_state.hist = pfm.portefeuille_vide(), {}
        if stock.actif:
            try:
                st.session_state.pf = stock.lire(pfm.FICHIER_PF, pfm.portefeuille_vide())
                st.session_state.hist = stock.lire(pfm.FICHIER_HIST, {})
            except Exception as e:
                st.error(f"Lecture du portefeuille impossible : {e}")
    pf, hist = st.session_state.pf, st.session_state.hist

    def sauver(message):
        if stock.actif:
            try:
                stock.ecrire(pfm.FICHIER_PF, pf, message)
            except Exception as e:
                st.error(f"Enregistrement impossible : {e}")

    if not stock.actif:
        st.info("Mode temporaire : le portefeuille est perdu quand tu fermes la page (sauf si tu le télécharges). "
                "Pour qu'il soit gardé automatiquement et suivi chaque soir, suis l'étape 4 du LISEZMOI (5 minutes).")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ Télécharger mon portefeuille", pfm.json.dumps(pf, ensure_ascii=False, indent=1),
                           "portefeuille.json", "application/json")
        fic = c2.file_uploader("Recharger un portefeuille.json", type="json")
        if fic is not None and st.session_state.get("fic_charge") != fic.name + str(fic.size):
            st.session_state.pf = pf = pfm.json.loads(fic.read().decode("utf-8"))
            st.session_state.fic_charge = fic.name + str(fic.size)

    with st.expander("➕ Ajouter une action que j'ai achetée", expanded=not pf["positions"]):
        with st.form("ajout", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            action = c1.text_input("Action (ticker Yahoo ou nom)", placeholder="MC.PA, NVDA, Schneider…")
            compte = c2.selectbox("Compte", ["PEA", "CTO"], help="PEA BoursoBank ou compte-titres Trade Republic")
            date_achat = c3.date_input("Date d'achat", pd.Timestamp.today().date(), max_value=pd.Timestamp.today().date(),
                                       format="DD/MM/YYYY")
            prix_achat = c1.number_input("Prix d'achat par titre (frais compris)", min_value=0.0, step=0.01, format="%.2f")
            quantite = c2.number_input("Quantité", min_value=0.0, step=1.0)
            stop_saisi = c3.number_input("Stop (0 = calcul automatique)", min_value=0.0, step=0.01, format="%.2f")
            style_pos = st.radio("Pourquoi tu l'as achetée ?", list(ra.STYLES), horizontal=True,
                                 format_func=lambda k: {"valeur": "Sous-cotée qui se retourne", "momentum": "Déjà en tendance"}[k],
                                 help="Choisit la note qui sert à suivre la position")
            if st.form_submit_button("Ajouter", type="primary"):
                if not action.strip() or prix_achat <= 0 or quantite <= 0:
                    st.warning("Indique l'action, le prix d'achat et la quantité.")
                else:
                    t, nom = ra.resoudre(action, DEMO)
                    iu = ra.infos_univers(t)
                    pf["positions"].append(pfm.nouvelle_position(t, iu.get("nom") or nom, compte, prix_achat, quantite,
                                                                 date_achat, stop_saisi or None, style_pos))
                    sauver(f"Ajout {t}")
                    st.rerun()

    if pf["positions"]:
        with st.spinner("Analyse de tes positions…"):
            lignes = pfm.evaluer(pf, opts, data_fn=lambda tk, an: donnees(tk, round(an, 1)), meteo=mt)
        st.caption("Avis recalculé à chaque ouverture avec les derniers cours (et enregistré chaque soir si le suivi est configuré). "
                   "Règles : stop suiveur à 3 ATR sous le plus haut, moitié vendue à 2× le risque, sortie si la tendance casse.")
        afficher(pfm.html_resume(lignes))
        n_avant = sum(len(v) for v in hist.values())
        hist = st.session_state.hist = pfm.ajouter_historique(hist, lignes)
        if stock.actif and sum(len(v) for v in hist.values()) > n_avant:
            try:
                stock.ecrire(pfm.FICHIER_HIST, hist, "Suivi depuis l'appli")
            except Exception:
                pass
        for l in lignes:
            p = l["pos"]
            with st.expander(f"{l.get('avis', '?')} — {p['nom']} ({p['ticker']}, {p['compte']})"):
                if "erreur" in l:
                    st.warning(l["erreur"])
                else:
                    afficher(pfm.html_detail(l))
                    h = pd.DataFrame(hist.get(p["id"], []))
                    if len(h) > 1:
                        h["date"] = pd.to_datetime(h["date"])
                        h = h.set_index("date")
                        g1, g2 = st.columns(2)
                        g1.caption("Cours et stop suiveur")
                        g1.line_chart(h[["prix", "stop"]])
                        g2.caption("Note au fil des jours")
                        g2.line_chart(h[["note"]])
                    else:
                        st.caption("L'historique de la note se remplira jour après jour.")
                c1, c2, c3 = st.columns(3)
                mv = c1.checkbox("Moitié déjà vendue", value=p.get("moitie_vendue", False), key="mv" + p["id"],
                                 help="Le stop remonte alors au prix d'achat : la position ne peut plus finir en perte")
                if mv != p.get("moitie_vendue", False):
                    p["moitie_vendue"] = mv
                    sauver(f"Mise à jour {p['ticker']}")
                    st.rerun()
                nq = c2.number_input("Quantité détenue", min_value=0.0, value=float(p["quantite"]), step=1.0, key="q" + p["id"])
                if c2.button("Mettre à jour la quantité", key="bq" + p["id"]) and nq != p["quantite"]:
                    p["quantite"] = nq
                    sauver(f"Quantité {p['ticker']}")
                    st.rerun()
                pv = c3.number_input("Prix de vente", min_value=0.0, value=float(l.get("prix", 0)), step=0.01,
                                     format="%.2f", key="pv" + p["id"])
                if c3.button("✅ J'ai tout vendu", key="bv" + p["id"]):
                    pf["positions"] = [x for x in pf["positions"] if x["id"] != p["id"]]
                    pf.setdefault("ventes", []).append({**p, "prix_vente": pv, "date_vente": str(pd.Timestamp.today().date()),
                                                        "resultat": (pv - p["prix_achat"]) * p["quantite"]})
                    sauver(f"Vente {p['ticker']}")
                    st.rerun()
    if pf.get("ventes"):
        with st.expander(f"📜 Positions vendues ({len(pf['ventes'])})"):
            v = pd.DataFrame(pf["ventes"])[["nom", "ticker", "compte", "date", "prix_achat", "date_vente", "prix_vente",
                                             "quantite", "resultat"]]
            st.dataframe(v, hide_index=True)
            st.write(f"Résultat réalisé total : **{v.resultat.sum():+,.0f}** (avant impôt pour le CTO)".replace(",", " "))


with o_pf:
    onglet_portefeuille()

# ---------------------------------------------------------------- analyse à la demande
with o_analyse:
    st.write("Propose une ou plusieurs actions : ticker Yahoo (**NVDA**, **MC.PA**, **SAP.DE**, **ASML.AS**, **6857.T** pour Advantest, "
             "**000660.KS** pour SK Hynix…) "
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
    st.write("⚠️ Seule la partie « cours et volumes » du score peut être testée : l'historique des fondamentaux "
             "(PER, dettes…) n'existe pas gratuitement. Pour le style « sous-cotées », le test porte donc sur la décote, "
             "le retour à la moyenne sur 2 ans et les signaux de retournement.")
    b = R.get("backtest") if pret else None
    if b:
        st.caption("Backtest recalculé automatiquement chaque samedi.")
        for k in ([style] + [x for x in b if x != style]):
            if k in b:
                afficher(ra.html_backtest(b[k]))
    elif st.button("Lancer le backtest (quelques minutes)"):
        with st.spinner("Calcul sur 15 ans d'historique…"):
            try:
                o = types.SimpleNamespace(**{**vars(opts), "univers": "coeur", "top": 15, "style": style})
                univ = ra.charger_univers("coeur")
                data = donnees(tuple(list(univ) + [ra.INDICE_US]), annees=16)
                afficher(ra.html_backtest(ra.backtest(o, data=data)))
            except Exception as e:
                st.error(f"Backtest impossible : {e}")
