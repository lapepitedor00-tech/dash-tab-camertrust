"""
CamerTrust — E3 — Espace client (mini-application smartphone)
================================================================

Livrable S7 du plan (p.12) : trois écrans réellement branchés sur l'API —
Mon score de confiance, Mes alertes, Mes réglages. C'est la version
« smartphone » du service, complémentaire du terminal USSD/SMS de la page
principale (téléphone à touches).

Ergonomie (voir `style.py` pour le détail) : la navigation entre les trois
écrans est une barre d'onglets en haut du contenu, façon application
mobile grand public (WhatsApp, Instagram) — 3 choix, grandes cibles,
sélection immédiatement visible. Chaque écran ne montre que l'information
nécessaire à la tâche du moment (loi de Hick), regroupée en blocs de 2 à 5
éléments (loi de Miller) plutôt qu'en longue liste plate.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from PIL import Image

import api_client
from style import LOGO_PATH, PHONE_CSS, app_header, badge, bottom_nav, score_ring

st.set_page_config(page_title="CamerTrust — Espace client", page_icon=Image.open(LOGO_PATH), layout="centered")
st.markdown(PHONE_CSS, unsafe_allow_html=True)

USER_ID_DEMO = "C123"  # voir README : généralisation multi-comptes hors périmètre de la démo

st.sidebar.header("📲 Espace client")
online = api_client.is_online()
st.sidebar.markdown(
    badge("🟢 API en ligne" if online else "🔴 Mode démo hors ligne", "success" if online else "danger"),
    unsafe_allow_html=True,
)

st.markdown(app_header("Mon compte"), unsafe_allow_html=True)
# Visibilité de l'état du système (Nielsen) reprise ici, sur la page :
# la barre latérale ci-dessus est masquée sur mobile (voir PHONE_CSS).
st.markdown(
    badge("🟢 API en ligne" if online else "🔴 Mode démo hors ligne", "success" if online else "danger"),
    unsafe_allow_html=True,
)
st.caption(f"Compte {USER_ID_DEMO} · connecté depuis la mini-application")

# ---------------------------------------------------------------------------
# Barre d'onglets — 3 choix seulement (loi de Miller : largement sous les
# 7 ± 2 éléments retenus en mémoire de travail), grandes cibles côte à
# côte (loi de Fitts). st.container(key=...) donne la classe CSS ciblée
# par style.py pour transformer le st.radio natif en barre d'onglets.
# ---------------------------------------------------------------------------
with st.container(key="nav_tabs"):
    ecran = st.radio(
        "Écran", ["🔷 Score", "🔔 Alertes", "⚙️ Réglages"],
        horizontal=True, label_visibility="collapsed", key="espace_nav_ecran",
    )

if ecran == "🔷 Score":
    data = api_client.get_trustscore(USER_ID_DEMO)
    score = data.get("score")
    if score is None:
        st.warning("Score indisponible pour ce compte.")
    else:
        # L'information la plus importante de l'écran (le score) est aussi
        # la plus grande et la plus contrastée visuellement — hiérarchie
        # claire, façon solde affiché par une application bancaire.
        st.markdown(f'<div class="ct-card">{score_ring(score)}</div>', unsafe_allow_html=True)
        st.caption(
            "Ce score reflète la régularité de vos habitudes de transaction. "
            "Il augmente quand vous confirmez vos opérations, et n'est jamais "
            "communiqué à des tiers."
        )

elif ecran == "🔔 Alertes":
    alertes = api_client.get_alerts(USER_ID_DEMO)
    if not alertes:
        st.info("Aucune alerte pour l'instant — c'est bon signe.")
    else:
        en_attente = [a for a in alertes if a["statut"] == "en_attente"]
        historique = [a for a in alertes if a["statut"] != "en_attente"]

        # Regroupement en deux blocs distincts (loi de Miller) : ce qui
        # demande une action MAINTENANT, séparé de ce qui est déjà classé.
        if en_attente:
            st.markdown(
                f'<div class="ct-card-title">⏳ En attente de votre réponse ({len(en_attente)})</div>',
                unsafe_allow_html=True,
            )
            for a in en_attente:
                with st.container(border=True):
                    st.write(f"**{a['type_op'].capitalize()}** de {a['montant']:,} FCFA à {a['heure']}".replace(",", " "))
                    # Loi de Fitts : deux grandes cibles pleine largeur,
                    # côte à côte — réponse rapide et sans ambiguïté.
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("1️⃣ C'est moi", key=f"conf_{a['alert_id']}", width='stretch'):
                            api_client.respond_alert(a["alert_id"], 1)
                            st.rerun()
                    with c2:
                        if st.button("2️⃣ Ce n'est pas moi", key=f"disp_{a['alert_id']}", width='stretch', type="primary"):
                            api_client.respond_alert(a["alert_id"], 2)
                            st.rerun()

        if historique:
            st.markdown(
                '<div class="ct-card-title" style="margin-top:20px;">🗂️ Historique</div>',
                unsafe_allow_html=True,
            )
            df = pd.DataFrame(historique)
            libelle_statut = {"confirmee": "✅ Confirmée", "bloquee": "🔒 Bloquée"}
            df["statut"] = df["statut"].map(libelle_statut).fillna(df["statut"])
            df = df.rename(columns={
                "montant": "Montant (FCFA)", "type_op": "Type", "heure": "Heure",
                "motif": "Motif", "statut": "Statut", "horodatage": "Horodatage",
            })
            colonnes = [c for c in ["Horodatage", "Type", "Montant (FCFA)", "Heure", "Motif", "Statut"] if c in df.columns]
            st.dataframe(df[colonnes], width='stretch', hide_index=True)

elif ecran == "⚙️ Réglages":
    reglages = api_client.get_settings(USER_ID_DEMO)
    if not reglages:
        st.warning("Réglages indisponibles pour ce compte.")
    else:
        # Un même formulaire, mais deux groupes visuels distincts (loi de
        # Miller) : les limites de transaction d'un côté, les préférences
        # générales de l'autre — plutôt que 5 champs à la suite.
        with st.form("form_reglages"):
            st.markdown('<div class="ct-card-title">💳 Limites de transaction</div>', unsafe_allow_html=True)
            plafond = st.number_input(
                "Plafond de transaction (FCFA)", min_value=0, step=10_000,
                value=int(reglages.get("plafond", 500_000)),
            )
            plafond_nocturne = st.slider(
                "Plafond nocturne (FCFA)", 0, 1_000_000,
                value=int(reglages.get("plafond_nocturne", 100_000)), step=10_000,
            )

            st.markdown('<div class="ct-card-title" style="margin-top:16px;">⚙️ Préférences</div>', unsafe_allow_html=True)
            liste_blanche_texte = st.text_area(
                "Numéros habituels (liste blanche) — un par ligne",
                value="\n".join(reglages.get("liste_blanche", [])),
                height=100,
            )
            # Puces colorées plutôt que les petits cercles gris par défaut
            # de st.radio — mêmes sélection/état visibles au premier coup
            # d'œil que la barre d'onglets juste au-dessus (voir
            # `.st-key-canal_pref` dans style.py).
            with st.container(key="canal_pref"):
                canal = st.radio(
                    "Canal préféré pour les alertes", ["ussd", "sms", "app"],
                    index=["ussd", "sms", "app"].index(reglages.get("canal_prefere", "ussd")),
                    horizontal=True,
                )
            langue = st.selectbox(
                "Langue", ["fr", "en"],
                index=["fr", "en"].index(reglages.get("langue", "fr")),
            )
            # `use_container_width` plutôt que `width='stretch'` : la
            # checklist de compatibilité (requirements.txt) ne garantit
            # que Streamlit >= 1.37, où `width=` n'existe pas encore sur
            # les boutons — ce paramètre plus ancien couvre une bien plus
            # large plage de versions et donne le même bouton pleine
            # largeur.
            valide = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)

        if valide:
            liste_blanche = [n.strip() for n in liste_blanche_texte.splitlines() if n.strip()]
            api_client.put_settings(
                USER_ID_DEMO,
                plafond=int(plafond),
                plafond_nocturne=int(plafond_nocturne),
                liste_blanche=liste_blanche,
                canal_prefere=canal,
                langue=langue,
            )
            st.success("Réglages enregistrés.")

        st.divider()
        st.caption("Vous pouvez vous désinscrire à tout moment depuis le menu USSD (*888*6#) ou ci-dessous.")
        if st.button("🚫 Désactiver CamerTrust"):
            api_client.delete_user(USER_ID_DEMO)
            st.success("Compte désinscrit. Vos données d'analyse ont été effacées.")

# Barre de 3 icônes — mobile uniquement (voir PHONE_CSS) ; remplace la
# navigation par barre latérale masquée sur ce format d'écran.
bottom_nav(active="espace")
