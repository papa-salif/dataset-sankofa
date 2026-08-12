# Changelog — Collecte de données Français → Mooré

Récapitulatif de tous les changements effectués sur le projet, du scaffold initial à aujourd'hui.

## 1. Socle applicatif (Streamlit + PostgreSQL)

- Structure du projet : `app.py`, `src/` (config, base de données, modèles, stockage, traitement audio, repository), `scripts/`.
- Modèle de données PostgreSQL (SQLAlchemy) : `contributors`, `sentences`, `translations`, `recordings`.
- Parcours contributeur initial : phrase FR → traduction mooré → enregistrement audio → nettoyage optionnel des silences → validation.
- Stockage audio sur disque (chemins en base, pas de blob) : originaux dans `data/audio/original/`, versions nettoyées dans `data/audio/cleaned/` — **l'original n'est jamais modifié**, seule une copie séparée est retouchée.
- Scripts utilitaires : `init_db.py`, `import_sentences.py`, `export_dataset.py`.
- Mise en place de Git : `.gitignore`, premier commit.

## 2. Séparation Admin / Contributeur

- Ajout de `sentences.category` et `sentences.note` (migration `migrate_add_category.py`).
- Bascule en application Streamlit multipage : `app.py` (routeur central) + dossier `app_pages/` (renommé depuis `pages/` — Streamlit interceptait ce dossier comme navigation automatique et contournait le routeur).
- Espace **admin** créé : Overview (statistiques), Bulk Upload (import `.csv/.json/.txt` ou saisie unique), Translation Queue (recherche/filtre), Audio Lab (revue un par un : Trim/Normalize/Reset, puis Approve/Reject), Export.
- Accès admin protégé par mot de passe partagé (`ADMIN_PASSWORD`).
- **Navigation dynamique par rôle** : les pages admin ne sont même pas listées dans la barre latérale d'un contributeur (pas seulement protégées par mot de passe).
- Bug corrigé : `st.audio_input` n'avait pas de `key` unique par phrase, donc Streamlit réutilisait le même widget (et le même flux micro) entre deux phrases — l'ancien enregistrement pouvait rester accroché.

## 3. Déploiement Docker

- `Dockerfile` (Python 3.12-slim + ffmpeg + utilisateur non-root + healthcheck), `.dockerignore`, `docker-compose.yml`.
- Connexion au conteneur PostgreSQL existant via `host.docker.internal` (pas de duplication de données).

## 4. HTTPS pour l'accès micro (Caddy)

- Ajout d'un service **Caddy** en reverse-proxy avec certificat auto-signé (`tls internal`), car les navigateurs bloquent l'accès micro (`getUserMedia`) sur toute page en HTTP simple hors `localhost`.
- Correction de deux pièges Caddy rencontrés en cours de route :
  - le port dans le Caddyfile doit toujours être le port **interne au conteneur** (443), jamais le port externe choisi côté hôte ;
  - ajout de l'option `default_sni` : sans elle, Caddy ne sait pas quel certificat présenter quand un client se connecte via une **IP nue** (pas de SNI envoyé), ce qui est justement l'usage réel de l'app.

## 5. Persistance de session au rafraîchissement

- La session ne se perdait plus au rafraîchissement (F5) : identité stockée dans les paramètres d'URL.
- Admin : jeton aléatoire (`src/admin_tokens.py`, en mémoire côté serveur) revalidé à chaque chargement — impossible de deviner/forcer l'accès.
- Réparation du conteneur PostgreSQL local, arrêté sans politique de redémarrage (`docker update --restart=unless-stopped postgres`).

## 6. Identification unique des contributeurs

- Ajout de `contributors.code` (identité unique, ex. `CTR-95AG`), retrait de l'ancienne contrainte d'unicité sur `name` (deux personnes peuvent avoir choisi le même nom).
- Migration `migrate_add_contributor_code.py` (génère un code pour les contributeurs déjà existants, sans perte de données).
- Refonte du flux de connexion en assistant pas-à-pas : on ne demande que le nom au départ ; si c'est « admin » → mot de passe ; sinon → étape suivante proposant de saisir un code existant, d'en créer un nouveau, ou de retrouver un code oublié (recherche par nom, avec choix si plusieurs comptes correspondent).

## 7. Suivi des paiements contributeurs

- Page admin **Paiements** : durée totale enregistrée par contributeur (mm:ss) et montant à verser, calculé selon un tarif ajustable (par minute ou par seconde).
- Page contributeur **Mes gains** : ses propres statistiques (enregistrements validés / en attente / rejetés) et le montant estimé, au tarif fixe défini par l'admin (`CURRENCY`, `DEFAULT_RATE_PER_MINUTE`).

## 8. Export du dataset avec audio

- Passage de JSONL à **JSON** valide pour les exports.
- Ajout d'une section « Phrases encore à traduire » dans l'export, pour toujours savoir ce qu'il reste à faire.
- Nouveau : export en **archive ZIP** autonome (`src/export_utils.py`) contenant un `manifest.json` et les fichiers audio réels (version nettoyée si elle existe, sinon l'originale) — prête à être importée dans un pipeline d'entraînement, sans dépendre des chemins du serveur.
- Bug corrigé : certains chemins audio étaient stockés avec des antislashs Windows, invisibles depuis les conteneurs Linux (fichiers introuvables à l'export). Correction de `storage.py`/`config.py` (chemins toujours en `/`) + script de réparation des données existantes (`fix_audio_path_separators.py`).

## 9. Page de gestion (CRUD)

- Nouvelle page admin **Gestion** : recherche/filtre des phrases, avec pour chacune :
  - modification ou suppression de la phrase (et en cascade ses traductions + audio, avec confirmation) ;
  - modification ou suppression de chaque traduction ;
  - **écoute de l'audio même s'il est déjà validé**, changement manuel du statut, suppression de l'enregistrement (fichier + base).
