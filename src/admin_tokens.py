import secrets

# Stockage en mémoire, au niveau du process (partagé entre tous les onglets/
# utilisateurs de ce serveur Streamlit) — volontairement pas en base : ces
# jetons ne servent qu'à retenir une session admin déjà authentifiée après un
# rafraîchissement de page, ils sont invalidés au redémarrage du conteneur.
_valid_tokens = set()


def issue_token() -> str:
    token = secrets.token_urlsafe(24)
    _valid_tokens.add(token)
    return token


def is_valid(token) -> bool:
    return bool(token) and token in _valid_tokens


def revoke(token) -> None:
    _valid_tokens.discard(token)
