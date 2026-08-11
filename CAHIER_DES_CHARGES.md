# Cahier des charges — Collecte de données Français → Mooré

## Objectif

Construire un dataset (français / mooré / audio) destiné à entraîner des modèles de langue, via une application de collecte permettant à des contributeurs de traduire et d'enregistrer des phrases.

## Parcours utilisateur souhaité

1. **Affichage d'une phrase en français** à traduire.
2. **Construction de l'équivalent en mooré** (saisie texte par le contributeur).
3. **Enregistrement de l'audio** correspondant à la phrase en mooré.
4. **Peaufinage de l'audio** : traitement des moments de silence (si possible).
5. **Enregistrement de toutes ces données en base**, dans une configuration adaptée.

## Contraintes explicites

- Les fichiers audio doivent être **conservés dans leur état d'origine** : pas de conversion/transcodage du fichier brut. Un éventuel traitement (nettoyage des silences) doit produire une **copie séparée**, sans jamais modifier l'original.
- La base de données doit être structurée « dans la bonne configuration qu'il faut » pour ce type de dataset (phrases, traductions, enregistrements, contributeurs reliés entre eux).

## Choix technologiques validés

- **Langage** : Python
- **Interface** : Streamlit
- **Base de données** : PostgreSQL (choisi directement, sans passer par SQLite)

## Évolution : séparation Admin / Contributeur

En s'inspirant de maquettes de référence (« Sahel Echo » / « Admin Console — Linguist Data Collector »), l'application a été scindée en deux espaces :

- **Espace contributeur** : login léger (nom + taille de session), barre de progression, phrase avec catégorie/note, étape traduction puis étape enregistrement, boutons « Passer » / « Valider ». Sélectionne la phrase à proposer en priorisant celles ayant le moins de traductions (plusieurs contributeurs peuvent traduire/enregistrer la même phrase).
- **Espace admin** (protégé par mot de passe partagé) : Overview (statistiques), Bulk Upload (import .csv/.json/.txt ou saisie unique), File de traduction (recherche/filtre par catégorie), Audio Lab (revue d'un enregistrement à la fois : Trim/Normalize/Reset, puis Approve/Reject), Export (téléchargement JSONL filtré sur les enregistrements validés).

Ajout au modèle de données : `sentences.category` (obligatoire léger, utile pour équilibrer la couverture par domaine) et `sentences.note` (optionnel, pour lever une ambiguïté de traduction) — décision : pas de champ « contexte » libre systématique, jugé trop coûteux à produire pour la valeur qu'il apporte à un modèle multi-domaines.

## Réponse apportée

- Application Streamlit multipage : `app.py` (accueil) + `pages/1_Contributeur.py` + `pages/2..6_Admin_*.py`.
- Modèle de données PostgreSQL (via SQLAlchemy) : `contributors`, `sentences` (+ `category`, `note`), `translations`, `recordings` (avec `status` pending/validated/rejected).
- Stockage des fichiers audio sur disque (chemin en base, pas de blob) : originaux dans `data/audio/original/`, versions nettoyées dans `data/audio/cleaned/` — l'original n'est jamais réécrit, y compris lors des retouches faites dans l'Audio Lab.
- Traitement audio (`src/audio_processing.py`) : Trim (silences de bordure + silences internes raccourcis) et Normalize (volume), via `pydub`.
- Accès admin protégé par mot de passe partagé (`ADMIN_PASSWORD` en `.env`), vérifié par `src/auth.py`.
- Scripts utilitaires : `scripts/init_db.py` (création des tables), `scripts/migrate_add_category.py` (migration additive sans perte de données), `scripts/import_sentences.py` (import CLI), `scripts/export_dataset.py` (export CLI).
