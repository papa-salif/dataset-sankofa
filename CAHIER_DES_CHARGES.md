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

## Réponse apportée

- Application Streamlit en assistant pas-à-pas (phrase → traduction → enregistrement → nettoyage optionnel → validation).
- Modèle de données PostgreSQL (via SQLAlchemy) : `contributors`, `sentences`, `translations`, `recordings`.
- Stockage des fichiers audio sur disque (chemin en base, pas de blob) : originaux dans `data/audio/original/`, versions nettoyées dans `data/audio/cleaned/`.
- Nettoyage des silences via `pydub`/`librosa` : coupe les silences de bordure et raccourcit (sans supprimer) les silences internes trop longs.
- Scripts utilitaires : `scripts/init_db.py` (création des tables), `scripts/import_sentences.py` (import de phrases FR), `scripts/export_dataset.py` (export du dataset validé en JSONL).
