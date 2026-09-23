"""
CamerTrust — E3 — Système de conception (design system) de l'émulateur.
=========================================================================

Ce module centralise :

  1. `PHONE_CSS` — un seul bloc CSS injecté une fois par page, qui donne à
     toute l'application une identité visuelle cohérente (Nielsen —
     « consistency & standards ») et applique trois lois d'ergonomie des
     interfaces sur l'ensemble des trois écrans d'E3 :

       • Loi de Fitts (atteindre une cible est d'autant plus rapide que sa
         taille est grande et sa distance courte) → tous les boutons ont
         une hauteur minimale de 44-48 px (norme de cible tactile
         Apple HIG / Material Design), le pavé USSD utilise de grandes
         touches rondes, les boutons de réponse à une alerte sont pleine
         largeur et regroupés.
       • Loi de Hick (le temps de décision augmente avec le nombre
         d'options) → les réglages avancés (URL de l'API, vérification de
         connexion) sont repliés dans un panneau secondaire, la navigation
         de l'espace client se limite à 3 choix visibles à la fois.
       • Loi de Miller (7 ± 2 éléments retenus en mémoire de travail) →
         les informations sont regroupées en blocs visuels distincts
         (cartes) de 3 à 5 éléments plutôt que listées en vrac : 4
         indicateurs sur la console, 2-3 champs par groupe de réglages.

     Inspiration visuelle assumée : les applications de mobile money et de
     banque mobile (grand chiffre de score façon « solde », badges de
     statut colorés, cartes à ombre légère), et les barres d'onglets des
     applications mobiles grand public (WhatsApp, Instagram) pour la
     navigation de l'espace client.

  2. Une poignée de petits générateurs HTML (`badge`, `score_ring`) pour
     rester cohérent avec le reste du code, qui construit déjà ses propres
     fragments HTML (`sms-bubble-in`, `status-pill-*`, etc.) plutôt que
     d'ajouter une dépendance de composants tierce.
"""

import base64
from pathlib import Path

import streamlit as st

NAVY = "#1B3A5C"
BLUE = "#2E6DA4"
TEAL = "#1F7A72"
GOLD = "#B8860B"
RED = "#C0392B"

# Icône d'onglet / de navigation multipage (favicon) : le même bouclier que
# le logo affiché en en-tête de chaque écran, pour une identité de marque
# cohérente du premier coup d'œil (onglet du navigateur compris). Fichier
# fourni par le porteur du projet (fond blanc détouré en transparence) —
# voir `assets/logo.png`.
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"

# Encodée en base64 une seule fois au chargement du module, pour rester
# cohérent avec le reste du design system (tout le HTML de style.py est
# auto-suffisant, sans requête réseau ni chemin de fichier à résoudre côté
# navigateur).
LOGO_DATA_URI = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

# Logo « bouclier CamerTrust » fourni par le porteur du projet, réutilisé en
# HTML inline dans l'en-tête de chacun des 3 écrans. La taille réelle est
# fixée par le conteneur CSS `.ct-logo` (et réduite sur mobile) ;
# `object-fit: contain` préserve les proportions du bouclier.
LOGO_IMG = f'<img src="{LOGO_DATA_URI}" alt="CamerTrust" />'

PHONE_CSS = """
<style>
:root {
    --ct-navy: #1B3A5C;
    --ct-blue: #2E6DA4;
    --ct-teal: #1F7A72;
    --ct-gold: #B8860B;
    --ct-red:  #C0392B;
    --ct-bg:      #F3F6FA;
    --ct-card:    #FFFFFF;
    --ct-border:  #E2E8F0;
    --ct-text:    #1F2937;
    --ct-muted:   #64748B;
}

/* Attention : ce sélecteur ne doit PAS inclure [class*="st-emotion"].
   Les icônes natives de Streamlit (chevrons d'expander, flèches, etc.)
   sont du texte ("keyboard_arrow_down"...) affiché comme une icône via
   la police à ligatures Material Symbols, sur un <span
   data-testid="stIconMaterial"> qui porte lui aussi une classe
   st-emotion-cache-*. Un sélecteur `[class*="st-emotion"]` écrase donc
   la police d'icônes par une police normale, et le nom brut de l'icône
   ("keyboard_arrow_down", "double_arrow"...) s'affiche en toutes
   lettres par-dessus le contenu au lieu du petit chevron attendu — bug
   corrigé ici. `font-family` hérite naturellement de html/body vers
   tous les descendants, donc cibler seulement la racine suffit et
   laisse les règles plus spécifiques de Streamlit (dont celle des
   icônes) prendre le dessus normalement. */
html, body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
[data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
}

/* Fond légèrement teinté pour la zone de contenu : fait ressortir les
   cartes blanches (élévation à la Material Design), plutôt qu'un blanc
   sur blanc plat. La barre latérale garde le thème par défaut de
   Streamlit pour rester clairement identifiable comme un panneau
   « réglages », distinct du contenu applicatif (heuristique de
   reconnaissance des zones fonctionnelles). */
[data-testid="stMain"] {
    background: var(--ct-bg);
}

/* ====================================================================
   BOUTONS — loi de Fitts : cible tactile confortable (>= 44px de haut,
   Apple HIG / Material Design), coins arrondis cohérents, retour visuel
   immédiat à l'appui (heuristique de visibilité de l'état du système).
   ==================================================================== */
div[data-testid="stButton"] button,
div[data-testid="stFormSubmitButton"] button,
div[data-testid="stDownloadButton"] button {
    min-height: 46px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 14.5px;
    transition: transform 0.05s ease, box-shadow 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}
div[data-testid="stButton"] button:active,
div[data-testid="stFormSubmitButton"] button:active,
div[data-testid="stDownloadButton"] button:active {
    transform: scale(0.98);
}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(180deg, #3579b8, var(--ct-blue));
    border: none;
    color: #fff;
    box-shadow: 0 3px 10px rgba(46,109,164,0.32);
}
button[data-testid="stBaseButton-primary"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
    background: linear-gradient(180deg, #3f86c4, #2a6396);
    box-shadow: 0 4px 12px rgba(46,109,164,0.42);
}
button[data-testid="stBaseButton-secondary"],
button[data-testid="stBaseButton-secondaryFormSubmit"] {
    background: #ffffff;
    border: 1.5px solid var(--ct-border);
    color: var(--ct-navy);
}
button[data-testid="stBaseButton-secondary"]:hover,
button[data-testid="stBaseButton-secondaryFormSubmit"]:hover {
    border-color: var(--ct-blue);
    color: var(--ct-blue);
}

/* Action « ce n'est pas moi / signaler une fraude » : couleur d'alerte
   dédiée pour qu'elle se reconnaisse au premier coup d'œil, sans avoir à
   lire le texte (reconnaissance plutôt que rappel). Ciblage par
   sous-chaîne de la classe générée par `key=` : fonctionne même si
   l'identifiant de l'alerte change à chaque rendu. */
div[class*="st-key-disp_"] button {
    background: linear-gradient(180deg, #d3493a, var(--ct-red));
    border: none;
    color: #fff;
    box-shadow: 0 3px 10px rgba(192,57,43,0.30);
}
div[class*="st-key-disp_"] button:hover {
    background: linear-gradient(180deg, #dd5b4d, #b3362a);
}
div[class*="st-key-conf_"] button {
    background: #ffffff;
    border: 1.5px solid var(--ct-teal);
    color: var(--ct-teal);
}
div[class*="st-key-conf_"] button:hover {
    background: #EAF6F4;
}

/* ====================================================================
   CARTES — regroupement visuel des informations liées (loi de Miller) :
   un fond blanc, une ombre légère, un rayon de 16px, utilisés partout
   où l'app affiche un bloc d'information cohérent.
   ==================================================================== */
.ct-card {
    background: var(--ct-card);
    border: 1px solid var(--ct-border);
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 2px 10px rgba(15,23,42,0.05);
}
.ct-card-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--ct-muted);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
}

/* ====================================================================
   BADGES DE STATUT — code couleur constant sur toute l'application :
   vert/sarcelle = sûr/confirmé, or = en attente, rouge = bloqué/risque.
   ==================================================================== */
.ct-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: 0.2px;
}
.ct-badge-success { background: #E4F5EE; color: #146C43; }
.ct-badge-warning  { background: #FBF0DA; color: #8A6608; }
.ct-badge-danger   { background: #FBE7E4; color: #A32E20; }
.ct-badge-neutral  { background: #EAEFF4; color: var(--ct-muted); }

/* ====================================================================
   EN-TÊTE DE MARQUE — bouclier « CamerTrust » affiché sur les 3 écrans, à
   la place d'un simple emoji : un bouclier est le symbole naturel de la
   protection contre la fraude, et porter le nom de l'application
   directement dessus en fait un vrai logo (reconnaissance immédiate,
   cohérence de marque — Nielsen) plutôt qu'un pictogramme générique.
   ==================================================================== */
.ct-app-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 2px 0 6px 0;
}
.ct-logo {
    flex: 0 0 auto;
    height: 52px;
    width: auto;
    filter: drop-shadow(0 3px 6px rgba(27,58,92,0.28));
}
.ct-logo img {
    height: 100%;
    width: auto;
    display: block;
    object-fit: contain;
}
.ct-app-header-text { line-height: 1.15; }
.ct-app-header-title {
    font-size: 1.75rem;
    font-weight: 800;
    color: var(--ct-navy);
}
.ct-app-header-subtitle {
    font-size: 0.98rem;
    font-weight: 700;
    color: var(--ct-blue);
    margin-top: 1px;
}

/* ====================================================================
   SCORE DE CONFIANCE — grand anneau (façon jauge), inspiré des « rings »
   d'activité et des scores affichés en gros par les applications de
   banque mobile : l'information la plus importante de l'écran doit être
   la plus visible (hiérarchie visuelle claire = moins d'effort de
   lecture = application de la loi de Hick au niveau perceptif).
   ==================================================================== */
.ct-ring-outer {
    width: 168px; height: 168px;
    border-radius: 50%;
    background: conic-gradient(var(--ring-color) var(--pct), #E7ECF2 0);
    display: flex; align-items: center; justify-content: center;
    margin: 10px auto 8px auto;
    box-shadow: 0 8px 22px rgba(15,23,42,0.10);
}
.ct-ring-inner {
    width: 132px; height: 132px;
    border-radius: 50%;
    background: #ffffff;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    box-shadow: inset 0 0 0 1px rgba(15,23,42,0.04);
}
.ct-ring-value { font-size: 36px; font-weight: 800; color: var(--ct-navy); line-height: 1; }
.ct-ring-max   { font-size: 12px; color: var(--ct-muted); margin-top: 3px; }
.ct-ring-caption {
    text-align: center; font-size: 13.5px; font-weight: 700; margin-top: 2px;
}

/* ====================================================================
   INDICATEURS (st.metric) — console de supervision : transformés en
   petites cartes élevées, 4 au total sur une seule rangée (loi de
   Miller : un coup d'œil suffit à tout mémoriser).
   ==================================================================== */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--ct-border);
    border-radius: 14px;
    padding: 16px 18px 14px 18px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
}
[data-testid="stMetricLabel"] p {
    color: var(--ct-muted) !important;
    font-size: 12.5px !important;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    font-weight: 700 !important;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
}
[data-testid="stMetricValue"] {
    color: var(--ct-navy);
    font-weight: 800;
}

/* Boîtes d'alerte Streamlit (st.info/success/warning/error) : mêmes
   coins arrondis que le reste du système pour rester cohérent. */
div[data-testid="stAlert"] {
    border-radius: 12px;
}

/* ====================================================================
   BARRE D'ONGLETS DE NAVIGATION — remplace un st.radio horizontal par
   une barre à la manière des apps mobiles (WhatsApp, Instagram) : peu
   d'options, très visibles, grandes cibles (Fitts), sélection évidente
   (Nielsen — visibilité de l'état du système). Ciblé via
   st.container(key="nav_tabs"), donc n'affecte aucun autre st.radio de
   l'application.
   ==================================================================== */
.st-key-nav_tabs div[data-testid="stRadioGroup"] {
    display: flex;
    gap: 6px;
    background: #EAF0F6;
    padding: 5px;
    border-radius: 14px;
    margin-bottom: 4px;
}
.st-key-nav_tabs div[data-testid="stRadioGroup"] > div {
    flex: 1;
}
.st-key-nav_tabs label[data-testid="stRadioOption"] {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 40px;
    padding: 8px 6px;
    border-radius: 10px;
    cursor: pointer;
    transition: background 0.15s ease, box-shadow 0.15s ease;
}
/* La puce ronde native du bouton radio est masquée : le fond de la
   pastille suffit à indiquer la sélection (design minimaliste). */
.st-key-nav_tabs label[data-testid="stRadioOption"] > div > div:first-child {
    display: none;
}
.st-key-nav_tabs label[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
    margin: 0;
    font-size: 13.5px;
    font-weight: 700;
    color: var(--ct-muted);
}
.st-key-nav_tabs label[data-testid="stRadioOption"][data-selected="true"] {
    background: var(--ct-blue);
    box-shadow: 0 2px 8px rgba(46,109,164,0.35);
}
.st-key-nav_tabs label[data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p {
    color: #ffffff;
}

/* ====================================================================
   GROUPES DE PUCES (RADIO) — utilisé pour tout st.radio horizontal
   secondaire de l'application (ex. « Canal préféré » de l'écran
   Réglages). Un st.radio natif de Streamlit n'a par défaut que de
   petits cercles gris sans aucune couleur de marque : à côté de la
   barre d'onglets très colorée juste au-dessus, il paraît terne et sans
   retour visuel clair sur la sélection en cours (signalé par
   l'utilisateur — options « muettes »). Reprend le même principe que
   `.st-key-nav_tabs` (puce ronde native masquée, fond coloré sur
   l'option sélectionnée) mais en puces individuelles plutôt qu'en
   segments d'une même barre, plus adapté à un choix secondaire dans un
   formulaire. Ciblé via `st.container(key="canal_pref")` — pour
   réutiliser ce même style ailleurs, ajouter la classe du nouveau
   conteneur à la liste de sélecteurs ci-dessous plutôt que dupliquer le
   bloc.
   ==================================================================== */
.st-key-canal_pref div[data-testid="stRadioGroup"] {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 4px;
}
.st-key-canal_pref label[data-testid="stRadioOption"] {
    display: flex;
    align-items: center;
    gap: 0;
    min-height: 38px;
    padding: 7px 16px;
    border-radius: 999px;
    border: 1.5px solid var(--ct-border);
    background: #ffffff;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.st-key-canal_pref label[data-testid="stRadioOption"]:hover {
    border-color: var(--ct-blue);
}
/* Puce ronde native masquée — même logique que `.st-key-nav_tabs` : le
   fond de la pastille suffit à indiquer la sélection, sans doubler le
   signal avec un petit rond ET un fond coloré. */
.st-key-canal_pref label[data-testid="stRadioOption"] > div > div:first-child {
    display: none;
}
.st-key-canal_pref label[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p {
    margin: 0;
    font-size: 13.5px;
    font-weight: 700;
    color: var(--ct-navy);
}
.st-key-canal_pref label[data-testid="stRadioOption"][data-selected="true"] {
    background: var(--ct-blue);
    border-color: var(--ct-blue);
    box-shadow: 0 2px 8px rgba(46,109,164,0.30);
}
.st-key-canal_pref label[data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p {
    color: #ffffff;
}

/* ====================================================================
   CADRE TÉLÉPHONE — reste volontairement sobre : « un cadre noir
   arrondi, une police à chasse fixe, un fond clair » est plus crédible
   pour un terminal basique qu'une imitation d'iPhone.
   ==================================================================== */
.phone-frame {
    background: #1c1c1e;
    border-radius: 34px;
    padding: 18px 14px 22px 14px;
    width: 320px;
    margin: 0 auto 1rem auto;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}
.phone-notch {
    width: 60px;
    height: 6px;
    background: #3a3a3c;
    border-radius: 3px;
    margin: 0 auto 10px auto;
}
.phone-screen {
    background: #d7e6d0;
    color: #16281a;
    font-family: "Courier New", Courier, monospace;
    font-size: 15px;
    line-height: 1.5;
    min-height: 190px;
    padding: 14px;
    border-radius: 6px;
    white-space: pre-wrap;
    word-wrap: break-word;
    border: 2px solid #0f1a11;
}
.phone-screen .cursor {
    display: inline-block;
    width: 8px;
    background: #16281a;
    animation: blink 1s steps(2) infinite;
}
@keyframes blink { 50% { opacity: 0; } }
.phone-label {
    text-align: center;
    color: #8e8e93;
    font-size: 11px;
    letter-spacing: 1px;
    margin-top: 10px;
    text-transform: uppercase;
}
.sms-bubble-in {
    background: #2f3136;
    color: #f2f2f2;
    padding: 10px 14px;
    border-radius: 14px 14px 14px 2px;
    max-width: 80%;
    margin: 4px 0;
    font-size: 14px;
}
.sms-bubble-out {
    background: #2e7d32;
    color: #ffffff;
    padding: 10px 14px;
    border-radius: 14px 14px 2px 14px;
    max-width: 80%;
    margin: 4px 0 4px auto;
    font-size: 14px;
    text-align: right;
}
.sms-meta {
    font-size: 10px;
    color: #9a9a9a;
    margin: 0 6px 8px 6px;
}
.status-pill-online {
    background: #1b5e20; color: white; padding: 3px 12px;
    border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block;
}
.status-pill-offline {
    background: #b71c1c; color: white; padding: 3px 12px;
    border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block;
}

/* Pastille de saisie USSD — une seule ligne fine à la place d'un champ
   Streamlit complet (label + marges natives), pour que le clavier qui
   suit occupe l'espace disponible sans allonger le défilement. */
.ussd-buffer {
    background: #eef2f7;
    border: 1.5px solid var(--ct-border);
    border-radius: 10px;
    padding: 7px 12px;
    margin: 6px 0 4px 0;
    min-height: 18px;
    font-family: "Courier New", Courier, monospace;
    font-size: 15px;
    color: var(--ct-navy);
}
.ussd-buffer .cursor {
    display: inline-block;
    width: 8px;
    background: var(--ct-navy);
    animation: blink 1s steps(2) infinite;
}

/* ====================================================================
   ÉCRAN DE DIALOGUE USSD — resserre l'espacement vertical par défaut de
   Streamlit (~1rem) entre le titre, l'écran simulé, le clavier et les
   actions : sur 6-7 blocs empilés, ce seul réglage évite une bonne
   partie du long défilement dénoncé sur mobile. Ciblé via
   st.container(key="ussd_panel"), donc sans effet sur le reste de la
   page (colonne SMS, barre latérale...).
   ==================================================================== */
.st-key-ussd_panel {
    gap: 0.5rem !important;
}

/* ====================================================================
   PAVÉ NUMÉRIQUE USSD — touches rondes et grandes (loi de Fitts),
   lettres ABC/DEF... comme sur un vrai téléphone, retour d'appui net.
   Ciblé via st.container(key="ussd_keypad"), donc isolé du reste des
   boutons de la page (Envoyer, Composer *888#, etc.).
   ==================================================================== */
.st-key-ussd_keypad {
    background: linear-gradient(160deg, #29292c 0%, #1c1c1e 75%);
    border-radius: 18px;
    padding: 10px 10px 4px 10px;
    margin: 2px 0 10px 0;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06), 0 6px 16px rgba(0,0,0,0.30);
    gap: 6px !important; /* Streamlit espace chaque rangée de 16px par défaut */
}
/* Les touches gardent une cible confortable (loi de Fitts, > 44px) sans
   pour autant grandir jusqu'à occuper toute la largeur de leur colonne :
   un vrai clavier de téléphone est compact, pas géant. Le plafond de
   largeur (et donc de hauteur, via aspect-ratio) est ce qui évite au
   pavé de devenir la première cause de long défilement sur l'écran ;
   `margin: 0 auto` centre chaque touche dans sa colonne. */
.st-key-ussd_keypad div[data-testid="stButton"] button {
    position: relative;
    width: 100%;
    max-width: 58px;
    margin: 0 auto;
    aspect-ratio: 1 / 1;
    border-radius: 50%;
    background: radial-gradient(circle at 32% 28%, #3d3d40 0%, #2a2a2d 65%);
    border: 1px solid rgba(255,255,255,0.08);
    color: #f2f2f2;
    font-family: "Courier New", Courier, monospace;
    font-weight: 700;
    font-size: 17px;
    line-height: 1;
    padding-bottom: 9px;
    box-shadow: 0 2px 0 rgba(0,0,0,0.45), 0 4px 10px rgba(0,0,0,0.25);
    transition: transform 0.06s ease, box-shadow 0.06s ease, background 0.15s ease, border-color 0.15s ease;
    min-height: 0; /* neutralise la règle globale min-height:46px, la taille vient de aspect-ratio */
}
.st-key-ussd_keypad div[data-testid="stButton"] button:hover {
    background: radial-gradient(circle at 32% 28%, #48484c 0%, #313134 65%);
    border-color: rgba(90,200,120,0.4);
}
.st-key-ussd_keypad div[data-testid="stButton"] button:focus:not(:active) {
    box-shadow: 0 2px 0 rgba(0,0,0,0.45), 0 4px 10px rgba(0,0,0,0.25), 0 0 0 2px rgba(90,200,120,0.35);
}
.st-key-ussd_keypad div[data-testid="stButton"] button:active {
    transform: scale(0.92);
    background: radial-gradient(circle at 32% 28%, #2f7a3c 0%, #16281a 70%);
    box-shadow: inset 0 3px 6px rgba(0,0,0,0.55);
}
.st-key-ussd_keypad div[data-testid="stButton"] button::after {
    position: absolute;
    bottom: 7px;
    left: 0;
    right: 0;
    text-align: center;
    font-family: Arial, Helvetica, sans-serif;
    font-weight: 600;
    font-size: 7.5px;
    letter-spacing: 1px;
    color: #9a9a9a;
}
.st-key-pad_2 button::after { content: "ABC"; }
.st-key-pad_3 button::after { content: "DEF"; }
.st-key-pad_4 button::after { content: "GHI"; }
.st-key-pad_5 button::after { content: "JKL"; }
.st-key-pad_6 button::after { content: "MNO"; }
.st-key-pad_7 button::after { content: "PQRS"; }
.st-key-pad_8 button::after { content: "TUV"; }
.st-key-pad_9 button::after { content: "WXYZ"; }
.st-key-pad_0 button::after { content: "+"; }
.keypad-caption {
    text-align: center;
    color: #8e8e93;
    font-size: 10.5px;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: -4px 0 8px 0;
}

/* ====================================================================
   RESPONSIVE — adaptation au terminal mobile de l'abonné.

   Streamlit stack automatiquement ses `st.columns` en dessous de ~640px
   de large (chaque colonne passe à min-width: calc(100% - 24px)) : très
   bien pour la plupart des lignes de boutons (une colonne empilée =
   cible pleine largeur = loi de Fitts encore mieux respectée sur un
   petit écran), mais catastrophique pour le pavé numérique, dont les 3
   colonnes par rangée sont *le* clavier : empilées, chaque touche
   devient un cercle plein écran et il faut faire défiler toute la page
   pour taper un simple numéro. On neutralise donc l'empilement
   uniquement à l'intérieur de `st.container(key="ussd_keypad")`
   (ciblage isolé, comme pour le reste du pavé), pour qu'il garde sa
   disposition en grille 3×4 — fidèle à un vrai clavier de téléphone —
   à toutes les largeurs.
   ==================================================================== */
@media (max-width: 640px) {
    .st-key-ussd_keypad div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    .st-key-ussd_keypad div[data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    .st-key-ussd_keypad div[data-testid="stButton"] button {
        font-size: 17px;
    }

    /* Même correctif que le pavé numérique, pour la rangée Envoyer /
       Effacer / Terminer : sans lui, Streamlit empile les 3 boutons en
       pleine largeur (~150px de plus), alors qu'une seule ligne compacte
       suffit largement à des cibles de cette taille (loi de Fitts déjà
       satisfaite par leur hauteur, pas besoin de la largeur complète). */
    .st-key-ussd_actions div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    .st-key-ussd_actions div[data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    .st-key-ussd_actions div[data-testid="stButton"] button {
        font-size: 12.5px;
        padding-left: 4px;
        padding-right: 4px;
    }

    /* Le cadre du terminal simulé s'adapte à la largeur de l'écran au
       lieu d'une largeur fixe en pixels (défensif : garde une marge de
       respiration même sur les téléphones les plus étroits, ~320px). */
    .phone-frame {
        width: 100%;
        max-width: 320px;
        padding: 16px 12px 20px 12px;
    }

    /* Les titres `st.title()` sont dimensionnés pour un écran large ;
       sur un téléphone ils retombent sur 3 lignes et mangent tout
       l'écran avant même d'arriver au contenu utile. On les réduit
       (hiérarchie visuelle conservée, juste rééchelonnée) et on
       resserre l'espace au-dessus du contenu pour que l'abonné voie
       une information utile dès l'ouverture, sans défiler. */
    [data-testid="stMainBlockContainer"], .block-container {
        padding-top: 2.6rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    [data-testid="stMarkdownContainer"] h1, h1 {
        font-size: 1.35rem !important;
        line-height: 1.25 !important;
    }
    [data-testid="stMarkdownContainer"] h2, h2 {
        font-size: 1.2rem !important;
        line-height: 1.25 !important;
    }
    [data-testid="stMarkdownContainer"] h3, h3 {
        font-size: 1.05rem !important;
        line-height: 1.25 !important;
    }

    /* Anneau de score légèrement réduit pour rester confortablement
       dans une carte plus étroite, sans jamais toucher ses bords. */
    .ct-ring-outer { width: 148px; height: 148px; }
    .ct-ring-inner { width: 114px; height: 114px; }
    .ct-ring-value { font-size: 30px; }

    .ct-card { padding: 16px; }

    /* Logo un cran plus petit, pour laisser toute sa place au nom de
       l'application sur les écrans étroits. */
    .ct-logo { height: 40px; }
    .ct-app-header-title { font-size: 1.4rem; }
    .ct-app-header-subtitle { font-size: 0.85rem; }

    /* Écran simulé et espacement du panneau USSD encore un peu resserrés
       sur mobile — c'est là que le clavier a le plus besoin de la place
       libérée pour tenir sans long défilement. */
    .phone-screen { min-height: 168px; padding: 11px 12px; font-size: 14px; }
    .phone-frame { padding: 12px 10px 14px 10px; }
    .st-key-ussd_panel { gap: 0.35rem !important; }

    /* ====================================================================
       NAVIGATION MOBILE — la barre latérale de Streamlit (liste des 3
       pages + tout contenu placé dans st.sidebar) est un panneau qu'il
       faut ouvrir puis faire défiler : sur un téléphone, ça revient à
       cacher la navigation. On la masque entièrement (elle et son bouton
       « ouvrir/fermer ») et on la remplace par une barre de 3 icônes fixée
       en bas de l'écran — toujours visible, jamais besoin de défiler pour
       l'atteindre, comme la barre d'onglets de n'importe quelle app grand
       public. Les réglages qu'elle contenait (abonné simulé, réglages
       avancés...) sont repris sous forme d'icône directement sur la page
       (voir `.settings-trigger` plus bas), pas perdus. */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }
    [data-testid="stMainBlockContainer"], .block-container {
        padding-bottom: 76px !important;
    }
}

/* Le déclencheur de réglages (icône ⚙️ sur la page) n'a de raison d'être
   que lorsque la barre latérale est masquée : sur bureau, les mêmes
   réglages restent dans la barre latérale comme avant, donc on ne
   double pas l'interface. */
.settings-trigger,
.st-key-settings_trigger {
    display: none;
}
@media (max-width: 640px) {
    .settings-trigger,
    .st-key-settings_trigger {
        display: block;
    }
    .st-key-settings_trigger [data-testid="stPopoverButton"] {
        min-height: 40px;
        width: 40px;
        padding: 0;
        border-radius: 50%;
        font-size: 17px;
        box-shadow: 0 2px 8px rgba(15,23,42,0.12);
    }
}

/* ====================================================================
   BARRE DE NAVIGATION DU BAS — remplace les 3 liens de page de la barre
   latérale sur mobile. Fixée (position: fixed), donc accessible sans
   défiler quel que soit l'endroit de la page où se trouve l'abonné.
   Masquée sur bureau : la barre latérale y suffit déjà (pas de double
   navigation). Ciblée via st.container(key="bottom_nav").
   ==================================================================== */
.st-key-bottom_nav {
    display: none;
}
@media (max-width: 640px) {
    .st-key-bottom_nav {
        display: block;
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 999;
        background: #ffffff;
        border-top: 1px solid var(--ct-border);
        padding: 4px 6px calc(4px + env(safe-area-inset-bottom, 0px)) 6px;
        box-shadow: 0 -2px 12px rgba(15,23,42,0.10);
    }
    .st-key-bottom_nav div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 4px !important;
    }
    .st-key-bottom_nav div[data-testid="stColumn"] {
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }
    .st-key-bottom_nav div[data-testid="stButton"] button {
        min-height: 50px;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        white-space: pre-line;
        font-size: 10.5px;
        line-height: 1.5;
        letter-spacing: 0.2px;
    }
    /* Onglet actif : icône + libellé en bleu de marque (visibilité de
       l'état du système — Nielsen) ; les deux autres restent neutres. */
    .st-key-bottom_nav button[data-testid="stBaseButton-primary"] {
        color: var(--ct-blue) !important;
        font-weight: 800;
    }
    .st-key-bottom_nav button[data-testid="stBaseButton-secondary"] {
        color: var(--ct-muted) !important;
        font-weight: 600;
    }
    .st-key-bottom_nav button[data-testid="stBaseButton-secondary"]:hover {
        background: #EEF2F7 !important;
        color: var(--ct-blue) !important;
    }
}

/* Téléphones très étroits (ex. iPhone SE 1ère génération, 320px) :
   encore un cran de marge en moins pour éviter tout risque de
   débordement horizontal. */
@media (max-width: 360px) {
    [data-testid="stMainBlockContainer"], .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }
    .ct-ring-outer { width: 132px; height: 132px; }
    .ct-ring-inner { width: 100px; height: 100px; }
    .ct-ring-value { font-size: 26px; }
}
</style>
"""


def app_header(subtitle: str) -> str:
    """En-tête de marque commun aux 3 écrans : le bouclier CamerTrust
    (logo) suivi du nom de l'application et du sous-titre de l'écran —
    remplace un `st.title()` texte par un vrai logo, reconnaissable même
    sans lire un seul mot (norme de branding des applications mobiles
    grand public)."""
    return (
        f'<div class="ct-app-header">'
        f'<span class="ct-logo">{LOGO_IMG}</span>'
        f'<div class="ct-app-header-text">'
        f'<div class="ct-app-header-title">CamerTrust</div>'
        f'<div class="ct-app-header-subtitle">{subtitle}</div>'
        f'</div></div>'
    )


def badge(text: str, kind: str = "neutral") -> str:
    """Petite pastille de statut colorée (vert/or/rouge/gris), utilisée
    partout où l'app affiche un état (alerte, connexion, etc.) — la
    couleur porte l'information avant même la lecture du texte."""
    return f'<span class="ct-badge ct-badge-{kind}">{text}</span>'


def score_ring(score: int) -> str:
    """Anneau de score façon application bancaire : la couleur suit le
    même code que le reste de l'app (>=70 sûr, 40-69 moyen, <40 faible)."""
    if score >= 70:
        color, caption, kind = TEAL, "Bon niveau de confiance", "success"
    elif score >= 40:
        color, caption, kind = GOLD, "Niveau de confiance moyen", "warning"
    else:
        color, caption, kind = RED, "Niveau de confiance faible", "danger"
    pct = max(0, min(100, score))
    ring = (
        f'<div class="ct-ring-outer" style="--pct:{pct}%; --ring-color:{color};">'
        f'<div class="ct-ring-inner">'
        f'<div class="ct-ring-value">{score}</div>'
        f'<div class="ct-ring-max">/ 100</div>'
        f'</div></div>'
        f'<div class="ct-ring-caption">{badge(caption, kind)}</div>'
    )
    return ring


# Les 3 écrans d'E3, dans l'ordre où ils apparaissaient déjà dans la barre
# latérale native de Streamlit — (identifiant, icône, libellé court, chemin
# tel qu'attendu par st.switch_page).
_NAV_PAGES = [
    ("app", "📱", "Terminal", "app.py"),
    ("espace", "📲", "Espace", "pages/1_📲_Espace_client.py"),
    ("console", "📊", "Console", "pages/2_📊_Console_supervision.py"),
]


def bottom_nav(active: str) -> None:
    """Barre de navigation à 3 icônes, fixée en bas de l'écran sur mobile
    (masquée sur bureau, voir PHONE_CSS) — remplace les liens de page que
    Streamlit range normalement dans la barre latérale. Fixée, donc
    toujours accessible en un tap sans avoir à faire défiler la page pour
    la retrouver, exactement comme la barre d'onglets d'une app mobile
    grand public (WhatsApp, Instagram)."""
    with st.container(key="bottom_nav"):
        cols = st.columns(3)
        for col, (key, icon, label, target) in zip(cols, _NAV_PAGES):
            with col:
                is_active = key == active
                # "  \n" (deux espaces avant le saut de ligne) est la
                # syntaxe Markdown d'un retour à la ligne forcé : c'est ce
                # qui sépare l'icône du libellé sur deux lignes dans le
                # bouton, plutôt qu'un simple "\n" que Markdown réduirait
                # à une espace.
                label_md = f"{icon}  \n{label}"
                if st.button(
                    label_md, key=f"navbtn_{key}", width='stretch',
                    type="primary" if is_active else "secondary",
                ):
                    if not is_active:
                        st.switch_page(target)


def settings_trigger(render_fn) -> None:
    """Icône ⚙️ affichée sur la page (visible sur mobile seulement, voir
    PHONE_CSS) qui ouvre en popover les réglages autrement rangés dans la
    barre latérale — cette dernière étant masquée sur mobile, ses options
    restent ainsi accessibles directement sur l'écran plutôt que perdues.
    `render_fn` est appelée à l'intérieur du popover pour en dessiner le
    contenu (partagée avec la barre latérale, pour que les deux surfaces
    restent synchronisées)."""
    with st.container(key="settings_trigger"):
        with st.popover("⚙️"):
            render_fn()
