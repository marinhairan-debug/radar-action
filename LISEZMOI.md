# Radar actions — mise en ligne (≈ 5 100 actions PEA BoursoBank + Trade Republic, Europe, États-Unis, Japon, accessible depuis n'importe quel PC)

## Comment ça marche

1. **Chaque soir de bourse**, un robot gratuit de GitHub (« GitHub Actions ») télécharge les cours des
   ≈ 5 100 actions (celles achetables sur ton PEA BoursoBank ou chez Trade Republic), calcule les notes, analyse en détail les meilleures (probabilités, fondamentaux),
   lit la météo économique, et range le résultat dans un fichier. Le samedi, il refait aussi le backtest.
2. **L'appli web** (Streamlit) lit simplement ce fichier : elle s'ouvre en quelques secondes,
   depuis n'importe quel PC ou téléphone, sans rien installer.
3. **L'analyse d'une action que tu proposes** se fait en direct, à la demande.

Tout est gratuit. Mise en place : environ 30 minutes, une seule fois.

---

## Étape 1 — Mettre les fichiers sur GitHub

1. Crée un compte sur https://github.com.
2. **+** en haut à droite > **New repository** > nom : `radar-actions` > **Public** > **Create repository**.
3. Clique **uploading an existing file** et glisse : `app.py`, `radar_actions.py`, `macro.py`,
   `univers.csv`, `requirements.txt`, `.gitignore`, `portefeuille.py`. Clique **Commit changes**.
4. Le robot du soir : **Add file** > **Create new file**. Dans le nom, tape exactement
   `.github/workflows/radar.yml` (les « / » créent les dossiers tout seuls).
   Colle le contenu du fichier `radar.yml` fourni, puis **Commit changes**.

## Étape 2 — Lancer le premier calcul

1. Onglet **Actions** du dépôt. Si GitHub le demande, clique sur le bouton vert pour activer les workflows.
2. Clique **Calcul du radar** à gauche > **Run workflow** > **Run workflow**.
3. Attends que la pastille devienne verte (30 à 90 minutes, c'est normal : 5 100 actions, deux styles de score).
4. Une branche **donnees** apparaît dans le dépôt, avec le fichier `resultats.json.gz`.

Ensuite, il se relance tout seul chaque soir (23 h 30, heure de Paris, en hiver).

Si la pastille est rouge : clique dessus, puis sur l'étape en erreur, et envoie une capture à Claude.

## Étape 3 — Mettre l'appli en ligne

1. Va sur https://share.streamlit.io et connecte-toi **avec ton compte GitHub**.
2. **Create app** > **Deploy a public app from GitHub** > dépôt `ton-pseudo/radar-actions`,
   branche `main`, fichier `app.py`. Choisis une adresse, par exemple `radar-marin.streamlit.app`.
3. **Advanced settings** > **Secrets**, colle (en remplaçant TON-PSEUDO et le mot de passe) :

   ```
   MOT_DE_PASSE = "ton-mot-de-passe"
   RESULTATS_URL = "https://raw.githubusercontent.com/TON-PSEUDO/radar-actions/donnees/resultats.json.gz"
   ```

4. **Deploy**. Mets l'adresse dans tes favoris : c'est fini.

## Étape 4 — Garder mon portefeuille (dépôt privé, 5 minutes)

Tes positions sont rangées dans un **second dépôt, privé** : personne d'autre ne peut les voir.

1. GitHub : **+** > **New repository** > nom `radar-portefeuille` > **Private** > coche **Add a README** > **Create**.
2. Crée une clé d'accès limitée à ce seul dépôt : photo de profil > **Settings** > tout en bas **Developer settings** >
   **Personal access tokens** > **Fine-grained tokens** > **Generate new token**.
   - Nom : `radar-portefeuille` · Expiration : 1 an (ou « No expiration »).
   - **Repository access** > **Only select repositories** > `radar-portefeuille`.
   - **Permissions** > **Repository permissions** > **Contents** : **Read and write**.
   - **Generate token**, puis copie le code `github_pat_…` (il ne s'affiche qu'une fois).
3. Streamlit : ton appli > **⋮** > **Settings** > **Secrets**, ajoute (en plus de ce qui y est déjà) :

   ```
   PORTEFEUILLE_TOKEN = "github_pat_..."
   PORTEFEUILLE_REPO = "TON-PSEUDO/radar-portefeuille"
   ```

   ⚠️ `MOT_DE_PASSE` est **obligatoire** dès que le portefeuille est branché (sinon l'onglet refuse de s'afficher).
4. Pour le suivi automatique du soir : dépôt **public** `radar-action` > **Settings** > **Secrets and variables** >
   **Actions** > **New repository secret** : `PORTEFEUILLE_TOKEN` (le même code) puis `PORTEFEUILLE_REPO`.

Sans cette étape, l'onglet « Mon portefeuille » marche quand même, mais ne garde rien après fermeture
(bouton pour télécharger / recharger le fichier).

---

## Bon à savoir

- **Deux styles de score** (choix en barre de gauche) :
  - **Sous-cotées qui se retournent** (par défaut) : PER et cours/actif net comparés à la médiane du secteur,
    rendement de trésorerie, décote sous le plus haut annuel, retour à la moyenne sur 2 ans, objectif des analystes,
    contrôle qualité (rentabilité, dette, croissance) pour éviter les pièges, et signaux de retournement
    (reprise de la moyenne 50 j, RSI qui remonte, plus bas montants, accumulation). Pénalité « couteau qui tombe ».
  - **Momentum** : l'ancien score, actions déjà en tendance.
  - Le backtest ne teste que la partie cours de chaque style : l'historique des fondamentaux n'existe pas gratuitement.
- **Univers « PEA BoursoBank »** : sociétés de l'UE cotées à Paris, Amsterdam, Bruxelles, Lisbonne (sans minimum),
  plus Francfort/Xetra, Madrid, Milan où BoursoBank impose un **ordre d'au moins 2 500 €** (signalé dans le plan).
  **« CTO Trade Republic »** : uniquement les actions de la liste officielle Trade Republic (« Univers d'investissement »,
  novembre 2026), reconnues par leur code ISIN : ≈ 4 400 actions américaines et européennes. Pour mettre la liste à jour,
  renvoie le nouveau PDF à Claude.
- **Japon & Asie** : ≈ 570 actions japonaises de la liste Trade Republic, plus SK Hynix, Samsung, Samsung SDI,
  LG Electronics, Foxconn et AUO (analysées sur leur bourse locale, achetées chez Trade Republic sous forme de
  certificat ADR/GDR, indiqué sur la fiche). Chaque action est comparée à son propre indice (Nikkei, Kospi, Taiex)
  et aux valorisations de sa région. Attention : chez Trade Republic, l'ordre passe pendant que Tokyo est fermé
  (écart de prix plus large, ordre à cours limité, risque d'écart la nuit). Pas de météo économique pour l'Asie.
- **Devises** : tailles de position et liquidité converties en euros (taux mis à jour chaque nuit).

- **Univers** : ≈ 5 100 actions (≈ 850 éligibles PEA BoursoBank, ≈ 5 000 chez Trade Republic, dont ≈ 580 japonaises), des géantes
  aux petites. Les micro-valeurs trop peu échangées sont exclues. Filtre par univers et par taille dans
  la barre de gauche. Filtre aussi par secteur si tu veux (vide = tous les secteurs). La liste est dans `univers.csv` (modifiable sur GitHub).
- **Si Yahoo bloque le robot** (beaucoup d'actions « sans données » dans le journal du calcul),
  solution gratuite : fais le calcul sur ton PC, où Yahoo fonctionne, puis dépose le fichier sur GitHub.
  1. Sur ton PC (une fois) : installe Python, puis `pip install -r requirements.txt`.
  2. Le soir : `python radar_actions.py preparer` (20 à 60 min). Le fichier est créé dans `resultats/`.
  3. Sur GitHub : choisis la branche **donnees** (menu des branches en haut à gauche),
     **Add file** > **Upload files**, dépose `resultats.json.gz`, **Commit changes**.
     L'appli en ligne affiche le nouveau classement dans la demi-heure.
  (Option payante si tu changes d'avis : clé EODHD, ~20 $/mois, à mettre dans
  **Settings** > **Secrets and variables** > **Actions** > secret `EODHD_API_KEY`.)
- **Le robot s'arrête après 60 jours sans activité sur le dépôt** (règle de GitHub) : si le calcul
  n'est plus à jour, va dans **Actions** et réactive le workflow.
- **Modifier l'outil** : sur GitHub, ouvre le fichier, clique sur le crayon, **Commit changes**.

## En local (optionnel)

```
pip install -r requirements.txt
python radar_actions.py preparer        # calcul complet (long)
streamlit run app.py                    # l'appli lit resultats/resultats.json.gz
python radar_actions.py analyse NVDA MC.PA
```
