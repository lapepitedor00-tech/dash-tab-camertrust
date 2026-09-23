"""
CamerTrust — E3 — Console de supervision (page secondaire, opérateur)
========================================================================

Livrable S8 du plan (p.12) : page secondaire à destination de l'analyste
côté opérateur — CamerTrust reste avant tout un service pour l'abonné,
cette console ne sert qu'à « démontrer le service, pas à le définir »
(changement de cap documenté en page 1 du plan).

Ergonomie : exactement 4 indicateurs en tête d'écran (loi de Miller — un
coup d'œil suffit à tous les retenir), rendus comme des cartes élevées
plutôt que du texte brut. Les filtres, au nombre de 3, sont regroupés
dans un bloc visuel unique plutôt que dispersés dans la page.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st
from PIL import Image

import api_client
from style import LOGO_PATH, PHONE_CSS, app_header, badge, bottom_nav

st.set_page_config(page_title="CamerTrust — Supervision", page_icon=Image.open(LOGO_PATH), layout="wide")
st.markdown(PHONE_CSS, unsafe_allow_html=True)

top_l, top_r = st.columns([3, 1])
with top_l:
    st.markdown(app_header("Console de supervision"), unsafe_allow_html=True)
    st.caption("Vue opérateur — secondaire. L'abonné reste acteur de sa propre sécurité ; cette page ne fait que rendre le service visible côté institutionnel.")
with top_r:
    online = api_client.is_online()
    st.markdown(
        badge("🟢 API en ligne" if online else "🔴 Mode démo hors ligne", "success" if online else "danger"),
        unsafe_allow_html=True,
    )
    if st.button("🔄 Actualiser", width='stretch'):
        st.rerun()

# ---------------------------------------------------------------------------
# 4 indicateurs, une seule rangée (loi de Miller) — chacun rendu comme une
# petite carte élevée (voir [data-testid="stMetric"] dans style.py) pour
# se distinguer immédiatement du reste du contenu.
# ---------------------------------------------------------------------------
stats = api_client.get_admin_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions du jour", f"{stats.get('transactions_jour', 0):,}".replace(",", " "))
c2.metric("Alertes émises", stats.get("alertes_jour", 0))
c3.metric("Taux de réponse abonnés", f"{stats.get('taux_reponse_pct', 0)} %")
c4.metric("Comptes protégés", stats.get("alertes_bloquees", 0))

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Alertes récentes")

alertes = api_client.get_admin_alerts()
if not alertes:
    st.info("Aucune alerte enregistrée.")
else:
    df = pd.DataFrame(alertes)
    df["horodatage"] = pd.to_datetime(df["horodatage"], errors="coerce")

    # Les 3 filtres regroupés dans un seul bloc visuel (loi de Miller :
    # une même « pensée » — affiner la liste — plutôt que 3 contrôles
    # dispersés que l'œil doit relier lui-même).
    with st.container(border=True):
        st.markdown('<div class="ct-card-title">🔍 Filtrer</div>', unsafe_allow_html=True)
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            dates_disponibles = sorted(df["horodatage"].dt.date.dropna().unique())
            date_choisie = st.selectbox(
                "Date", ["Toutes"] + [d.isoformat() for d in dates_disponibles],
            )
        with col_f2:
            montant_min = st.number_input("Montant minimum (FCFA)", min_value=0, value=0, step=10_000)
        with col_f3:
            statuts = ["Tous"] + sorted(df["statut"].unique().tolist())
            statut_choisi = st.selectbox("Statut", statuts)

    df_filtre = df.copy()
    if date_choisie != "Toutes":
        df_filtre = df_filtre[df_filtre["horodatage"].dt.date.astype(str) == date_choisie]
    if montant_min:
        df_filtre = df_filtre[df_filtre["montant"] >= montant_min]
    if statut_choisi != "Tous":
        df_filtre = df_filtre[df_filtre["statut"] == statut_choisi]

    libelle_statut = {"en_attente": "En attente", "confirmee": "Confirmée", "bloquee": "Bloquée"}
    df_affiche = df_filtre.rename(columns={
        "horodatage": "Horodatage", "user_id": "Compte", "montant": "Montant (FCFA)",
        "type_op": "Type", "heure": "Heure",
    })
    df_affiche["statut"] = df_filtre["statut"].map(libelle_statut).fillna(df_filtre["statut"])
    df_affiche = df_affiche.rename(columns={"statut": "Statut"})

    st.caption(f"{len(df_affiche)} alerte(s) affichée(s) sur {len(df)} au total.")
    st.dataframe(
        df_affiche[["Horodatage", "Compte", "Type", "Montant (FCFA)", "Heure", "Statut"]],
        width='stretch', hide_index=True,
    )

    csv = df_affiche.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Export CSV", data=csv,
        file_name=f"alertes_camertrust_{datetime.now():%Y%m%d_%H%M}.csv",
        mime="text/csv",
    )

# Barre de 3 icônes — mobile uniquement (voir PHONE_CSS) ; remplace la
# navigation par barre latérale masquée sur ce format d'écran.
bottom_nav(active="console")
