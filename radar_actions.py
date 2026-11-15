#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RADAR ACTIONS — sélection quantitative d'actions pour le swing trading
=====================================================================

Trois commandes :

  python radar_actions.py scan
        Classe chaque soir les actions de l'univers (PEA + US par défaut)
        et produit un rapport HTML avec le top, les raisons et un plan de trade.

  python radar_actions.py analyse NVDA ASML.AS "Schneider Electric"
        Donne un avis détaillé sur les actions que TU proposes
        (tendance, statistiques, probabilités, saisonnalité, fondamentaux, plan).

  python radar_actions.py backtest
        Vérifie sur l'historique si le score a réellement battu l'indice.

Options utiles :
  --univers pea | europe | us | tout | mon_fichier.txt   (≈ 1 000 actions au total, voir univers.csv)
  --top 20            nombre d'actions dans le rapport
  --capital 10000     capital en € pour le calcul des tailles de position
  --risque 1          % du capital risqué par trade
  --objectif 20       objectif de gain en % pour le calcul de probabilité
  --horizon 40        horizon en jours de bourse pour la probabilité

Installation (une seule fois) :  pip install yfinance pandas numpy
Données : Yahoo Finance (gratuit). Ce n'est pas un conseil en investissement.
"""

import argparse
import datetime as dt
import html
import math
import os
import sys
import webbrowser

import numpy as np
import pandas as pd

# ============================================================================
# 1. UNIVERS D'ACTIONS
# ============================================================================

# Actions européennes généralement éligibles au PEA (vérifie chez ton courtier)
UNIVERS_PEA = {
    # France
    "MC.PA": "LVMH", "OR.PA": "L'Oréal", "RMS.PA": "Hermès", "TTE.PA": "TotalEnergies",
    "SAN.PA": "Sanofi", "AIR.PA": "Airbus", "SU.PA": "Schneider Electric", "AI.PA": "Air Liquide",
    "BNP.PA": "BNP Paribas", "CS.PA": "AXA", "EL.PA": "EssilorLuxottica", "SAF.PA": "Safran",
    "DG.PA": "Vinci", "KER.PA": "Kering", "RI.PA": "Pernod Ricard", "BN.PA": "Danone",
    "CAP.PA": "Capgemini", "DSY.PA": "Dassault Systèmes", "STMPA.PA": "STMicroelectronics",
    "HO.PA": "Thales", "ENGI.PA": "Engie", "ORA.PA": "Orange", "GLE.PA": "Société Générale",
    "ACA.PA": "Crédit Agricole", "SGO.PA": "Saint-Gobain", "LR.PA": "Legrand", "ML.PA": "Michelin",
    "PUB.PA": "Publicis", "VIE.PA": "Veolia", "RNO.PA": "Renault", "AM.PA": "Dassault Aviation",
    "ERF.PA": "Eurofins", "BVI.PA": "Bureau Veritas", "TEP.PA": "Teleperformance",
    "SOI.PA": "Soitec", "ALO.PA": "Alstom", "EN.PA": "Bouygues", "AC.PA": "Accor",
    "ATE.PA": "Alten", "SPIE.PA": "Spie", "EXENS.PA": "Exosens", "NEX.PA": "Nexans",
    # Allemagne
    "SAP.DE": "SAP", "SIE.DE": "Siemens", "ALV.DE": "Allianz", "DTE.DE": "Deutsche Telekom",
    "MUV2.DE": "Munich Re", "IFX.DE": "Infineon", "ADS.DE": "Adidas", "BAS.DE": "BASF",
    "BAYN.DE": "Bayer", "BMW.DE": "BMW", "MBG.DE": "Mercedes-Benz", "VOW3.DE": "Volkswagen",
    "DBK.DE": "Deutsche Bank", "DB1.DE": "Deutsche Börse", "RHM.DE": "Rheinmetall",
    "MTX.DE": "MTU Aero Engines", "ENR.DE": "Siemens Energy", "AIXA.DE": "Aixtron",
    "ZAL.DE": "Zalando", "HNR1.DE": "Hannover Re", "SHL.DE": "Siemens Healthineers",
    "HAG.DE": "Hensoldt",
    # Pays-Bas / Belgique
    "ASML.AS": "ASML", "ASM.AS": "ASM International", "BESI.AS": "BE Semiconductor",
    "ADYEN.AS": "Adyen", "PRX.AS": "Prosus", "INGA.AS": "ING", "AD.AS": "Ahold Delhaize",
    "HEIA.AS": "Heineken", "WKL.AS": "Wolters Kluwer", "ABI.BR": "AB InBev", "UCB.BR": "UCB",
    # Italie / Espagne / Nord
    "ENEL.MI": "Enel", "ENI.MI": "Eni", "ISP.MI": "Intesa Sanpaolo", "UCG.MI": "UniCredit",
    "RACE.MI": "Ferrari", "LDO.MI": "Leonardo", "PRY.MI": "Prysmian",
    "SAN.MC": "Banco Santander", "IBE.MC": "Iberdrola", "ITX.MC": "Inditex", "BBVA.MC": "BBVA",
    "NOKIA.HE": "Nokia", "NOVO-B.CO": "Novo Nordisk",
}

# Actions américaines (compte-titres)
UNIVERS_US = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "META": "Meta", "TSLA": "Tesla", "AVGO": "Broadcom", "AMD": "AMD", "ORCL": "Oracle",
    "CRM": "Salesforce", "ADBE": "Adobe", "NFLX": "Netflix", "INTC": "Intel", "QCOM": "Qualcomm",
    "TXN": "Texas Instruments", "MU": "Micron", "AMAT": "Applied Materials", "LRCX": "Lam Research",
    "KLAC": "KLA", "SMCI": "Super Micro", "ARM": "Arm", "MRVL": "Marvell", "ON": "ON Semi",
    "PLTR": "Palantir", "SNOW": "Snowflake", "NOW": "ServiceNow", "UBER": "Uber",
    "SHOP": "Shopify", "CRWD": "CrowdStrike", "PANW": "Palo Alto", "ANET": "Arista",
    "COIN": "Coinbase", "HOOD": "Robinhood", "APP": "AppLovin", "DELL": "Dell", "SOFI": "SoFi",
    "RKLB": "Rocket Lab", "JPM": "JPMorgan", "GS": "Goldman Sachs", "BAC": "Bank of America",
    "V": "Visa", "MA": "Mastercard", "BRK-B": "Berkshire", "UNH": "UnitedHealth",
    "LLY": "Eli Lilly", "JNJ": "Johnson & Johnson", "ABBV": "AbbVie", "MRK": "Merck",
    "PFE": "Pfizer", "XOM": "Exxon", "CVX": "Chevron", "CAT": "Caterpillar", "DE": "Deere",
    "GE": "GE Aerospace", "BA": "Boeing", "LMT": "Lockheed Martin", "RTX": "RTX",
    "HD": "Home Depot", "COST": "Costco", "WMT": "Walmart", "MCD": "McDonald's", "NKE": "Nike",
    "DIS": "Disney", "KO": "Coca-Cola", "PEP": "PepsiCo", "PG": "Procter & Gamble",
    "TMO": "Thermo Fisher", "ISRG": "Intuitive Surgical", "VRTX": "Vertex", "AXON": "Axon",
    "CEG": "Constellation Energy", "VST": "Vistra", "ETN": "Eaton", "VRT": "Vertiv",
}

SUFFIXES_EUROPE = (".PA", ".DE", ".AS", ".BR", ".MI", ".MC", ".HE", ".CO", ".LS", ".VI",
                   ".IR", ".ST", ".OL", ".SW", ".L")
INDICE_EUROPE = "^STOXX"      # Stoxx Europe 600
INDICE_US = "^GSPC"           # S&P 500
VIX = "^VIX"
TAUX_10A = "^TNX"

# ============================================================================
# 2. PARAMÈTRES PAR DÉFAUT
# ============================================================================

FRAIS_ORDRE_EUR = 1.0     # Trade Republic : 1 € par ordre
SPREAD_ESTIME = 0.001     # 0,1 % d'écart de prix estimé par ordre
LIQUIDITE_MIN = 2e6       # volume moyen échangé par jour minimum (devise locale)
JOURS_MIN = 300           # historique minimum pour analyser une action

POIDS = {                 # poids des sous-scores dans la note finale
    "momentum": 0.27, "tendance": 0.18, "probabilites": 0.22,
    "volume": 0.10, "risque": 0.08, "fondamentaux": 0.15,
}

# ============================================================================
# 3. DONNÉES
# ============================================================================

def _demo_data(tickers, years=10, seed=7):
    """Données simulées réalistes (mode --demo, pour tester sans internet)."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=int(252 * years))
    out = {}
    market = rng.standard_t(4, len(idx)) * 0.009 / np.sqrt(2) + 0.0003
    for i, t in enumerate(tickers):
        beta = rng.uniform(0.6, 1.6)
        vol = rng.uniform(0.012, 0.03)
        # régimes de tendance propres à chaque action (crée du momentum)
        drift = np.repeat(rng.normal(0.0002, 0.0012, len(idx) // 120 + 1), 120)[:len(idx)]
        eps = rng.standard_t(4, len(idx)) * vol / np.sqrt(2)
        if t.startswith("^"):
            r = market + (0.0004 if t == VIX else 0)
            beta = 1
        else:
            r = beta * market + drift + eps
        close = 100 * np.exp(np.cumsum(r))
        rng_hl = np.abs(rng.normal(0, vol, len(idx))) + vol / 2
        df = pd.DataFrame({
            "Open": close * (1 + rng.normal(0, vol / 3, len(idx))),
            "High": close * (1 + rng_hl), "Low": close * (1 - rng_hl), "Close": close,
            "Volume": (rng.lognormal(13, 0.4, len(idx)) * (1 + 3 * np.abs(eps) / vol)).round(),
        }, index=idx)
        if t == VIX:
            df["Close"] = 15 + 10 * np.abs(np.sin(np.arange(len(idx)) / 90)) + rng.normal(0, 1, len(idx))
        out[t] = df
    return out


# Correspondance Yahoo -> EODHD (bourses et indices)
EODHD_BOURSES = {".PA": ".PA", ".DE": ".XETRA", ".AS": ".AS", ".BR": ".BR", ".MI": ".MI", ".MC": ".MC",
                 ".HE": ".HE", ".CO": ".CO", ".LS": ".LS", ".VI": ".VI", ".IR": ".IR", ".ST": ".ST",
                 ".OL": ".OL", ".SW": ".SW", ".L": ".LSE"}
EODHD_INDICES = {INDICE_US: "GSPC.INDX", INDICE_EUROPE: "EXSA.XETRA", VIX: "VIX.INDX", TAUX_10A: None}


def _eodhd_symbole(t):
    if t in EODHD_INDICES:
        return EODHD_INDICES[t]
    for suf, rep in EODHD_BOURSES.items():
        if t.upper().endswith(suf):
            return t[: -len(suf)] + rep
    return t + ".US"


def _telecharger_eodhd(tickers, annees, cle):
    import json
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    debut = (dt.date.today() - dt.timedelta(days=int(365.25 * annees) + 10)).isoformat()

    def un(t):
        sym = _eodhd_symbole(t)
        if not sym:
            return t, None
        url = f"https://eodhd.com/api/eod/{sym}?api_token={cle}&fmt=json&from={debut}"
        try:
            with urllib.request.urlopen(url, timeout=30) as rep:
                rows = json.loads(rep.read().decode())
            df = pd.DataFrame(rows)
            if df.empty:
                return t, None
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
            k = (df["adjusted_close"] / df["close"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
            out = pd.DataFrame({"Open": df["open"] * k, "High": df["high"] * k, "Low": df["low"] * k,
                                "Close": df["adjusted_close"], "Volume": df["volume"]})
            return t, out.dropna(subset=["Close"])
        except Exception as e:  # noqa
            print("   ! EODHD", t, e)
            return t, None

    with ThreadPoolExecutor(max_workers=8) as ex:
        return {t: df for t, df in ex.map(un, tickers) if df is not None and len(df)}


def telecharger(tickers, annees=10, demo=False, reessai=1):
    """Télécharge les cours journaliers ajustés. Retourne {ticker: DataFrame OHLCV}.
    Source : EODHD si la variable d'environnement EODHD_API_KEY existe, sinon Yahoo Finance."""
    tickers = list(dict.fromkeys(tickers))
    if demo:
        return _demo_data(tickers, annees)
    cle = os.environ.get("EODHD_API_KEY")
    if cle:
        return _telecharger_eodhd(tickers, annees, cle)
    import yfinance as yf
    debut = (dt.date.today() - dt.timedelta(days=int(365.25 * annees) + 10)).isoformat()
    out = {}
    paquet = 80
    for i in range(0, len(tickers), paquet):
        lot = tickers[i:i + paquet]
        print(f"  Téléchargement {i + 1}-{i + len(lot)} / {len(tickers)}…", flush=True)
        try:
            data = yf.download(lot, start=debut, auto_adjust=True, group_by="ticker",
                               progress=False, threads=True)
        except Exception as e:  # noqa
            print("   ! erreur de téléchargement :", e)
            continue
        if i + paquet < len(tickers):
            import time
            time.sleep(1.5)       # ménage Yahoo pour éviter d'être bloqué
        for t in lot:
            try:
                df = data[t] if isinstance(data.columns, pd.MultiIndex) else data
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
                if len(df) > 0:
                    out[t] = df
            except Exception:
                pass
    manquants = [t for t in tickers if t not in out]
    if manquants and len(manquants) < len(tickers) and reessai > 0 and len(manquants) > 0.02 * len(tickers):
        import time
        print(f"  {len(manquants)} tickers sans données, nouvel essai dans 60 s…")
        time.sleep(60)
        out.update(telecharger(manquants, annees, demo, reessai - 1))
    return out


def resoudre(requete, demo=False):
    """Transforme un nom ('Schneider') ou un ticker en ticker Yahoo."""
    q = requete.strip()
    if demo or (q.upper() == q and " " not in q):
        return q.upper(), q.upper()
    try:
        import yfinance as yf
        res = yf.Search(q, max_results=5).quotes
        for r in res:
            if r.get("quoteType") == "EQUITY":
                return r["symbol"], r.get("shortname") or r.get("longname") or r["symbol"]
    except Exception:
        pass
    return q.upper(), q


def fondamentaux(ticker, demo=False):
    """Données fondamentales Yahoo (peuvent être incomplètes)."""
    if demo:
        rng = np.random.default_rng(abs(hash(ticker)) % 2**32)
        return {"forwardPE": float(rng.uniform(8, 45)), "trailingPE": float(rng.uniform(10, 50)),
                "revenueGrowth": float(rng.normal(0.08, 0.12)), "profitMargins": float(rng.normal(0.12, 0.08)),
                "returnOnEquity": float(rng.normal(0.15, 0.1)), "debtToEquity": float(rng.uniform(10, 200)),
                "targetMeanPrice": None, "recommendationMean": float(rng.uniform(1.5, 3.5)),
                "numberOfAnalystOpinions": int(rng.integers(3, 40)), "sector": "Démo",
                "industry": "Démo", "currency": "EUR", "marketCap": float(rng.uniform(1e9, 2e11)),
                "surprise_pct": float(rng.normal(3, 8)), "prochains_resultats": None}
    info = {}
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        raw = tk.info or {}
        for k in ["longName", "shortName", "sector", "industry", "currency", "marketCap", "forwardPE",
                  "trailingPE", "priceToSalesTrailing12Months", "revenueGrowth", "earningsGrowth",
                  "profitMargins", "returnOnEquity", "debtToEquity", "targetMeanPrice",
                  "recommendationMean", "numberOfAnalystOpinions", "shortPercentOfFloat"]:
            info[k] = raw.get(k)
        try:
            ed = tk.get_earnings_dates(limit=8)
            if ed is not None and len(ed):
                ed = ed.sort_index()
                passes = ed[ed.index <= pd.Timestamp.now(tz=ed.index.tz)].dropna(subset=["Surprise(%)"])
                if len(passes):
                    info["surprise_pct"] = float(passes["Surprise(%)"].iloc[-1])
                futurs = ed[ed.index > pd.Timestamp.now(tz=ed.index.tz)]
                if len(futurs):
                    info["prochains_resultats"] = futurs.index[0].date().isoformat()
        except Exception:
            pass
    except Exception:
        pass
    return info

# ============================================================================
# 4. OUTILS STATISTIQUES
# ============================================================================

def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df, n=14):
    pc = df.Close.shift()
    tr = pd.concat([df.High - df.Low, (df.High - pc).abs(), (df.Low - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def max_drawdown(c):
    return float((c / c.cummax() - 1).min())


def sharpe_probabiliste(r):
    """PSR (Bailey & López de Prado) : probabilité que le vrai Sharpe soit > 0."""
    r = r.dropna()
    n = len(r)
    if n < 60 or r.std() == 0:
        return np.nan
    sr = r.mean() / r.std()
    g3 = float(((r - r.mean()) ** 3).mean() / r.std() ** 3)
    g4 = float(((r - r.mean()) ** 4).mean() / r.std() ** 4)
    den = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return _phi(sr * math.sqrt(n - 1) / den)


def hurst(c, max_lag=60):
    """Exposant de Hurst : > 0,5 = tendance persistante, < 0,5 = retour à la moyenne."""
    x = np.log(c.dropna().values[-750:])
    if len(x) < 200:
        return np.nan
    lags = np.arange(2, max_lag)
    tau = [np.std(x[l:] - x[:-l]) for l in lags]
    return float(np.polyfit(np.log(lags), np.log(tau), 1)[0])


def ratio_variance(c, q=5):
    """Test de Lo-MacKinlay : VR > 1 = tendance, < 1 = retour à la moyenne. Retourne (VR, z)."""
    lr = np.diff(np.log(c.dropna().values[-750:]))
    T = len(lr)
    if T < 200:
        return np.nan, np.nan
    mu = lr.mean()
    v1 = ((lr - mu) ** 2).sum() / (T - 1)
    rq = np.convolve(lr, np.ones(q), "valid")
    vq = ((rq - q * mu) ** 2).sum() / (q * (T - q + 1) * (1 - q / T))
    vr = vq / v1
    z = (vr - 1) / math.sqrt(2 * (2 * q - 1) * (q - 1) / (3 * q * T))
    return float(vr), float(z)


def bootstrap_barrieres(c, objectif, stop, horizon, n_sim=4000, bloc=5, demean=False, seed=0):
    """Simule des trajectoires futures en rejouant des blocs de rendements passés
    (garde la volatilité réelle et les queues épaisses). Retourne
    P(objectif touché avant le stop), P(stop d'abord), rendement moyen final."""
    lr = np.diff(np.log(c.dropna().values[-504:]))
    if len(lr) < 100:
        return None
    if demean:
        lr = lr - lr.mean()
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(horizon / bloc))
    starts = rng.integers(0, len(lr) - bloc, size=(n_sim, nb))
    idx = (starts[:, :, None] + np.arange(bloc)[None, None, :]).reshape(n_sim, -1)[:, :horizon]
    paths = np.cumsum(lr[idx], axis=1)
    up, dn = math.log(1 + objectif), math.log(1 - stop)
    hit_up = np.where((paths >= up).any(1), (paths >= up).argmax(1), horizon + 1)
    hit_dn = np.where((paths <= dn).any(1), (paths <= dn).argmax(1), horizon + 1)
    p_up = float(np.mean(hit_up < hit_dn))
    p_dn = float(np.mean(hit_dn < hit_up))
    reste = (hit_up > horizon) & (hit_dn > horizon)
    final = np.where(hit_up < hit_dn, objectif, np.where(hit_dn < hit_up, -stop, np.exp(paths[:, -1]) - 1))
    return {"p_objectif": p_up, "p_stop": p_dn, "p_ni_ni": float(reste.mean()),
            "esperance": float(final.mean())}


def analogues(df, horizon=21):
    """Cherche dans l'historique de l'action les jours qui ressemblent à aujourd'hui
    (même position de tendance, même momentum, même distance au plus haut, même RSI)
    et regarde ce qui s'est passé ensuite."""
    c = df.Close
    feat = pd.DataFrame({
        "mom6": c / c.shift(126) - 1,
        "dist52": c / df.High.rolling(252).max() - 1,
        "au_dessus200": c > c.rolling(200).mean(),
        "rsi": rsi(c),
        "fwd": c.shift(-horizon) / c - 1,
    }).dropna(subset=["mom6", "dist52", "rsi"])
    if len(feat) < 400:
        return None
    now = feat.iloc[-1]
    hist = feat.iloc[:-horizon].dropna(subset=["fwd"])
    tol_m = max(0.10, 0.5 * hist.mom6.std())
    for essai in range(3):
        k = 1 + essai
        m = ((hist.au_dessus200 == now.au_dessus200)
             & ((hist.dist52 - now.dist52).abs() < 0.05 * k)
             & ((hist.mom6 - now.mom6).abs() < tol_m * k))
        if essai < 2:
            m &= (hist.rsi - now.rsi).abs() < 10 * k
        sel = hist[m]
        # on espace les cas d'au moins 10 jours pour ne pas compter 20 fois le même épisode
        garde, dernier = [], None
        for d in sel.index:
            if dernier is None or (d - dernier).days >= 14:
                garde.append(d)
                dernier = d
        sel = sel.loc[garde]
        if len(sel) >= 15:
            break
    base = hist.fwd.iloc[::horizon]
    if len(sel) < 8:
        return {"n": len(sel)}
    f = sel.fwd
    t = f.mean() / (f.std() / math.sqrt(len(f))) if f.std() > 0 else np.nan
    return {"n": int(len(f)), "moyenne": float(f.mean()), "mediane": float(f.median()),
            "taux_gain": float((f > 0).mean()), "pire": float(f.min()), "meilleur": float(f.max()),
            "t_stat": float(t), "base_moyenne": float(base.mean()), "base_taux_gain": float((base > 0).mean()),
            "horizon": horizon}


def saisonnalite(c):
    try:
        m = c.resample("ME").last().pct_change().dropna()
    except ValueError:  # anciennes versions de pandas
        m = c.resample("M").last().pct_change().dropna()
    mois = pd.Timestamp.today().month
    s = m[m.index.month == mois]
    if len(s) < 4:
        return None
    return {"mois": mois, "moyenne": float(s.mean()), "taux_hausse": float((s > 0).mean()),
            "annees": int(len(s)), "base": float(m.mean())}

# ============================================================================
# 5. RÉGIME DE MARCHÉ
# ============================================================================

def regime_marche(donnees, indice):
    df = donnees.get(indice)
    if df is None or len(df) < 260:
        return {"etat": "inconnu", "texte": "Indice indisponible", "indice": indice}
    c = df.Close
    au200 = c.iloc[-1] > c.rolling(200).mean().iloc[-1]
    r3m = c.iloc[-1] / c.iloc[-64] - 1
    vol20 = c.pct_change().rolling(20).std() * math.sqrt(252)
    pct_vol = float((vol20.iloc[-1260:] < vol20.iloc[-1]).mean())
    vix = donnees.get(VIX)
    vix_niv = float(vix.Close.iloc[-1]) if vix is not None and len(vix) else None
    tnx = donnees.get(TAUX_10A)
    taux_var = (float(tnx.Close.iloc[-1] - tnx.Close.iloc[-64]) if tnx is not None and len(tnx) > 70 else None)
    points = (2 if au200 else -2) + (1 if r3m > 0 else -1) + (-1 if pct_vol > 0.8 else 0) \
        + (-1 if (vix_niv or 0) > 25 else 0)
    etat = "favorable" if points >= 2 else ("prudence" if points >= 0 else "défavorable")
    nom = "Stoxx 600" if indice == INDICE_EUROPE else "S&P 500"
    morceaux = [f"{nom} {'au-dessus' if au200 else 'en dessous'} de sa moyenne 200 jours",
                f"{r3m:+.1%} sur 3 mois", f"volatilité au {pct_vol:.0%} de ses 5 dernières années"]
    if vix_niv:
        morceaux.append(f"VIX à {vix_niv:.1f}")
    if taux_var is not None:
        morceaux.append(f"taux 10 ans US {taux_var:+.2f} pt sur 3 mois")
    return {"etat": etat, "texte": " · ".join(morceaux), "indice": indice, "au200": bool(au200),
            "r3m": float(r3m), "pct_vol": pct_vol, "vix": vix_niv}

# ============================================================================
# 6. ANALYSE D'UNE ACTION
# ============================================================================

def _sig(x):
    return 1 / (1 + math.exp(-x))


def analyser(ticker, nom, df, indice_df, opts, avec_fonda=True, avec_proba=True):
    df = df.dropna(subset=["Close"])
    df = df[df.Close > 0]
    if len(df) < JOURS_MIN:
        return None
    c, v = df.Close, df.Volume.fillna(0)
    r = c.pct_change()
    m = {"ticker": ticker, "nom": nom, "prix": float(c.iloc[-1]), "date": c.index[-1].date().isoformat()}

    # --- Tendance & momentum
    m["r1m"] = float(c.iloc[-1] / c.iloc[-22] - 1)
    m["r3m"] = float(c.iloc[-1] / c.iloc[-64] - 1)
    m["r6m"] = float(c.iloc[-1] / c.iloc[-127] - 1)
    m["r12_1"] = float(c.iloc[-22] / c.iloc[-253] - 1) if len(c) > 253 else np.nan
    m["vol"] = float(r.iloc[-252:].std() * math.sqrt(252))
    ma20, ma50, ma200 = (c.rolling(n).mean() for n in (20, 50, 200))
    m["au50"], m["au200"] = bool(c.iloc[-1] > ma50.iloc[-1]), bool(c.iloc[-1] > ma200.iloc[-1])
    m["ma50_200"] = bool(ma50.iloc[-1] > ma200.iloc[-1])
    m["dist52"] = float(c.iloc[-1] / df.High.iloc[-252:].max() - 1)
    if indice_df is not None and len(indice_df) > 130:
        ic = indice_df.Close.reindex(c.index).ffill()
        m["rel6m"] = float(m["r6m"] - (ic.iloc[-1] / ic.iloc[-127] - 1))
        ri = ic.pct_change()
        both = pd.concat([r, ri], axis=1).iloc[-252:].dropna()
        m["beta"] = float(both.cov().iloc[0, 1] / both.iloc[:, 1].var()) if len(both) > 100 else np.nan
    else:
        m["rel6m"], m["beta"] = np.nan, np.nan

    # --- Statistiques
    a = atr(df)
    m["atr_pct"] = float(a.iloc[-1] / c.iloc[-1])
    m["mdd1a"] = max_drawdown(c.iloc[-252:])
    rr = r.iloc[-126:].dropna()
    m["t_stat_6m"] = float(rr.mean() / (rr.std() / math.sqrt(len(rr)))) if rr.std() > 0 else np.nan
    m["sharpe1a"] = float(r.iloc[-252:].mean() / r.iloc[-252:].std() * math.sqrt(252))
    m["psr"] = sharpe_probabiliste(r.iloc[-252:])
    m["hurst"] = hurst(c)
    m["vr"], m["vr_z"] = ratio_variance(c)
    m["rsi"] = float(rsi(c).iloc[-1])
    sd = r.iloc[-252:].std()
    m["z5"] = float((c.iloc[-1] / c.iloc[-6] - 1) / (sd * math.sqrt(5))) if sd > 0 else 0.0
    m["ext_atr"] = float((c.iloc[-1] - ma20.iloc[-1]) / a.iloc[-1])

    # --- Volume
    m["rvol"] = float(v.iloc[-5:].mean() / max(1, v.iloc[-65:-5].mean()))
    up_days = r.iloc[-50:] > 0
    m["updown"] = float(v.iloc[-50:][up_days].sum() / max(1, v.iloc[-50:][~up_days].sum()))
    m["liquidite"] = float((c * v).iloc[-20:].mean())

    # --- Plan de trade
    stop_px = max(c.iloc[-1] - 2 * a.iloc[-1], c.iloc[-1] * (1 - 0.12))
    m["stop_pct"] = float(1 - stop_px / c.iloc[-1])
    m["stop"] = float(stop_px)
    m["objectif1"] = float(c.iloc[-1] + 2 * (c.iloc[-1] - stop_px))
    risque_eur = opts.capital * opts.risque / 100
    qte = risque_eur / (c.iloc[-1] - stop_px)
    qte = min(qte, 0.25 * opts.capital / c.iloc[-1])
    m["quantite"] = int(max(0, math.floor(qte)))
    m["montant"] = float(m["quantite"] * c.iloc[-1])

    # --- Probabilités
    if avec_proba:
        m["analogues"] = analogues(df)
        obj = opts.objectif / 100
        m["boot_hist"] = bootstrap_barrieres(c, obj, m["stop_pct"], opts.horizon, demean=False)
        m["boot_neutre"] = bootstrap_barrieres(c, obj, m["stop_pct"], opts.horizon, demean=True)
        m["saison"] = saisonnalite(c)
    m["fonda"] = fondamentaux(ticker, opts.demo) if avec_fonda else {}
    m["devise"] = m["fonda"].get("currency") or ("EUR" if ticker.upper().endswith(SUFFIXES_EUROPE) else "USD")
    m["courbe"] = c.iloc[-252:]
    m["courbe_ma50"] = ma50.iloc[-252:]
    m["courbe_ma200"] = ma200.iloc[-252:]
    noter(m)
    return m

# ============================================================================
# 7. NOTATION ET EXPLICATIONS
# ============================================================================

def _f(x, fmt="{:+.1%}"):
    return "n.d." if x is None or (isinstance(x, float) and np.isnan(x)) else fmt.format(x)


def noter(m):
    s, pos, neg, alertes = {}, [], [], []
    vol = max(m["vol"], 0.10)

    # Momentum (rendement ajusté du risque, 12-1 mois et 6 mois)
    x = 0.5 * (np.nan_to_num(m["r12_1"]) / vol) + 0.5 * (m["r6m"] / (vol * 0.707))
    if not np.isnan(m["rel6m"]):
        x += 0.3 * m["rel6m"] / (vol * 0.707)
    s["momentum"] = 100 * _sig(1.4 * x)
    if s["momentum"] >= 70:
        pos.append(f"Momentum fort : {_f(m['r6m'])} sur 6 mois, {_f(m['r12_1'])} sur 12 mois (hors dernier mois)"
                   + (f", soit {_f(m['rel6m'])} de mieux que l'indice" if m['rel6m'] > 0 else ""))
    elif s["momentum"] <= 35:
        neg.append(f"Momentum faible : {_f(m['r6m'])} sur 6 mois")

    # Tendance et qualité statistique de la tendance
    t = 25 * m["au200"] + 20 * m["au50"] + 15 * m["ma50_200"] + 25 * max(0, 1 + m["dist52"] / 0.25)
    psr = 0 if np.isnan(m["psr"]) else m["psr"]
    t += 15 * max(0, (psr - 0.5) / 0.5)
    s["tendance"] = min(100, t)
    if m["au200"] and m["au50"] and m["dist52"] > -0.05:
        pos.append(f"Tendance haussière propre : au-dessus des moyennes 50 et 200 jours, à {_f(m['dist52'])} de son plus haut annuel")
    if not m["au200"]:
        neg.append("Sous sa moyenne 200 jours : tendance de fond baissière")
    if psr >= 0.95:
        pos.append(f"Hausse statistiquement solide sur 1 an : {psr:.0%} de probabilité que la performance ne soit pas due au hasard (PSR)")
    if not np.isnan(m["t_stat_6m"]) and m["t_stat_6m"] >= 2:
        pos.append(f"Rendement moyen sur 6 mois significatif (t-stat {m['t_stat_6m']:.1f} > 2)")
    if not np.isnan(m["hurst"]):
        if m["hurst"] > 0.55:
            pos.append(f"Exposant de Hurst {m['hurst']:.2f} : l'action a tendance à prolonger ses mouvements")
        elif m["hurst"] < 0.45:
            alertes.append(f"Exposant de Hurst {m['hurst']:.2f} : l'action a plutôt tendance à revenir en arrière (moins adaptée au suivi de tendance)")

    # Probabilités
    an = m.get("analogues") or {}
    if an.get("moyenne") is not None:
        n = an["n"]
        edge = (an["moyenne"] - an["base_moyenne"]) * n / (n + 20)      # rétrécissement vers 0 si peu de cas
        edge += 0.5 * (an["taux_gain"] - an["base_taux_gain"]) * 0.05 * n / (n + 20)
        s["probabilites"] = 50 + 50 * math.tanh(edge / 0.03)
        txt = (f"Situations similaires dans son passé ({n} cas) : {_f(an['moyenne'])} en moyenne sur {an['horizon']} jours, "
               f"hausse dans {an['taux_gain']:.0%} des cas (contre {_f(an['base_moyenne'])} et {an['base_taux_gain']:.0%} en temps normal)")
        (pos if edge > 0.005 else neg if edge < -0.005 else alertes).append(txt)
    else:
        s["probabilites"] = 50.0
    bn = m.get("boot_neutre")
    if bn:
        s["probabilites"] = 0.8 * s["probabilites"] + 0.2 * (100 * bn["p_objectif"] / max(0.01, bn["p_objectif"] + bn["p_stop"]))

    # Volume
    s["volume"] = 50 + 25 * math.tanh(math.log(max(m["rvol"], 1e-3))) + 25 * math.tanh((m["updown"] - 1) * 2)
    if m["rvol"] >= 1.8:
        pos.append(f"Volume en forte hausse : {m['rvol']:.1f}× la normale sur 5 jours (intérêt d'acteurs importants)")
    if m["updown"] >= 1.3:
        pos.append(f"Accumulation : {m['updown']:.1f}× plus de volume les jours de hausse que les jours de baisse (50 j)")
    elif m["updown"] <= 0.75:
        neg.append(f"Distribution : plus de volume les jours de baisse ({m['updown']:.1f}×)")

    # Risque
    s["risque"] = 100 - 70 * min(1, max(0, (m["vol"] - 0.20) / 0.60)) - 30 * min(1, max(0, (-m["mdd1a"] - 0.15) / 0.45))
    if m["vol"] > 0.55:
        alertes.append(f"Très volatile ({m['vol']:.0%} par an) : positions à réduire")

    # Fondamentaux
    fd = m.get("fonda") or {}
    notes = []
    pe = fd.get("forwardPE") or fd.get("trailingPE")
    if pe:
        notes.append(10 if pe <= 0 else 85 if pe < 12 else 65 if pe < 20 else 50 if pe < 30 else 35 if pe < 45 else 20)
        if pe > 45:
            alertes.append(f"Valorisation élevée (PER {pe:.0f}) : beaucoup de croissance est déjà dans le prix")
        elif 0 < pe < 14:
            pos.append(f"Valorisation raisonnable (PER {pe:.0f})")
    g = fd.get("revenueGrowth")
    if g is not None:
        notes.append(50 + 50 * math.tanh(g / 0.15))
        if g > 0.15:
            pos.append(f"Croissance du chiffre d'affaires {_f(g)}")
        elif g < 0:
            neg.append(f"Chiffre d'affaires en baisse ({_f(g)})")
    roe = fd.get("returnOnEquity")
    if roe is not None:
        notes.append(50 + 50 * math.tanh((roe - 0.10) / 0.10))
    pm = fd.get("profitMargins")
    if pm is not None and pm < 0:
        neg.append("Entreprise non rentable (marge nette négative)")
        notes.append(20)
    tgt = fd.get("targetMeanPrice")
    if tgt:
        up = tgt / m["prix"] - 1
        notes.append(50 + 50 * math.tanh(up / 0.25))
        m["potentiel_analystes"] = up
        (pos if up > 0.15 else alertes if up < 0 else []).append(
            f"Objectif moyen des analystes : {tgt:.2f} ({_f(up)})") if (up > 0.15 or up < 0) else None
    sp = fd.get("surprise_pct")
    if sp is not None:
        notes.append(50 + 50 * math.tanh(sp / 10))
        if sp > 5:
            pos.append(f"Derniers résultats au-dessus des attentes ({sp:+.1f} %) : effet de dérive post-résultats possible")
        elif sp < -5:
            neg.append(f"Derniers résultats sous les attentes ({sp:+.1f} %)")
    if fd.get("prochains_resultats"):
        alertes.append(f"Prochains résultats le {fd['prochains_resultats']} : risque de gap")
    s["fondamentaux"] = float(np.mean(notes)) if notes else None

    # Note finale
    tot, poids = 0.0, 0.0
    for k, w in POIDS.items():
        if s.get(k) is not None:
            tot += w * s[k]
            poids += w
    note = tot / poids

    # Pénalités
    if m["z5"] > 2.5 or m["ext_atr"] > 4:
        note -= 10
        alertes.append(f"Surchauffe à court terme ({_f(m['r1m'])} sur 1 mois, {m['ext_atr']:.1f} ATR au-dessus de la moyenne 20 j) : "
                       "les hausses trop rapides ont tendance à se retracer, attendre un repli")
    if m["rsi"] > 80:
        note -= 5
        alertes.append(f"RSI {m['rsi']:.0f} : suracheté")
    if not m["au200"]:
        note -= 10
    if m["liquidite"] < LIQUIDITE_MIN:
        note -= 10
        alertes.append("Faible liquidité : écart de prix (spread) élevé, ordres à cours limité obligatoires")

    m["scores"] = {k: (None if v is None else float(v)) for k, v in s.items()}
    m["note"] = float(max(0, min(100, note)))
    m["verdict"] = ("Fort potentiel" if m["note"] >= 72 else "Intéressant" if m["note"] >= 60
                    else "Neutre" if m["note"] >= 45 else "À éviter")
    m["positifs"], m["negatifs"], m["alertes"] = pos, neg, alertes

# ============================================================================
# 8. RAPPORT HTML
# ============================================================================

CSS = """
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f6f7f9;color:#1d2330}
.wrap{max-width:1150px;margin:0 auto;padding:24px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:19px;margin:28px 0 10px} h3{font-size:16px;margin:16px 0 6px}
.muted{color:#6b7280;font-size:13px}
.regime{padding:12px 16px;border-radius:10px;margin:14px 0;font-size:14px}
.favorable{background:#e7f6ec;border:1px solid #9bd3ae}.prudence{background:#fff6e0;border:1px solid #f0cf7a}
.défavorable{background:#fdeaea;border:1px solid #efa3a3}.inconnu{background:#eee}
table{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid #eef0f3;text-align:left;vertical-align:middle}
th{background:#f0f2f5;font-weight:600;font-size:12px;color:#4b5563}
.bar{height:8px;background:#e5e7eb;border-radius:4px;width:90px;display:inline-block;vertical-align:middle;margin-right:6px}
.bar i{display:block;height:8px;border-radius:4px}
.badge{padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600;white-space:nowrap}
.b1{background:#dcf3e3;color:#17663a}.b2{background:#e3eefc;color:#1f4f99}.b3{background:#f1f1f1;color:#555}.b4{background:#fde4e4;color:#992424}
.card{background:#fff;border-radius:12px;padding:18px 20px;margin:16px 0;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin:10px 0}
.kpi{background:#f7f8fa;border-radius:8px;padding:9px 11px}.kpi b{display:block;font-size:16px}.kpi span{font-size:12px;color:#6b7280}
ul{margin:6px 0 6px 18px;padding:0} li{margin:3px 0;font-size:14px}
.pos li::marker{color:#1a9a4b}.neg li::marker{color:#c62828}.al li::marker{color:#d58a00}
.note{font-size:34px;font-weight:700}
.plan{background:#f3f7ff;border-radius:8px;padding:10px 14px;font-size:14px}
.small{font-size:12px}
"""


def _badge(verdict):
    cls = {"Fort potentiel": "b1", "Intéressant": "b2", "Neutre": "b3", "À éviter": "b4"}[verdict]
    return f'<span class="badge {cls}">{verdict}</span>'


def _bar(v):
    if v is None:
        return '<span class="muted">n.d.</span>'
    col = "#1a9a4b" if v >= 65 else "#3b82f6" if v >= 50 else "#f59e0b" if v >= 40 else "#dc2626"
    return f'<span class="bar"><i style="width:{v:.0f}%;background:{col}"></i></span>{v:.0f}'


def _svg(m, w=520, h=150):
    c, a, b = m["courbe"], m["courbe_ma50"], m["courbe_ma200"]
    allv = pd.concat([c, a.dropna(), b.dropna()])
    lo, hi = allv.min(), allv.max()
    def pts(s):
        s = s.dropna()
        if s.empty:
            return ""
        xs = np.linspace(0, w, len(c))[-len(s):]
        ys = h - (s.values - lo) / (hi - lo + 1e-9) * (h - 10) - 5
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (f'<svg width="100%" viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="max-width:{w}px">'
            f'<polyline fill="none" stroke="#9ca3af" stroke-width="1" stroke-dasharray="4 3" points="{pts(b)}"/>'
            f'<polyline fill="none" stroke="#f59e0b" stroke-width="1.2" points="{pts(a)}"/>'
            f'<polyline fill="none" stroke="#2563eb" stroke-width="1.8" points="{pts(c)}"/></svg>'
            '<div class="small muted">1 an · bleu : cours · orange : moyenne 50 j · gris : moyenne 200 j</div>')


def _taille(m):
    q = m["quantite"]
    return "cours trop élevé pour ton capital" if q == 0 else f"{q} titre{'s' if q > 1 else ''}"


def _liste(titre, items, cls):
    if not items:
        return ""
    return f"<h3>{titre}</h3><ul class='{cls}'>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>"


def carte_html(m, opts, detail=False):
    e = html.escape
    sc = m["scores"]
    fd = m.get("fonda") or {}
    an = m.get("analogues") or {}
    bh, bn = m.get("boot_hist"), m.get("boot_neutre")
    out = [f'<div class="card"><div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap">'
           f'<div><h2 style="margin:0">{e(m["nom"])} <span class="muted">{e(m["ticker"])}</span></h2>'
           f'<div class="muted">{e(str(fd.get("sector") or ""))} {("· " + e(str(fd.get("industry")))) if fd.get("industry") else ""}'
           f' · cours {m["prix"]:.2f} au {m["date"]}</div></div>'
           f'<div style="text-align:right"><div class="note">{m["note"]:.0f}<span class="muted" style="font-size:14px">/100</span></div>{_badge(m["verdict"])}</div></div>']
    out.append('<div class="grid">' + "".join(
        f'<div class="kpi"><span>{lab}</span><b>{_bar(sc.get(k))}</b></div>' for k, lab in
        [("momentum", "Momentum"), ("tendance", "Tendance"), ("probabilites", "Probabilités"),
         ("volume", "Volume"), ("risque", "Risque (100 = calme)"), ("fondamentaux", "Fondamentaux")]) + "</div>")
    out.append(_liste("Points forts", m["positifs"], "pos"))
    out.append(_liste("Points faibles", m["negatifs"], "neg"))
    out.append(_liste("Points d'attention", m["alertes"], "al"))
    if bh and bn:
        out.append(f"<h3>Probabilités (objectif +{opts.objectif:.0f} % / stop −{m['stop_pct']:.1%} / {opts.horizon} jours)</h3>"
                   f"<div class='grid'><div class='kpi'><span>Si la tendance passée continue</span><b>{bh['p_objectif']:.0%} objectif · {bh['p_stop']:.0%} stop</b>"
                   f"<span>espérance {_f(bh['esperance'])} par trade</span></div>"
                   f"<div class='kpi'><span>Sans tendance (hasard pur, même volatilité)</span><b>{bn['p_objectif']:.0%} objectif · {bn['p_stop']:.0%} stop</b>"
                   f"<span>espérance {_f(bn['esperance'])} par trade</span></div></div>"
                   "<div class='small muted'>Simulation de 4 000 trajectoires en rejouant des blocs de vrais rendements des 2 dernières années. "
                   "La réalité se situe généralement entre les deux : la tendance passée ne continue pas toujours.</div>")
    plan = (f"<div class='plan'><b>Plan de trade indicatif</b> — entrée vers {m['prix']:.2f} · stop {m['stop']:.2f} "
            f"(−{m['stop_pct']:.1%}, 2 ATR) · vendre la moitié à {m['objectif1']:.2f} (+{m['objectif1'] / m['prix'] - 1:.0%}, 2× le risque) "
            f"puis suivre le reste sous la moyenne 50 jours · taille : {_taille(m)} ≈ {m['montant']:,.0f} {m.get('devise', '')} "
            f"pour risquer {opts.risque:g} % de {opts.capital:,.0f} €</div>").replace(",", " ")
    out.append(plan)
    if detail:
        out.append("<h3>Graphique</h3>" + _svg(m))
        stats = [("Perf. 1 mois", _f(m["r1m"])), ("Perf. 3 mois", _f(m["r3m"])), ("Perf. 6 mois", _f(m["r6m"])),
                 ("Perf. 12-1 mois", _f(m["r12_1"])), ("vs indice (6 mois)", _f(m["rel6m"])),
                 ("Distance plus haut 52 sem.", _f(m["dist52"])), ("Volatilité annuelle", _f(m["vol"], "{:.0%}")),
                 ("Bêta vs indice", _f(m["beta"], "{:.2f}")), ("Pire baisse sur 1 an", _f(m["mdd1a"])),
                 ("Sharpe 1 an", _f(m["sharpe1a"], "{:.2f}")), ("PSR (Sharpe > 0)", _f(m["psr"], "{:.0%}")),
                 ("t-stat 6 mois", _f(m["t_stat_6m"], "{:.2f}")), ("Hurst", _f(m["hurst"], "{:.2f}")),
                 ("Ratio de variance (5 j)", f"{_f(m['vr'], '{:.2f}')} (z {_f(m['vr_z'], '{:+.1f}')})"),
                 ("RSI 14", _f(m["rsi"], "{:.0f}")), ("ATR", _f(m["atr_pct"], "{:.1%}")),
                 ("Volume relatif 5 j", _f(m["rvol"], "{:.2f}×")), ("Volume hausse/baisse 50 j", _f(m["updown"], "{:.2f}×"))]
        out.append("<h3>Statistiques</h3><div class='grid'>" + "".join(
            f"<div class='kpi'><span>{a}</span><b>{b}</b></div>" for a, b in stats) + "</div>")
        if an.get("moyenne") is not None:
            out.append("<h3>Situations similaires dans l'historique de l'action</h3><table><tr><th></th><th>Cas similaires</th><th>Toutes périodes</th></tr>"
                       f"<tr><td>Nombre de cas</td><td>{an['n']}</td><td>—</td></tr>"
                       f"<tr><td>Rendement moyen à {an['horizon']} j</td><td>{_f(an['moyenne'])}</td><td>{_f(an['base_moyenne'])}</td></tr>"
                       f"<tr><td>Rendement médian</td><td>{_f(an['mediane'])}</td><td>—</td></tr>"
                       f"<tr><td>% de cas en hausse</td><td>{an['taux_gain']:.0%}</td><td>{an['base_taux_gain']:.0%}</td></tr>"
                       f"<tr><td>Pire / meilleur cas</td><td>{_f(an['pire'])} / {_f(an['meilleur'])}</td><td>—</td></tr>"
                       f"<tr><td>t-stat</td><td>{an['t_stat']:.2f}</td><td>—</td></tr></table>"
                       "<div class='small muted'>Jours passés où l'action avait la même position de tendance, un momentum et une distance au plus haut proches, "
                       "et un RSI proche. Moins de 20 cas ou une t-stat sous 2 = indication fragile.</div>")
        sa = m.get("saison")
        if sa:
            mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"][sa["mois"] - 1]
            out.append(f"<h3>Saisonnalité</h3><p style='font-size:14px'>En {mois}, l'action a fait en moyenne {_f(sa['moyenne'])} "
                       f"(hausse {sa['taux_hausse']:.0%} des années, sur {sa['annees']} ans), contre {_f(sa['base'])} pour un mois moyen. "
                       "<span class='muted'>À prendre comme une indication secondaire : peu d'années.</span></p>")
        if fd:
            rows = [("PER prévisionnel", fd.get("forwardPE"), "{:.1f}"), ("PER", fd.get("trailingPE"), "{:.1f}"),
                    ("Croissance CA", fd.get("revenueGrowth"), "{:+.1%}"), ("Marge nette", fd.get("profitMargins"), "{:.1%}"),
                    ("Rentabilité des capitaux propres", fd.get("returnOnEquity"), "{:.1%}"),
                    ("Dette / capitaux propres", fd.get("debtToEquity"), "{:.0f} %"),
                    ("Objectif analystes", fd.get("targetMeanPrice"), "{:.2f}"),
                    ("Recommandation (1 = achat fort, 5 = vente)", fd.get("recommendationMean"), "{:.1f}"),
                    ("Nombre d'analystes", fd.get("numberOfAnalystOpinions"), "{:.0f}"),
                    ("Dernière surprise de résultats", fd.get("surprise_pct"), "{:+.1f} %")]
            out.append("<h3>Fondamentaux</h3><div class='grid'>" + "".join(
                f"<div class='kpi'><span>{a}</span><b>{_f(v, f) if v is not None else 'n.d.'}</b></div>" for a, v, f in rows) + "</div>")
    out.append("</div>")
    return "".join(out)


def page_html(titre, regimes, corps):
    reg = html_regimes(regimes)
    return (f"<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'><title>{titre}</title><style>{CSS}</style></head>"
            f"<body><div class='wrap'><h1>{titre}</h1><div class='muted'>Généré le {dt.datetime.now():%d/%m/%Y à %H:%M} · "
            "données Yahoo Finance · outil d'aide à la décision, pas un conseil en investissement</div>"
            f"{reg}{corps}</div></body></html>")


def ecrire_rapport(nom, contenu, ouvrir=True):
    os.makedirs("rapports", exist_ok=True)
    chemin = os.path.abspath(os.path.join("rapports", nom))
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu)
    print(f"\nRapport : {chemin}")
    if ouvrir:
        try:
            webbrowser.open("file://" + chemin)
        except Exception:
            pass
    return chemin

# ============================================================================
# 9. COMMANDES
# ============================================================================

FICHIER_UNIVERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "univers.csv")
UNIVERS_CHOIX = {"pea": "Europe éligible PEA", "europe": "Europe (dont Royaume-Uni, Suisse, Norvège)",
                 "us": "États-Unis", "tout": "Europe + États-Unis", "petites": "Petites valeurs uniquement",
                 "coeur": "Liste courte (≈ 1 000 valeurs principales)"}


def filtrer_univers(u, choix):
    if choix == "pea":
        return u[u.pea == "1"]
    if choix == "europe":
        return u[u.region == "Europe"]
    if choix == "us":
        return u[u.region == "US"]
    if choix == "semis":
        return u[u.secteur == "Semi-conducteurs"]
    if choix == "petites":
        return u[u.taille == "Petite"]
    if choix == "coeur":
        return u[u.coeur == "1"] if "coeur" in u else u
    return u


def _lire_univers():
    if not os.path.exists(FICHIER_UNIVERS):
        return None
    return pd.read_csv(FICHIER_UNIVERS, sep=";", dtype=str).fillna("")


def charger_univers(choix):
    u = _lire_univers()
    if u is not None and choix in UNIVERS_CHOIX:
        u = filtrer_univers(u, choix)
        return dict(zip(u.ticker, u.nom))
    if choix == "pea":
        return dict(UNIVERS_PEA)
    if choix == "us":
        return dict(UNIVERS_US)
    if choix in ("tout", "europe"):
        return {**UNIVERS_PEA, **UNIVERS_US} if choix == "tout" else dict(UNIVERS_PEA)
    if os.path.exists(choix):
        u = {}
        with open(choix, encoding="utf-8") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne and not ligne.startswith("#"):
                    t, *n = [x.strip() for x in ligne.split(";")]
                    u[t] = n[0] if n else t
        return u
    sys.exit(f"Univers inconnu : {choix}")


def ajuster_regime(m, regime, macro_zone=None):
    """Le contexte de marché et la macro pèsent sur la note : les achats en tendance échouent plus souvent en marché baissier."""
    if macro_zone and macro_zone.get("etat") == "défavorable":
        m["note"] = max(0.0, m["note"] - 4)
        m["alertes"].insert(0, "Macro défavorable dans sa zone (voir la météo économique) : note réduite de 4 points")
    elif macro_zone and macro_zone.get("etat") == "favorable":
        m["note"] = min(100.0, m["note"] + 2)
    if regime.get("etat") == "défavorable":
        m["note"] = max(0.0, m["note"] - 8)
        m["alertes"].insert(0, "Marché global baissier : la note est réduite de 8 points, la plupart des cassures échouent dans ce contexte")
    elif regime.get("etat") == "prudence":
        m["note"] = max(0.0, m["note"] - 3)
    m["verdict"] = ("Fort potentiel" if m["note"] >= 72 else "Intéressant" if m["note"] >= 60
                    else "Neutre" if m["note"] >= 45 else "À éviter")


def indice_de(ticker):
    return INDICE_EUROPE if ticker.upper().endswith(SUFFIXES_EUROPE) else INDICE_US


CONSEIL_REGIME = {
    "favorable": "Contexte porteur : tu peux utiliser tes positions normalement.",
    "prudence": "Contexte mitigé : réduis le nombre de positions ou la taille (moitié du risque).",
    "défavorable": "Contexte baissier : la plupart des achats en tendance échouent dans ces phases. Rester très sélectif ou en liquidités.",
    "inconnu": "",
}
INDICES_AUX = [INDICE_EUROPE, INDICE_US, VIX, TAUX_10A]


def meteo_macro(demo=False):
    try:
        import macro
        return macro.meteo(demo=demo)
    except Exception as e:  # noqa
        print("   ! macro indisponible :", e)
        return None


def macro_de(meteo, ticker):
    if not meteo:
        return None
    return meteo["Europe" if indice_de(ticker) == INDICE_EUROPE else "US"]


def scan(opts, data=None, progression=None, meteo=None):
    """Classe l'univers. Retourne un dictionnaire de résultats (utilisé par la ligne de commande et l'appli web)."""
    univ = charger_univers(opts.univers)
    if meteo is None:
        meteo = meteo_macro(opts.demo)
    if data is None:
        data = telecharger(list(univ) + INDICES_AUX, demo=opts.demo)
    res = []
    for t, nom in univ.items():
        if t not in data:
            continue
        m = analyser(t, nom, data[t], data.get(indice_de(t)), opts, avec_fonda=False, avec_proba=False)
        if m and m["liquidite"] >= LIQUIDITE_MIN / 4:
            res.append(m)
    res.sort(key=lambda m: -m["note"])
    finalistes = res[:max(opts.top * 2, 30)]
    complet = []
    for i, m in enumerate(finalistes, 1):
        if progression:
            progression(i / len(finalistes), m["ticker"])
        mm = analyser(m["ticker"], m["nom"], data[m["ticker"]], data.get(indice_de(m["ticker"])), opts)
        if mm:
            complet.append(mm)
    reg = {i: regime_marche(data, i) for i in (INDICE_EUROPE, INDICE_US)}
    for m in complet:
        ajuster_regime(m, reg[indice_de(m["ticker"])], macro_de(meteo, m["ticker"]))
    complet.sort(key=lambda m: -m["note"])
    regimes = [reg[i] for i in ([INDICE_EUROPE] if opts.univers in ("pea", "europe") else
                                [INDICE_US] if opts.univers == "us" else [INDICE_EUROPE, INDICE_US])]
    return {"top": complet[:opts.top], "complet": complet, "regimes": regimes, "n_analyse": len(res), "meteo": meteo}


def html_scan(r, opts):
    corps = ""
    if r.get("meteo"):
        import macro
        corps += macro.html_meteo(r["meteo"])
    corps += "".join(f"<p class='small'><b>{'Europe' if g['indice'] == INDICE_EUROPE else 'États-Unis'} :</b> "
                    f"{CONSEIL_REGIME[g['etat']]}</p>" for g in r["regimes"])
    corps += ("<h2>Classement du jour</h2><table><tr><th>#</th><th>Action</th><th>Note</th><th>Avis</th><th>Momentum</th>"
              "<th>Tendance</th><th>Proba.</th><th>Perf. 6 m</th><th>P(objectif) *</th><th>Stop</th><th>Taille</th></tr>")
    for i, m in enumerate(r["top"], 1):
        bn, bh = m.get("boot_neutre") or {}, m.get("boot_hist") or {}
        pmix = (bn.get("p_objectif", 0) + bh.get("p_objectif", 0)) / 2
        corps += (f"<tr><td>{i}</td><td><b>{html.escape(m['nom'])}</b><br><span class='muted'>{m['ticker']}</span></td>"
                  f"<td>{_bar(m['note'])}</td><td>{_badge(m['verdict'])}</td><td>{_bar(m['scores']['momentum'])}</td>"
                  f"<td>{_bar(m['scores']['tendance'])}</td><td>{_bar(m['scores']['probabilites'])}</td><td>{_f(m['r6m'])}</td>"
                  f"<td>{pmix:.0%}</td><td>−{m['stop_pct']:.1%}</td><td>{_taille(m)}</td></tr>")
    corps += (f"</table><div class='small muted'>* Probabilité moyenne de toucher +{opts.objectif:.0f} % avant le stop en {opts.horizon} jours "
              "(moyenne des simulations « tendance continue » et « hasard pur »).</div><h2>Détail et raisons</h2>")
    return corps + "".join(carte_html(m, opts) for m in r["top"])


def analyse(opts, requetes, data_fn=None, meteo=None):
    """Analyse détaillée des actions proposées. data_fn(tickers) permet à l'appli web de mettre en cache."""
    paires = [resoudre(q, opts.demo) for q in requetes]
    tickers = [t for t, _ in paires]
    data = (data_fn or (lambda tk: telecharger(tk, demo=opts.demo)))(tickers + INDICES_AUX)
    ok, erreurs = [], []
    noms = {**UNIVERS_PEA, **UNIVERS_US}
    u = _lire_univers()
    if u is not None:
        noms.update(dict(zip(u.ticker, u.nom)))
    if meteo is None:
        meteo = meteo_macro(opts.demo)
    for t, nom in paires:
        if t not in data:
            erreurs.append(f"Pas de données pour {t} (vérifie le ticker Yahoo : .PA Paris, .DE Francfort, .AS Amsterdam…)")
            continue
        m = analyser(t, noms.get(t, nom), data[t], data.get(indice_de(t)), opts)
        if m is None:
            erreurs.append(f"Historique trop court pour {t}")
            continue
        if m["fonda"].get("longName"):
            m["nom"] = m["fonda"]["longName"]
        ajuster_regime(m, regime_marche(data, indice_de(t)), macro_de(meteo, t))
        ok.append(m)
    regimes = [regime_marche(data, i) for i in sorted({indice_de(m["ticker"]) for m in ok})]
    return {"actions": ok, "regimes": regimes, "erreurs": erreurs, "meteo": meteo}


def html_analyse(r, opts):
    return "".join(carte_html(m, opts, detail=True) for m in r["actions"])


def backtest(opts, data=None):
    """Teste la partie 'cours et volumes' du score (momentum, tendance, volume, risque) :
    chaque fin de mois on achète les N meilleures actions, à poids égal, on garde un mois.
    Frais : spread + 1 € par ordre. Filtre de marché : liquidités si l'indice est sous sa moyenne 200 j."""
    univ = charger_univers(opts.univers)
    indice = INDICE_EUROPE if opts.univers in ("pea", "europe") else INDICE_US   # semis : S&P 500
    if data is None:
        data = telecharger(list(univ) + [indice], annees=16, demo=opts.demo)
    closes = pd.DataFrame({t: data[t].Close for t in univ if t in data}).sort_index().ffill(limit=5)
    highs = pd.DataFrame({t: data[t].High for t in univ if t in data}).reindex(closes.index).ffill(limit=5)
    vols = pd.DataFrame({t: data[t].Volume for t in univ if t in data}).reindex(closes.index).fillna(0)
    idx = data[indice].Close.reindex(closes.index).ffill()
    r = closes.pct_change(fill_method=None)
    vol = r.rolling(252).std() * math.sqrt(252)
    v = vol.clip(lower=0.10)
    r12_1 = closes.shift(21) / closes.shift(252) - 1
    r6 = closes / closes.shift(126) - 1
    rel6 = r6.sub(idx / idx.shift(126) - 1, axis=0)
    x = 0.5 * r12_1 / v + 0.5 * r6 / (v * 0.707) + 0.3 * rel6 / (v * 0.707)
    mom = 100 / (1 + np.exp(-1.4 * x))
    ma50, ma200 = closes.rolling(50).mean(), closes.rolling(200).mean()
    dist52 = closes / highs.rolling(252).max() - 1
    tend = (25 * (closes > ma200) + 20 * (closes > ma50) + 15 * (ma50 > ma200)
            + 25 * (1 + dist52 / 0.25).clip(lower=0)).clip(upper=100)
    rvol = vols.rolling(5).mean() / vols.shift(5).rolling(60).mean().replace(0, np.nan)
    upv = vols.where(r > 0, 0).rolling(50).sum()
    dnv = vols.where(r <= 0, 0).rolling(50).sum().replace(0, np.nan)
    volu = 50 + 25 * np.tanh(np.log(rvol.clip(lower=1e-3))) + 25 * np.tanh((upv / dnv - 1) * 2)
    mdd = closes / closes.rolling(252).max() - 1
    risq = 100 - 70 * ((vol - 0.2) / 0.6).clip(0, 1) - 30 * ((-mdd - 0.15) / 0.45).clip(0, 1)
    w = {k: POIDS[k] for k in ("momentum", "tendance", "volume", "risque")}
    note = (w["momentum"] * mom + w["tendance"] * tend + w["volume"] * volu + w["risque"] * risq) / sum(w.values())
    note = note - 10 * (closes <= ma200)
    liq = (closes * vols).rolling(20).mean()
    note = note.where(liq > LIQUIDITE_MIN)

    debut = pd.Timestamp(opts.debut)
    fins = closes.loc[debut:].groupby(closes.loc[debut:].index.to_period("M")).tail(1).index
    rend, rend_idx, rend_eq, exp, ancien = [], [], [], [], set()
    ma200_idx = idx.rolling(200).mean()
    for d0, d1 in zip(fins[:-1], fins[1:]):
        choix = set(note.loc[d0].dropna().nlargest(opts.top).index) if idx.loc[d0] > ma200_idx.loc[d0] else set()
        pr = (closes.loc[d1] / closes.loc[d0] - 1)
        brut = pr[list(choix)].fillna(0).mean() if choix else 0.0
        rot = len(choix ^ ancien) / max(1, opts.top)
        cout = rot * (SPREAD_ESTIME + FRAIS_ORDRE_EUR / (opts.capital / opts.top))
        rend.append(brut - cout)
        rend_idx.append(idx.loc[d1] / idx.loc[d0] - 1)
        rend_eq.append(pr.dropna().mean())
        exp.append(1 if choix else 0)
        ancien = choix
    s = pd.Series(rend, index=fins[1:])
    si, se = pd.Series(rend_idx, index=fins[1:]), pd.Series(rend_eq, index=fins[1:])

    def stats(x):
        eq = (1 + x).cumprod()
        ans = len(x) / 12
        return {"Rendement annuel": eq.iloc[-1] ** (1 / ans) - 1, "Volatilité": x.std() * math.sqrt(12),
                "Sharpe": x.mean() / x.std() * math.sqrt(12) if x.std() > 0 else np.nan,
                "Pire baisse": float((eq / eq.cummax() - 1).min()),
                "Mois positifs": (x[x != 0] > 0).mean() if (x != 0).any() else np.nan,
                "Total": eq.iloc[-1] - 1}
    tab = pd.DataFrame({f"Score (top {opts.top})": stats(s), "Indice": stats(si),
                        "Toutes les actions à poids égal": stats(se)})
    fmt = tab.copy().astype(object)
    for row in tab.index:
        for col in tab.columns:
            val = tab.loc[row, col]
            fmt.loc[row, col] = (f"{val:.2f}" if row == "Sharpe" else f"{val:.0%}" if row == "Mois positifs" else f"{val:+.1%}")
    exces = s - si
    t = exces.mean() / (exces.std() / math.sqrt(len(exces)))
    eqs = pd.DataFrame({"Score": (1 + s).cumprod(), "Indice": (1 + si).cumprod(), "Poids égal": (1 + se).cumprod()})
    return {"tableau": fmt, "exces": float(exces.mean()), "t": float(t), "exposition": float(np.mean(exp)),
            "debut": fins[0].date(), "fin": fins[-1].date(), "mois": len(s), "courbes": eqs}


def html_backtest(b):
    corps = (f"<div class='card'><h2>Résultats {b['debut']} → {b['fin']} ({b['mois']} mois)</h2>" + b["tableau"].to_html(border=0) +
             f"<p>Surperformance mensuelle moyenne vs indice : <b>{b['exces']:+.2%}</b> (t-stat {b['t']:.2f} ; au-dessus de 2 = significatif). "
             f"Investi {b['exposition']:.0%} du temps (liquidités quand l'indice est sous sa moyenne 200 jours).</p>"
             "<p class='small muted'>Biais du survivant : l'univers contient les actions d'aujourd'hui (les faillites passées n'y sont pas). "
             "Résultats réels probablement inférieurs. Probabilités et fondamentaux non inclus (pas d'historique gratuit).</p></div>")
    eqs = b["courbes"]
    w_, h_ = 900, 260
    lo, hi = eqs.min().min(), eqs.max().max()
    cols = {"Score": "#2563eb", "Indice": "#9ca3af", "Poids égal": "#f59e0b"}
    lignes = ""
    for k in eqs:
        xs = np.linspace(0, w_, len(eqs))
        ys = h_ - (np.log(eqs[k].values) - np.log(lo)) / (np.log(hi) - np.log(lo) + 1e-9) * (h_ - 10) - 5
        lignes += f'<polyline fill="none" stroke="{cols[k]}" stroke-width="2" points="{" ".join(f"{a:.1f},{c:.1f}" for a, c in zip(xs, ys))}"/>'
    corps += (f"<div class='card'><h2>Évolution de 1 € (échelle log)</h2><svg width='100%' viewBox='0 0 {w_} {h_}'>{lignes}</svg>"
              "<div class='small'><span style='color:#2563eb'>■ Score</span> · <span style='color:#9ca3af'>■ Indice</span> · "
              "<span style='color:#f59e0b'>■ Toutes les actions</span></div></div>")
    return corps


def html_regimes(regimes):
    return "".join(f'<div class="regime {r["etat"]}"><b>Marché {("européen" if r["indice"] == INDICE_EUROPE else "américain")} : '
                   f'{r["etat"]}</b> — {html.escape(r["texte"])}</div>' for r in regimes)


# ---- préparation nocturne (5 000+ actions) ----

def _json(x):
    """Rend un résultat sérialisable en JSON (pour l'appli web)."""
    if isinstance(x, pd.Series):
        return {"__serie__": [d.strftime("%Y-%m-%d") for d in x.index], "v": [None if pd.isna(v) else float(v) for v in x.values]}
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if np.isnan(x) or np.isinf(x) else float(x)
    if isinstance(x, (dt.date, pd.Timestamp)):
        return str(x)
    return x


def _dejson(x):
    if isinstance(x, dict):
        if "__serie__" in x:
            return pd.Series([np.nan if v is None else v for v in x["v"]], index=pd.to_datetime(x["__serie__"]), dtype=float)
        return {k: _dejson(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_dejson(v) for v in x]
    return np.nan if x is None else x


def recalculer_taille(m, capital, risque):
    ecart = m["prix"] - m["stop"]
    qte = capital * risque / 100 / ecart if ecart > 0 else 0
    qte = min(qte, 0.25 * capital / m["prix"])
    m["quantite"] = int(max(0, math.floor(qte)))
    m["montant"] = float(m["quantite"] * m["prix"])
    return m


def preparer(opts, sortie="resultats/resultats.json.gz"):
    """Calcul complet, prévu pour tourner chaque nuit (GitHub Actions) :
    1) cours sur 2 ans pour toutes les actions -> note rapide,
    2) analyse complète (10 ans, probabilités, fondamentaux) des meilleures de chaque univers,
    3) macro, 4) backtest (option). Résultat : un fichier JSON compressé lu par l'appli."""
    import gzip
    import json
    import time
    t0 = time.time()
    u = _lire_univers()
    tickers = list(u.ticker)
    info = u.set_index("ticker")
    print(f"1/4 Cours sur 2 ans de {len(tickers)} actions…")
    data = telecharger(tickers + INDICES_AUX, annees=2.3, demo=opts.demo)
    lignes, rapides = [], {}
    for t in tickers:
        if t not in data:
            continue
        try:
            m = analyser(t, info.at[t, "nom"], data[t], data.get(indice_de(t)), opts, avec_fonda=False, avec_proba=False)
        except Exception:
            m = None
        if not m or m["liquidite"] < LIQUIDITE_MIN / 4:
            continue
        rapides[t] = m
        lignes.append({"ticker": t, "nom": m["nom"], "note": m["note"], "verdict": m["verdict"], "prix": m["prix"],
                       "r1m": m["r1m"], "r6m": m["r6m"], "r12_1": m["r12_1"], "dist52": m["dist52"], "vol": m["vol"],
                       "rsi": m["rsi"], "liquidite": m["liquidite"], **{f"s_{k}": v for k, v in m["scores"].items()},
                       **{c: info.at[t, c] for c in ("region", "pea", "secteur", "taille", "pays")}})
    tab = pd.DataFrame(lignes)
    print(f"   {len(tab)} actions notées sur {len(tickers)} ({time.time() - t0:.0f} s)")
    # finalistes : les meilleures de chaque univers
    final = set()
    tabc = tab.assign(coeur=tab.ticker.map(info["coeur"]) if "coeur" in info else "1")
    for choix in UNIVERS_CHOIX:
        final |= set(filtrer_univers(tabc, choix).nlargest(60, "note").ticker)
    for _, g in tabc.groupby("secteur"):          # les meilleures de chaque secteur, pour le filtre par secteur
        final |= set(g.nlargest(20, "note").ticker)
    for _, g in tabc.groupby("taille"):           # et de chaque taille
        final |= set(g.nlargest(25, "note").ticker)
    final = sorted(final)
    print(f"2/4 Analyse complète de {len(final)} finalistes…")
    data10 = telecharger(final + INDICES_AUX, annees=10, demo=opts.demo)
    meteo = meteo_macro(opts.demo)
    reg = {i: regime_marche(data10, i) for i in (INDICE_EUROPE, INDICE_US)}
    complets = []
    for i, t in enumerate(final, 1):
        df = data10.get(t, data.get(t))
        try:
            m = analyser(t, info.at[t, "nom"], df, data10.get(indice_de(t)), opts)
        except Exception as e:  # noqa
            print("   !", t, e)
            continue
        if not m:
            continue
        if (m.get("fonda") or {}).get("longName"):
            m["nom"] = m["fonda"]["longName"]
        ajuster_regime(m, reg[indice_de(t)], macro_de(meteo, t))
        for c in ("region", "pea", "secteur", "taille", "pays"):
            m[c] = info.at[t, c]
        complets.append(m)
        if not opts.demo:
            time.sleep(0.3)
        if i % 25 == 0:
            print(f"   {i}/{len(final)}")
    bt = None
    if getattr(opts, "avec_backtest", False):
        print("3/4 Backtest sur la liste courte…")
        try:
            o = argparse.Namespace(**vars(opts))
            o.univers, o.top, o.debut = "coeur", 15, "2012-01-01"
            bt = backtest(o)
            bt["courbes"] = {k: _json(v) for k, v in bt["courbes"].items()}
            bt["tableau"] = bt["tableau"].to_dict()
        except Exception as e:  # noqa
            print("   ! backtest :", e)
    res = {"date": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "n_univers": len(tickers), "n_notees": len(tab),
           "table": tab.to_dict(orient="list"), "finalistes": [_json(m) for m in complets],
           "regimes": _json(reg), "meteo": _json(meteo), "backtest": _json(bt) if bt else None,
           "params": {"objectif": opts.objectif, "horizon": opts.horizon}}
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    with gzip.open(sortie, "wt", encoding="utf-8") as f:
        json.dump(res, f)
    print(f"4/4 Terminé en {time.time() - t0:.0f} s -> {sortie} ({os.path.getsize(sortie) / 1e6:.1f} Mo)")
    return sortie


def charger_resultats(source):
    """Lit le fichier préparé (chemin local ou URL)."""
    import gzip
    import io
    import json
    import urllib.request
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=60) as r:
            brut = r.read()
        f = gzip.open(io.BytesIO(brut), "rt", encoding="utf-8")
    else:
        f = gzip.open(source, "rt", encoding="utf-8")
    res = json.load(f)
    res["table"] = pd.DataFrame(res["table"])
    res["finalistes"] = [_dejson(m) for m in res["finalistes"]]
    res["regimes"] = _dejson(res["regimes"])
    res["meteo"] = _dejson(res["meteo"]) if res.get("meteo") else None
    if res.get("backtest"):
        b = _dejson(res["backtest"])
        b["tableau"] = pd.DataFrame(b["tableau"])
        b["courbes"] = pd.DataFrame(b["courbes"])
        res["backtest"] = b
    return res


def cmd_preparer(opts):
    preparer(opts)


# ---- ligne de commande ----

def cmd_scan(opts):
    print(f"Scan de {len(charger_univers(opts.univers))} actions…")
    r = scan(opts, progression=lambda p, t: print(f"  analyse détaillée {p:.0%} {t}      ", end="\r", flush=True))
    titre = f"Radar actions — {dt.date.today():%d/%m/%Y}"
    ecrire_rapport(f"scan_{dt.date.today().isoformat()}.html", page_html(titre, r["regimes"], html_scan(r, opts)), not opts.pas_ouvrir)
    pd.DataFrame([{k: m.get(k) for k in ["ticker", "nom", "note", "verdict", "prix", "r1m", "r6m", "r12_1", "dist52",
                                          "vol", "rsi", "stop", "objectif1", "quantite"]} | m["scores"] for m in r["complet"]]
                 ).to_csv(os.path.join("rapports", f"scan_{dt.date.today().isoformat()}.csv"), sep=";", decimal=",", index=False)
    print("\nTop du jour :")
    for i, m in enumerate(r["top"][:10], 1):
        print(f"  {i:2d}. {m['nom'][:24]:24s} {m['ticker']:10s} note {m['note']:5.1f}  {m['verdict']}")


def cmd_analyse(opts):
    if not opts.actions:
        sys.exit("Indique au moins une action, ex. : python radar_actions.py analyse NVDA ASML.AS")
    r = analyse(opts, opts.actions)
    for e in r["erreurs"]:
        print("  !", e)
    for m in r["actions"]:
        print(f"  {m['nom'][:30]:30s} {m['ticker']:10s} note {m['note']:5.1f}  {m['verdict']}")
    if r["actions"]:
        noms = "_".join(m["ticker"] for m in r["actions"])[:60]
        ecrire_rapport(f"analyse_{noms}_{dt.date.today().isoformat()}.html",
                       page_html("Analyse : " + ", ".join(m["ticker"] for m in r["actions"]), r["regimes"], html_analyse(r, opts)),
                       not opts.pas_ouvrir)


def cmd_backtest(opts):
    b = backtest(opts)
    print(f"\nBacktest {b['debut']} → {b['fin']} ({b['mois']} mois), exposition {b['exposition']:.0%} du temps\n")
    print(b["tableau"].to_string())
    print(f"\nSurperformance mensuelle moyenne vs indice : {b['exces']:+.2%}  (t-stat {b['t']:.2f} ; > 2 = significatif)")
    ecrire_rapport(f"backtest_{opts.univers}_{dt.date.today().isoformat()}.html",
                   page_html("Backtest du score", [], html_backtest(b)), not opts.pas_ouvrir)


def main():
    p = argparse.ArgumentParser(description="Radar actions : sélection quantitative pour le swing trading")
    p.add_argument("commande", choices=["scan", "analyse", "backtest", "preparer"])
    p.add_argument("actions", nargs="*", help="actions à analyser (tickers Yahoo ou noms)")
    p.add_argument("--univers", default="tout", help="pea | europe | us | tout | petites | semis | coeur | fichier.txt")
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--capital", type=float, default=10000)
    p.add_argument("--risque", type=float, default=1.0, help="% du capital risqué par trade")
    p.add_argument("--objectif", type=float, default=20, help="objectif en % pour les probabilités")
    p.add_argument("--horizon", type=int, default=40, help="horizon en jours de bourse")
    p.add_argument("--debut", default="2012-01-01", help="début du backtest")
    p.add_argument("--demo", action="store_true", help="données simulées (test sans internet)")
    p.add_argument("--pas-ouvrir", dest="pas_ouvrir", action="store_true", help="ne pas ouvrir le navigateur")
    p.add_argument("--avec-backtest", dest="avec_backtest", action="store_true", help="preparer : refaire aussi le backtest")
    opts = p.parse_args()
    {"scan": cmd_scan, "analyse": cmd_analyse, "backtest": cmd_backtest, "preparer": cmd_preparer}[opts.commande](opts)


if __name__ == "__main__":
    main()
