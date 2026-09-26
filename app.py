"""
CamerTrust — E3 — Émulateur de terminal (page principale)
===========================================================

C'est la pièce maîtresse de la démo (plan p.11) : « le jury ne regarde pas
des courbes, il voit un téléphone qui reçoit une alerte et un doigt qui
répond « 2 »." Cette page réunit :

  1. Le terminal USSD (*888#) — S2 puis S5 du plan.
  2. La boîte de réception SMS simulée, avec réponse « 1 »/« 2 » en un
     clic — S6 du plan.

Les deux autres livrables d'E3 (espace client smartphone, console de
supervision) sont dans `pages/`, comme le veut le multipage natif de
Streamlit.

Lancement : `streamlit run app.py` depuis le dossier `dashboard/`.
"""

from __future__ import annotations

import uuid

import streamlit as st
from PIL import Image

import api_client
from api_client import (
    AlerteDejaTraiteeError,
    AlerteInconnueError,
    CompteBloqueError,
    CompteInconnuError,
)
from style import LOGO_PATH, PHONE_CSS, app_header, badge, bottom_nav, settings_trigger

# Identifiant de démonstration hors ligne — n'existe QUE dans
# `demo_backend.py` (voir la note juste en dessous, sur le panneau
# "Simuler une transaction suspecte").
USER_ID_DEMO_HORS_LIGNE = "C123"

st.set_page_config(
    page_title="CamerTrust — Émulateur",
    page_icon=Image.open(LOGO_PATH),
    layout="wide",
)
st.markdown(PHONE_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Numéros de démonstration — pré-remplis pour ne jamais laisser le jury
# face à un champ vide. C123 correspond au scénario amorcé par le
# simulateur de repli (demo_backend.py) : une alerte est déjà en attente.
# ---------------------------------------------------------------------------
NUMEROS_DEMO = {
    "Abonné de démo (alerte déjà en attente)": "+237690000123",
    "Nouvel abonné (à inscrire)": "+237691234567",
}


def _init_state() -> None:
    defaults = {
        "phone_number": NUMEROS_DEMO["Abonné de démo (alerte déjà en attente)"],
        "session_id": None,
        "accumulated": [],       # étapes USSD déjà envoyées, ex. ["3", "1", "500000"]
        "current_screen": "Composez *888# pour démarrer une session.",
        "session_active": False,
        "keypad_buffer": "",
        "api_url": api_client.get_api_url(),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


_init_state()


# ---------------------------------------------------------------------------
# Réglages de démo — loi de Hick : seuls les 2-3 choix vraiment utiles
# pendant une démonstration restent visibles d'emblée (l'abonné simulé,
# l'état de la connexion) ; le reste — réglages techniques, scénario de
# transaction — est replié dans des panneaux secondaires.
#
# Cette fonction est appelée deux fois : depuis la barre latérale (bureau)
# et depuis le popover ⚙️ affiché sur la page (mobile, barre latérale
# masquée — voir PHONE_CSS et `settings_trigger`) ; `suffix` distingue les
# clés des deux jeux de widgets tout en gardant un seul état partagé
# (`st.session_state`), donc les deux surfaces restent synchronisées.
# ---------------------------------------------------------------------------
def _on_api_url_change(suffix: str) -> None:
    """`_render_demo_settings` est appelée deux fois (barre latérale +
    popover mobile ⚙️), donc DEUX widgets `st.text_input` indépendants
    affichent la même URL. `st.popover` exécute son contenu à CHAQUE
    rechargement, même fermé — le jumeau caché est donc bien instancié en
    permanence, pas seulement à l'ouverture.

    Piège Streamlit : passer `value=st.session_state["api_url"]` à un
    widget ne fixe sa valeur affichée qu'à sa toute PREMIÈRE instanciation
    — aux rechargements suivants, le widget garde sa propre valeur
    mémorisée (celle de son premier rendu) et ignore `value=`. Sans ce
    callback, le jumeau jamais retouché par l'utilisateur revenait donc
    silencieusement à son ancienne valeur à chaque rechargement, et
    écrasait la nouvelle URL tout juste saisie dans l'autre champ — un
    utilisateur pouvait ainsi voir son URL Railway/Render « ne pas
    tenir ». On force ici explicitement les DEUX widgets (et l'état
    partagé) à la même valeur à chaque changement, des deux côtés."""
    nouvelle_url = st.session_state[f"api_url_input_{suffix}"]
    st.session_state["api_url"] = nouvelle_url
    autre_suffixe = "m" if suffix == "sb" else "sb"
    st.session_state[f"api_url_input_{autre_suffixe}"] = nouvelle_url


def _render_demo_settings(suffix: str) -> None:
    choix_numero = st.selectbox(
        "Abonné simulé", list(NUMEROS_DEMO.keys()), key=f"subscriber_choice_{suffix}",
    )
    nouveau_numero = NUMEROS_DEMO[choix_numero]
    if nouveau_numero != st.session_state["phone_number"]:
        st.session_state["phone_number"] = nouveau_numero
        st.session_state["session_id"] = None
        st.session_state["accumulated"] = []
        st.session_state["session_active"] = False
        st.session_state["current_screen"] = "Composez *888# pour démarrer une session."

    st.caption(st.session_state["phone_number"])
    if not api_client.is_online():
        st.caption(
            "Aucune réponse de l'API — l'émulateur rejoue un scénario local "
            "réaliste (`demo_backend.py`) pour que la démo reste jouable."
        )

    with st.expander("🔧 Réglages avancés"):
        # Pas de `value=` ici : Streamlit prévient à juste titre qu'on ne
        # doit pas fixer à la fois `value=` ET écrire dans
        # `st.session_state[clé]` (ce que fait `_on_api_url_change` pour
        # synchroniser le jumeau) — seul `st.session_state.setdefault`
        # initialise ce widget à son premier rendu ; ensuite, `key=` seul
        # suffit à le relier à l'état partagé.
        st.session_state.setdefault(f"api_url_input_{suffix}", st.session_state["api_url"])
        st.text_input(
            "URL de l'API (E2)", key=f"api_url_input_{suffix}",
            on_change=_on_api_url_change, args=(suffix,),
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Vérifier", width='stretch', key=f"check_health_{suffix}"):
                api_client.check_health()
        with col_b:
            if st.button("⏰ Réveiller", width='stretch', key=f"wake_{suffix}"):
                with st.spinner("Ping /health (jusqu'à 10 min si l'instance dormait)…"):
                    api_client.check_health()

    # Bug « le message de résultat n'apparaît pas après avoir cliqué sur
    # Envoyer la transaction » (constaté en testant automatiquement ce
    # panneau, y compris après une première tentative de correctif) :
    # `st.expander(...)` SANS `expanded=` se referme à CHAQUE rerun, et
    # `expanded=st.session_state[...]` lu en tête de fonction garde
    # l'ANCIENNE valeur pendant le rerun déclenché par le clic lui-même
    # (le `st.session_state[cle_expander] = True` ci-dessous n'est relu
    # qu'au rerun SUIVANT) — st.error/st.warning/st.success s'exécutaient
    # donc bien, mais dans un panneau encore replié au moment où Streamlit
    # dessine cette page, invisibles tant qu'on ne rouvrait pas le panneau
    # à la main. Corrigé en deux temps : (1) un `st.rerun()` explicite
    # juste après le clic, comme pour le bouton *888# plus bas, pour que le
    # panneau se redessine bien `expanded=True` dès l'affichage suivant ;
    # (2) comme ce rerun repart de zéro (le clic n'est « vrai » que pour un
    # seul run), le RÉSULTAT lui-même est mémorisé dans st.session_state
    # plutôt que simplement affiché une fois, pour survivre à ce rerun.
    cle_expander = f"expander_tx_ouvert_{suffix}"
    cle_resultat = f"resultat_tx_{suffix}"
    with st.expander("💡 Simuler une transaction suspecte", expanded=st.session_state.get(cle_expander, False)):
        # Cible le compte RÉEL inscrit depuis l'Espace client s'il y en a
        # un dans cette session (`espace_user_id`), sinon le compte de
        # démo hors ligne. Avant ce correctif, "C123" était ciblé en dur
        # ici : sur l'API réelle, ce compte n'existe presque jamais (E2
        # génère des identifiants aléatoires), donc `score_transaction`
        # recevait un 404 « Compte inconnu » — une réponse normale d'une
        # API bien en ligne, mais confondue avec une panne réseau (voir
        # `score_transaction` dans `api_client.py`) : la transaction était
        # alors scorée en silence par le simulateur hors ligne
        # (`demo_backend.py`, en mémoire) au lieu de la vraie API, d'où le
        # symptôme « bascule en mode démo, rien ne change sur la Console
        # de supervision ni sur les alertes détectées » malgré le message
        # de succès affiché ci-dessous.
        cible = st.session_state.get("espace_user_id", USER_ID_DEMO_HORS_LIGNE)
        st.caption(f"Compte ciblé : {cible}" + (
            " (démo hors ligne)" if cible == USER_ID_DEMO_HORS_LIGNE else " (inscrit depuis l'Espace client)"
        ))
        st.caption("Injecte une transaction pour déclencher une alerte, comme le ferait un vrai flux transactionnel côté opérateur.")
        montant = st.number_input("Montant (FCFA)", min_value=1000, value=450_000, step=10_000, key=f"montant_{suffix}")
        heure = st.slider("Heure de la transaction", 0, 23, 2, key=f"heure_{suffix}")
        type_op = st.selectbox("Type d'opération", ["retrait", "transfert"], key=f"type_op_{suffix}")
        if st.button("Envoyer la transaction", width='stretch', key=f"send_tx_{suffix}"):
            st.session_state[cle_expander] = True
            try:
                with st.spinner("Envoi de la transaction…"):
                    res = api_client.score_transaction(
                        user_id=cible, amount=int(montant), type_op=type_op, hour=int(heure),
                    )
            except CompteInconnuError:
                st.session_state[cle_resultat] = (
                    "error",
                    f"Le compte « {cible} » n'existe pas sur cette API — inscrivez-vous "
                    "d'abord depuis l'Espace client, ou repassez en mode démo pour tester "
                    "sans compte réel.",
                )
            except CompteBloqueError as exc:
                st.session_state[cle_resultat] = (
                    "warning",
                    f"Compte « {cible} » actuellement bloqué : {exc.detail or 'blocage temporaire en cours.'}",
                )
            else:
                if res.get("is_fraud"):
                    st.session_state[cle_resultat] = (
                        "success",
                        "Transaction risquée détectée — une alerte vient d'être envoyée à l'abonné (voir la boîte SMS).",
                    )
                else:
                    st.session_state[cle_resultat] = (
                        "info",
                        "Transaction jugée conforme aux habitudes — aucune alerte envoyée.",
                    )
            st.rerun()

        # Affiche le résultat de la dernière transaction envoyée : mémorisé
        # dans st.session_state (voir le commentaire ci-dessus) pour rester
        # visible après le `st.rerun()` qui garde ce panneau ouvert.
        if cle_resultat in st.session_state:
            type_message, texte_message = st.session_state[cle_resultat]
            getattr(st, type_message)(texte_message)


# ---------------------------------------------------------------------------
# Barre latérale — bureau uniquement. Sur mobile, Streamlit la range dans
# un panneau qu'il faut ouvrir puis faire défiler pour l'atteindre : on la
# masque entièrement (voir PHONE_CSS) et on la remplace par la barre de 3
# icônes en bas de l'écran (`bottom_nav`) plus l'icône ⚙️ sur la page pour
# ces mêmes réglages (`settings_trigger`) — rien n'est perdu, juste rendu
# accessible sans détour par un panneau caché.
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Réglages de démo")
    _render_demo_settings("sb")


# ---------------------------------------------------------------------------
# Mise en page : terminal USSD à gauche, boîte SMS à droite.
# ---------------------------------------------------------------------------
st.markdown(app_header("Terminal abonné"), unsafe_allow_html=True)

# Visibilité de l'état du système (Nielsen) : affichée directement sur la
# page plutôt que seulement dans la barre latérale, pour rester visible
# même sur mobile où celle-ci est masquée.
online = api_client.is_online()
st.markdown(
    badge("🟢 API en ligne" if online else "🔴 Mode démo hors ligne (Plan B)", "success" if online else "danger"),
    unsafe_allow_html=True,
)
st.caption("Vue exacte de ce que verrait un abonné sur un téléphone à touches : USSD *888# et SMS.")

# Icône ⚙️ : sur mobile seulement (voir PHONE_CSS), reprend ici les mêmes
# réglages que la barre latérale de bureau.
settings_trigger(lambda: _render_demo_settings("m"))

col_ussd, col_sms = st.columns([1, 1.2], gap="large")

# --- Colonne terminal USSD -------------------------------------------------
with col_ussd:
    # Tout l'écran de dialogue (titre, écran simulé, clavier, actions) est
    # regroupé dans un même conteneur resserré : l'espacement vertical par
    # défaut de Streamlit entre chaque élément (~1rem) s'additionne vite sur
    # 6-7 blocs empilés et allonge le défilement pour rien — on le réduit
    # ici globalement plutôt que bloc par bloc.
    with st.container(key="ussd_panel"):
        st.subheader("Menu USSD — *888#")

        screen_html = (
            f'<div class="phone-frame"><div class="phone-notch"></div>'
            f'<div class="phone-screen">{st.session_state["current_screen"]}<span class="cursor">&nbsp;</span></div>'
            f'<div class="phone-label">CamerTrust · terminal simulé</div></div>'
        )
        st.markdown(screen_html, unsafe_allow_html=True)

        if not st.session_state["session_active"]:
            if st.button("☎️ Composer *888#", width='stretch', type="primary"):
                st.session_state["session_id"] = str(uuid.uuid4())
                st.session_state["accumulated"] = []
                # Sans indicateur de chargement, un aller-retour réseau
                # lent vers l'API réelle (Railway) laisse l'écran figé sur
                # ce même bouton pendant plusieurs secondes, sans aucun
                # signe visible que quelque chose se passe — facile à
                # confondre avec « le clavier n'apparaît pas » alors qu'il
                # ne s'agit que d'une attente sans retour visuel.
                with st.spinner("Connexion à l'API…"):
                    reponse = api_client.ussd_request(
                        st.session_state["session_id"], st.session_state["phone_number"], "",
                    )
                st.session_state["current_screen"] = reponse[4:].strip() if reponse[:3] in ("CON", "END") else reponse
                st.session_state["session_active"] = reponse.startswith("CON")
                st.rerun()
        else:
            # Le clavier (et lui seul) occupe l'espace disponible tant que
            # la session est active ; dès que l'abonné envoie une dernière
            # saisie ou termine, ce bloc entier disparaît au prochain rerun
            # et seul l'écran (avec la nouvelle réponse, ou le message de
            # fin) reste affiché — pas d'empilement d'anciens écrans.
            buffer = st.session_state["keypad_buffer"]
            # Pastille de saisie compacte à la place d'un st.text_input
            # complet (label + marges natives ≈ 70px) : l'essentiel — voir
            # ce qu'on a tapé avant d'envoyer — tient en une seule ligne
            # fine, pour que le clavier occupe l'espace disponible sans
            # exiger un long défilement de l'écran.
            st.markdown(
                f'<div class="ussd-buffer">{buffer}<span class="cursor">&nbsp;</span></div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="keypad-caption">Pavé numérique</div>', unsafe_allow_html=True)
            with st.container(key="ussd_keypad"):
                pad_rows = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["*", "0", "#"]]
                for row in pad_rows:
                    cols = st.columns(3, gap="small")
                    for c, digit in zip(cols, row):
                        if c.button(digit, key=f"pad_{digit}", width='stretch'):
                            st.session_state["keypad_buffer"] += digit
                            st.rerun()

            action_row = st.container(key="ussd_actions")
            col_send, col_clear, col_end = action_row.columns(3)
            with col_send:
                if st.button("✅ Envoyer", type="primary", width='stretch', disabled=not buffer):
                    st.session_state["accumulated"].append(buffer)
                    st.session_state["keypad_buffer"] = ""
                    texte = "*".join(st.session_state["accumulated"])
                    with st.spinner("Connexion à l'API…"):
                        reponse = api_client.ussd_request(
                            st.session_state["session_id"], st.session_state["phone_number"], texte,
                        )
                    st.session_state["current_screen"] = reponse[4:].strip() if reponse[:3] in ("CON", "END") else reponse
                    st.session_state["session_active"] = reponse.startswith("CON")
                    st.rerun()
            with col_clear:
                if st.button("⌫ Effacer", width='stretch', disabled=not buffer):
                    st.session_state["keypad_buffer"] = buffer[:-1]
                    st.rerun()
            with col_end:
                if st.button("🔴 Terminer", width='stretch'):
                    st.session_state["session_active"] = False
                    st.session_state["current_screen"] = "Session terminee."
                    st.session_state["keypad_buffer"] = ""
                    st.rerun()

        with st.expander("Historique brut de la session (débogage)"):
            st.code(
                f"sessionId = {st.session_state['session_id']}\n"
                f"phoneNumber = {st.session_state['phone_number']}\n"
                f"text = {'*'.join(st.session_state['accumulated'])!r}",
                language="text",
            )

# --- Colonne SMS ------------------------------------------------------------
with col_sms:
    st.subheader("Messages reçus")
    if st.button("🔄 Actualiser la boîte de réception"):
        st.rerun()

    messages = api_client.get_outbox(st.session_state["phone_number"])

    with st.container(border=True):
        if not messages:
            st.info("Aucun SMS pour cet abonné pour l'instant.")

        for m in messages:
            st.markdown(
                f'<div class="sms-bubble-in">CamerTrust : {m["body"]}</div>'
                f'<div class="sms-meta">{m.get("horodatage", "")}</div>',
                unsafe_allow_html=True,
            )
            alert_id = m.get("alert_id")
            if alert_id:
                try:
                    # Terminal à touches : scénario démo mono-compte (voir
                    # README pour la généralisation multi-comptes) — cible
                    # le même compte que le panneau "Simuler une
                    # transaction suspecte" ci-dessus (`espace_user_id` si
                    # un vrai compte a été inscrit depuis l'Espace client,
                    # sinon le compte de démo). Sur une API réelle sans ce
                    # compte précis, on traite l'absence de correspondance
                    # comme "statut inconnu" plutôt que de laisser planter
                    # la page — ce panneau se contente alors de ne pas
                    # afficher les boutons de réponse pour ce SMS.
                    alerts = api_client.get_alerts(
                        st.session_state.get("espace_user_id", USER_ID_DEMO_HORS_LIGNE)
                    )
                except CompteInconnuError:
                    alerts = []
                alerte = next((a for a in alerts if a["alert_id"] == alert_id), None)
                if alerte and alerte.get("statut") == "en_attente":
                    # Loi de Fitts : les deux réponses possibles sont
                    # grandes, pleine largeur de leur colonne et côte à
                    # côte — la cible à atteindre est large et la distance
                    # entre les deux choix est minimale, pour une réponse
                    # aussi rapide que possible face à une alerte.
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("1️⃣ C'est moi", key=f"conf_{m['id']}", width='stretch'):
                            try:
                                api_client.respond_alert(alert_id, 1)
                            except AlerteInconnueError:
                                st.error("Cette alerte n'existe pas (ou plus) sur cette API.")
                            except AlerteDejaTraiteeError as exc:
                                st.warning(f"Cette alerte a déjà été traitée ({exc.statut_actuel}).")
                            st.rerun()
                    with c2:
                        if st.button("2️⃣ Ce n'est pas moi", key=f"disp_{m['id']}", width='stretch', type="primary"):
                            try:
                                api_client.respond_alert(alert_id, 2)
                            except AlerteInconnueError:
                                st.error("Cette alerte n'existe pas (ou plus) sur cette API.")
                            except AlerteDejaTraiteeError as exc:
                                st.warning(f"Cette alerte a déjà été traitée ({exc.statut_actuel}).")
                            st.rerun()
                elif alerte:
                    statut_badge = {
                        "confirmee": badge("✅ Confirmée par l'abonné", "success"),
                        "bloquee": badge("🔒 Compte protégé — transferts suspendus", "danger"),
                    }
                    st.markdown(statut_badge.get(alerte["statut"], badge(alerte["statut"])), unsafe_allow_html=True)

st.divider()
st.caption(
    "CamerTrust protège votre argent, pas vos habitudes. — "
    "Émulateur de terminal, projet de fin d'études SUP'PTIC 2023-2026."
)

# Barre de 3 icônes — mobile uniquement (voir PHONE_CSS) ; remplace la
# navigation par barre latérale masquée sur ce format d'écran.
bottom_nav(active="app")
