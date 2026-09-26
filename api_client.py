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

Numéro déjà inscrit (409) ≠ API injoignable
---------------------------------------------
Même principe pour `register_user` : un 409 sur `/users/register`
signifie que l'API a bien répondu (EN LIGNE) mais que ce numéro est déjà
inscrit — `register_user` lève alors `NumeroDejaInscritError` plutôt que
de basculer sur le simulateur (voir cette exception ci-dessous pour le
détail du bug que cela corrige).
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


class NumeroDejaInscritError(Exception):
    """L'API a répondu 409 sur `/users/register` : elle est donc EN LIGNE,
    mais ce numéro est déjà inscrit (et pas désinscrit) côté serveur —
    voir `api/routers/users.py::inscrire` d'E2. Même famille de bug que
    `CompteInconnuError` ci-dessus : sans cette distinction, `raise_for_status()`
    transforme ce 409 (réponse parfaitement normale de l'API) en
    `requests.HTTPError`, capté par le `except requests.RequestException`
    générique, qui bascule alors à tort en mode démo hors ligne — observé
    en pratique quand on clique « S'inscrire » sans changer le numéro
    proposé par défaut dans `_ecran_compte_inconnu` (voir
    `pages/1_📲_Espace_client.py`), déjà inscrit lors d'un essai
    précédent. Les numéros n'étant JAMAIS stockés en clair (hachage
    côté E2), il n'existe aucune route pour retrouver l'identifiant de
    compte à partir du numéro : à charge de la page appelante de le dire
    clairement plutôt que d'afficher un faux compte de démonstration."""

    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        super().__init__(f"Le numéro « {phone_number} » est déjà inscrit")


class CompteBloqueError(Exception):
    """L'API a répondu 403 sur `/transactions/score` : elle est donc EN
    LIGNE, mais ce compte est actuellement bloqué (réponse « 2 » à une
    alerte précédente, blocage réel de 30 min — voir
    `routers/transactions.py::scorer` d'E2). Distinct d'une vraie panne
    réseau pour la même raison que les exceptions ci-dessus."""

    def __init__(self, user_id: str, detail: str = ""):
        self.user_id = user_id
        self.detail = detail
        super().__init__(f"Compte « {user_id} » temporairement bloqué")


class AlerteInconnueError(Exception):
    """L'API a répondu 404 sur `/alerts/{alert_id}/respond` : elle est
    donc EN LIGNE, mais cet `alert_id` n'existe pas côté serveur (voir
    `routers/alerts.py::repondre_alerte` d'E2) — typiquement une alerte
    encore affichée localement (cache) alors qu'elle vient d'un scénario
    de démonstration hors ligne et n'a donc jamais existé sur cette API."""

    def __init__(self, alert_id: str):
        self.alert_id = alert_id
        super().__init__(f"Alerte « {alert_id} » inconnue sur cette API")


class AlerteDejaTraiteeError(Exception):
    """L'API a répondu 409 sur `/alerts/{alert_id}/respond` : elle est
    donc EN LIGNE, mais cette alerte a déjà reçu une réponse (statut ≠
    "en_attente" côté serveur) — par ex. un double clic, ou un onglet
    resté ouvert avec un cache local périmé."""

    def __init__(self, alert_id: str, statut_actuel: str = ""):
        self.alert_id = alert_id
        self.statut_actuel = statut_actuel
        super().__init__(f"Alerte « {alert_id} » déjà traitée ({statut_actuel})")


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
        if r.status_code == 409:
            _mark_status(True)
            raise NumeroDejaInscritError(phone_number)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except NumeroDejaInscritError:
        raise
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
    # Même famille de bug que `CompteInconnuError`/`NumeroDejaInscritError`
    # ci-dessus : `routers/transactions.py::scorer` d'E2 répond 404 si
    # `user_id` n'existe pas (ou est désinscrit) et 403 si le compte est
    # actuellement bloqué — deux réponses parfaitement normales d'une API
    # EN LIGNE. Sans cette distinction, `raise_for_status()` les
    # transforme en `requests.HTTPError`, capté par le
    # `except requests.RequestException` générique, qui bascule alors à
    # tort en mode démo hors ligne : observé en pratique avec le panneau
    # « Simuler une transaction suspecte » d'`app.py`, qui ciblait un
    # `user_id` fixe non garanti d'exister sur l'API réelle — la
    # transaction finissait alors scorée uniquement par
    # `demo_backend.py` (en mémoire, invisible de la vraie base), d'où le
    # symptôme « rien ne change sur la Console de supervision ni sur les
    # alertes détectées » malgré un message de succès affiché.
    try:
        r = _post("/transactions/score", json={
            "user_id": user_id, "amount": amount, "type": type_op, "hour": hour,
        })
        if r.status_code == 404:
            _mark_status(True)
            raise CompteInconnuError(user_id)
        if r.status_code == 403:
            _mark_status(True)
            detail = ""
            try:
                detail = r.json().get("detail", "")
            except ValueError:
                pass
            raise CompteBloqueError(user_id, detail)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except (CompteInconnuError, CompteBloqueError):
        raise
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
    # Même famille de bug que `score_transaction`/`CompteInconnuError`
    # ci-dessus : `routers/alerts.py::repondre_alerte` d'E2 répond 404 si
    # `alert_id` n'existe pas et 409 si l'alerte a déjà reçu une réponse —
    # deux réponses normales d'une API EN LIGNE, à ne pas confondre avec
    # une panne réseau (sans quoi la réponse de l'abonné — pourtant
    # cruciale, c'est la boucle de retour d'E1 — serait enregistrée
    # uniquement dans le simulateur hors ligne, invisible de la vraie
    # base et de la Console de supervision).
    try:
        r = _post(f"/alerts/{alert_id}/respond", json={"response": reponse})
        if r.status_code == 404:
            _mark_status(True)
            raise AlerteInconnueError(alert_id)
        if r.status_code == 409:
            _mark_status(True)
            statut_actuel = ""
            try:
                statut_actuel = r.json().get("detail", "")
            except ValueError:
                pass
            raise AlerteDejaTraiteeError(alert_id, statut_actuel)
        r.raise_for_status()
        _mark_status(True)
        return r.json()
    except (AlerteInconnueError, AlerteDejaTraiteeError):
        raise
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
    # Même famille de bug que les autres fonctions ci-dessus (voir
    # `routers/reports.py::signaler` d'E2 : 404 si `user_id` est inconnu,
    # une réponse normale d'une API en ligne) — pas de point d'appel dans
    # l'interface actuelle (le signalement via le menu USSD passe par
    # `/ussd`, pas cette route REST), mais corrigé par cohérence pour
    # toute future page qui l'utiliserait directement.
    try:
        r = _post("/reports", json={"user_id": user_id, "description": description})
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
