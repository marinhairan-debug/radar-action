# Radar actions — mise en ligne (5 700 actions, accessible depuis n'importe quel PC)

## Comment ça marche

1. **Chaque soir de bourse**, un robot gratuit de GitHub (« GitHub Actions ») télécharge les cours des
   5 752 actions, calcule les notes, analyse en détail les meilleures (probabilités, fondamentaux),
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
   `univers.csv`, `requirements.txt`, `.gitignore`. Clique **Commit changes**.
4. Le robot du soir : **Add file** > **Create new file**. Dans le nom, tape exactement
   `.github/workflows/radar.yml` (les « / » créent les dossiers tout seuls).
   Colle le contenu du fichier `radar.yml` fourni, puis **Commit changes**.

## Étape 2 — Lancer le premier calcul

1. Onglet **Actions** du dépôt. Si GitHub le demande, clique sur le bouton vert pour activer les workflows.
2. Clique **Calcul du radar** à gauche > **Run workflow** > **Run workflow**.
3. Attends que la pastille devienne verte (20 à 60 minutes la première fois, c'est normal : 5 700 actions).
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

---

## Bon à savoir

- **Univers** : 5 752 actions (Europe 2 048 dont 1 425 éligibles PEA, États-Unis 3 704), des géantes
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
