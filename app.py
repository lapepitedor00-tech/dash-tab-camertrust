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
from style import LOGO_PATH, PHONE_CSS, app_header, badge, bottom_nav, settings_trigger

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
        api_url_input = st.text_input(
            "URL de l'API (E2)", value=st.session_state["api_url"], key=f"api_url_input_{suffix}",
        )
        if api_url_input != st.session_state["api_url"]:
            st.session_state["api_url"] = api_url_input

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 Vérifier", width='stretch', key=f"check_health_{suffix}"):
                api_client.check_health()
        with col_b:
            if st.button("⏰ Réveiller", width='stretch', key=f"wake_{suffix}"):
                with st.spinner("Ping /health (jusqu'à 10 min si l'instance dormait)…"):
                    api_client.check_health()

    with st.expander("💡 Simuler une transaction suspecte"):
        st.caption("Injecte une transaction pour déclencher une alerte, comme le ferait un vrai flux transactionnel côté opérateur.")
        montant = st.number_input("Montant (FCFA)", min_value=1000, value=450_000, step=10_000, key=f"montant_{suffix}")
        heure = st.slider("Heure de la transaction", 0, 23, 2, key=f"heure_{suffix}")
        type_op = st.selectbox("Type d'opération", ["retrait", "transfert"], key=f"type_op_{suffix}")
        if st.button("Envoyer la transaction", width='stretch', key=f"send_tx_{suffix}"):
            res = api_client.score_transaction(
                user_id="C123", amount=int(montant), type_op=type_op, hour=int(heure),
            )
            if res.get("is_fraud"):
                st.success("Transaction risquée détectée — une alerte vient d'être envoyée à l'abonné (voir la boîte SMS).")
            else:
                st.info("Transaction jugée conforme aux habitudes — aucune alerte envoyée.")


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
                alerts = api_client.get_alerts("C123")  # démo mono-compte ; voir README pour la généralisation multi-comptes
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
                            api_client.respond_alert(alert_id, 1)
                            st.rerun()
                    with c2:
                        if st.button("2️⃣ Ce n'est pas moi", key=f"disp_{m['id']}", width='stretch', type="primary"):
                            api_client.respond_alert(alert_id, 2)
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
