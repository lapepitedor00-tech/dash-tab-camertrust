"""
CamerTrust — E3 — Client API
=============================

Point de passage UNIQUE entre l'émulateur (Streamlit) et le service
d'E2. Toute la logique réseau, les timeouts et le repli hors-ligne
(« Plan B ») sont ici : les pages Streamlit n'appellent jamais
`requests` directement.

Contrat d'API utilisé
----------------------
Le contrat ci-dessous reprend le tableau « Référence rapide — les
endpoints du service » du plan de travail (page 9) : c'est la version
que le rapport documente et que le jury voit.

    POST   /users/register            {"phone_number"}                 -> {"user_id","phone_number"}
    DELETE /users/{user_id}
    POST   /transactions/score        {"user_id","amount","type","hour"} -> {"is_fraud","score","motif","latence_ms"}
    GET    /alerts/{user_id}
    POST   /alerts/{alert_id}/respond {"response": 1|2}
    GET    /users/{user_id}/settings
    PUT    /users/{user_id}/settings  {"plafond","plafond_nocturne","liste_blanche","canal_prefere","langue"}
    GET    /users/{user_id}/trustscore
    POST   /reports                   {"user_id","description"}
    POST   /ussd                      {"sessionId","phoneNumber","text"} -> texte brut préfixé CON/END
    GET    /outbox?phone_number=...
    GET    /admin/alerts

⚠️ À VÉRIFIER AVEC E2 avant l'intégration finale (même remarque que celle
laissée par E1→E2 sur les noms de variables) : le suivi de projet indique
que le code déjà livré par E2 expose `/ussd`, `/sms/inbound`,
`/transactions` et `/admin/*` — noms proches mais pas nécessairement
identiques à ceux ci-dessus (ex. `/transactions` vs `/transactions/score`).
Si un nom diffère, ajuster UNIQUEMENT la constante `ROUTES` ci-dessous ou
le corps de la fonction concernée : le reste de l'émulateur n'a pas à
changer.

Mode hors-ligne (Plan B)
--------------------------
Si l'API ne répond pas (service Render endormi, pas de réseau le jour J),
chaque fonction bascule automatiquement sur `demo_backend.py`, qui rejoue
un scénario réaliste en mémoire. `st.session_state['api_online']` indique
l'état courant et est affiché dans la barre latérale de chaque page.

Compte inconnu (404) ≠ API injoignable
----------------------------------------
Un 404 sur une route « /users/{id}/... » ou « /alerts/{id} » signifie que
l'API a bien répondu (elle est donc EN LIGNE) mais qu'aucun compte ne
correspond à cet identifiant côté base de données — cas typique du
compte de démo « C123 » utilisé par `pages/1_📲_Espace_client.py », qui
n'existe réellement que dans `demo_backend.py`, pas dans la vraie base
d'E2. Les fonctions concernées (`get_trustscore`, `get_alerts`,
`get_settings`) lèvent `CompteInconnuError` dans ce cas précis, SANS
marquer l'API hors ligne et SANS basculer sur le simulateur — à charge
de la page appelante de proposer une inscription plutôt que d'afficher
silencieusement des données de démonstration qui ne correspondent à
rien de réel.
"""

from __future__ import annotations

import streamlit as st
import requests

from demo_backend import new_backend

TIMEOUT_S = 4  # le service Render peut être lent au réveil ; voir README


class CompteInconnuError(Exception):
    """L'API a répondu 404 pour cet identifiant : elle est donc EN LIGNE,
    mais aucun compte ne correspond à cet `user_id` côté base de données
    (voir la note « Compte inconnu (404) ≠ API injoignable » ci-dessus).
    À la charge de la page appelante d'offrir une inscription plutôt que
    d'afficher des données de démonstration sans rapport."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"Aucun compte « {user_id} » sur cette API")


def get_api_url() -> str:
    """URL de base de l'API d'E2. Ordre de priorité :
    1. `.streamlit/secrets.toml` (`api_url = "..."`) — utilisé en démo/prod.
    2. Valeur modifiable dans la barre latérale (pratique en développement).
    3. Repli sur l'URL Render par défaut du projet.
    """
    if "api_url" in st.session_state:
        return st.session_state["api_url"]
    try:
        return st.secrets.get("api_url", "https://camertrust.onrender.com")
    except Exception:
        return "https://camertrust.onrender.com"


def get_backend():
    """Instance unique du simulateur de repli, conservée pour la durée de
    la session Streamlit (sinon chaque interaction repartirait de zéro)."""
    if "demo_backend" not in st.session_state:
        st.session_state["demo_backend"] = new_backend()
    return st.session_state["demo_backend"]


def _mark_status(online: bool) -> None:
    st.session_state["api_online"] = online


def is_online() -> bool:
    return st.session_state.get("api_online", False)


def _get(path: str, **kwargs):
    return requests.get(f"{get_api_url()}{path}", timeout=TIMEOUT_S, **kwargs)


def _post(path: str, **kwargs):
    return requests.post(f"{get_api_url()}{path}", timeout=TIMEOUT_S, **kwargs)


def _put(path: str, **kwargs):
    return requests.put(f"{get_api_url()}{path}", timeout=TIMEOUT_S, **kwargs)


def _delete(path: str, **kwargs):
    return requests.delete(f"{get_api_url()}{path}", timeout=TIMEOUT_S, **kwargs)


def check_health() -> bool:
    """Sonde /health. Utilisée par le bouton « Réveiller le service »
    (difficulté documentée par E3 dans le plan : l'instance gratuite de
    Render s'endort après inactivité)."""
    try:
        r = requests.get(f"{get_api_url()}/health", timeout=TIMEOUT_S)
        online = r.status_code == 200
    except requests.RequestException:
        online = False
    _mark_status(online)
    return online


# ---------------------------------------------------------------------------
# Comptes
# ---------------------------------------------------------------------------
def register_user(phone_number: str) -> dict:
    try:
        r = _post("/users/register", json={"phone_number": phone_number})
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().register_user(phone_number)


def delete_user(user_id: str) -> dict:
    try:
        r = _delete(f"/users/{user_id}")
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        r.raise_for_status()
        _mark_status(True)
        return r.json() if r.content else {"deleted": True}
    except CompteInconnuError:
        raise
    except requests.RequestException:
        _mark_status(False)
        return get_backend().delete_user(user_id)


# ---------------------------------------------------------------------------
# Transactions / score
# ---------------------------------------------------------------------------
def score_transaction(user_id: str, amount: int, type_op: str, hour: int,
                       destinataire: str = "numero inconnu") -> dict:
    try:
        r = _post("/transactions/score", json={
            "user_id": user_id, "amount": amount, "type": type_op, "hour": hour,
        })
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().score_transaction(user_id, amount, type_op, hour, destinataire)


# ---------------------------------------------------------------------------
# Alertes
# ---------------------------------------------------------------------------
def get_alerts(user_id: str) -> list[dict]:
    try:
        r = _get(f"/alerts/{user_id}")
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except CompteInconnuError:
        raise
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_alerts(user_id)


def respond_alert(alert_id: str, reponse: int) -> dict:
    try:
        r = _post(f"/alerts/{alert_id}/respond", json={"response": reponse})
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().respond_alert(alert_id, reponse)


# ---------------------------------------------------------------------------
# Réglages / score de confiance
# ---------------------------------------------------------------------------
def get_settings(user_id: str) -> dict:
    try:
        r = _get(f"/users/{user_id}/settings")
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except CompteInconnuError:
        raise
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_settings(user_id)


def put_settings(user_id: str, **kwargs) -> dict:
    payload = {k: v for k, v in kwargs.items() if v is not None}
    try:
        r = _put(f"/users/{user_id}/settings", json=payload)
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except CompteInconnuError:
        raise
    except requests.RequestException:
        _mark_status(False)
        return get_backend().put_settings(user_id, **payload)


def get_trustscore(user_id: str) -> dict:
    try:
        r = _get(f"/users/{user_id}/trustscore")
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except CompteInconnuError:
        raise
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_trustscore(user_id)


def report_fraud(user_id: str, description: str) -> dict:
    try:
        r = _post("/reports", json={"user_id": user_id, "description": description})
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().report_fraud(user_id, description)


# ---------------------------------------------------------------------------
# USSD / SMS
# ---------------------------------------------------------------------------
def ussd_request(session_id: str, phone_number: str, text: str) -> str:
    """Retourne le texte brut préfixé CON/END, exactement comme le
    renverrait un agrégateur réel (voir plan p.7 — E2)."""
    try:
        r = _post("/ussd", data={"sessionId": session_id, "phoneNumber": phone_number, "text": text})
        r.raise_for_status()
        _mark_status(True)
        return r.text
    except requests.RequestException:
        _mark_status(False)
        result = get_backend().ussd(session_id, phone_number, text)
        return result["response"]


def sms_inbound(phone_number: str, texte: str) -> dict:
    try:
        r = _post("/sms/inbound", json={"phone_number": phone_number, "text": texte})
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().sms_inbound(phone_number, texte)


def get_outbox(phone_number: str | None = None) -> list[dict]:
    try:
        params = {"phone_number": phone_number} if phone_number else {}
        r = _get("/outbox", params=params)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_outbox(phone_number)


# ---------------------------------------------------------------------------
# Supervision (opérateur)
# ---------------------------------------------------------------------------
def get_admin_stats() -> dict:
    try:
        r = _get("/admin/alerts", params={"stats": 1})
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_admin_stats()


def get_admin_alerts() -> list[dict]:
    try:
        r = _get("/admin/alerts")
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except requests.RequestException:
        _mark_status(False)
        return get_backend().get_admin_alerts()
