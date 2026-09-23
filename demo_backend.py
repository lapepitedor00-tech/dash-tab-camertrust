"""
CamerTrust — E3 — Simulateur de repli (« Plan B »)
====================================================

Ce module rejoue localement, en mémoire, le comportement attendu de l'API
d'E2 (voir `api_client.py` pour le contrat exact). Il sert à deux choses :

1. **Développement de l'émulateur sans dépendre d'E2** : E3 peut construire
   et tester tout le frontend avant que le service d'E2 ne soit déployé.
2. **Plan B de soutenance** (checklist E3, p.13 du plan) : si le réseau de
   l'école tombe ou que l'instance Render s'est endormie et ne répond pas
   à temps, l'émulateur bascule automatiquement ici et la démo reste
   jouable, avec les mêmes scénarios que ceux du catalogue de messages
   d'E4 (p.18 du plan).

Rien ici n'est un modèle de détection de fraude : c'est un scénario
scripté, suffisant pour montrer la boucle complète
inscription → alerte → réponse → blocage.

IMPORTANT pour l'intégration finale : dès que l'API réelle d'E2 est en
ligne, ce module n'est plus appelé (voir `api_client.API_ONLINE`) — aucune
donnée simulée ne doit apparaître dans le rapport ou la démo finale.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Messages abonné — recopiés tels quels du catalogue d'E4 (plan p.18) pour
# que l'émulateur affiche exactement les textes qui figureront dans le
# rapport et qui auront été validés par les tests d'acceptation (S11).
# Si E4 fait évoluer une formulation suite aux tests utilisateurs, mettre
# à jour UNIQUEMENT ce dictionnaire : le reste du code ne change pas.
# ---------------------------------------------------------------------------
MESSAGES = {
    "confirmation_inscription": (
        "CamerTrust est active sur votre compte. Nous vous previendrons si "
        "une operation sort de vos habitudes. Pour arreter : *888*6#. Nous "
        "ne demandons jamais votre code."
    ),
    "alerte_risque_eleve": (
        "CamerTrust : {type_op} de {montant} FCFA a {heure} vers un numero "
        "inconnu. Inhabituel pour vous. Repondez 1 = c'est moi, 2 = ce "
        "n'est pas moi."
    ),
    "reponse_2": (
        "Compte protege. Vos transferts sont suspendus 30 min. Un agent "
        "est informe. Pour reactiver : *888*9#. Nous ne demandons jamais "
        "votre code."
    ),
    "reponse_1": (
        "Merci. Operation validee. CamerTrust retiendra moins cette "
        "habitude pour ce type d'operation."
    ),
    "absence_reponse": (
        "CamerTrust : sans reponse de votre part, aucune action n'a ete "
        "prise. Consultez vos alertes au *888*2#."
    ),
    "desinscription": (
        "CamerTrust est desactivee. Vos donnees d'analyse sont effacees. "
        "Pour revenir un jour : *888*1#. Merci."
    ),
}


@dataclass
class DemoUser:
    user_id: str
    phone_number: str
    trust_score: int = 82
    plafond: int = 500_000
    plafond_nocturne: int = 100_000
    liste_blanche: list = field(default_factory=list)
    canal_prefere: str = "ussd"
    langue: str = "fr"
    inscrit: bool = True


@dataclass
class DemoAlert:
    alert_id: str
    user_id: str
    montant: int
    type_op: str
    destinataire: str
    heure: str
    motif: str
    statut: str = "en_attente"  # en_attente | confirmee | bloquee
    horodatage: datetime = field(default_factory=datetime.utcnow)


class DemoBackend:
    """État en mémoire, réinitialisé à chaque redémarrage du process
    Streamlit. Un seul scénario de démo est préchargé pour ne jamais
    présenter un émulateur vide devant le jury."""

    def __init__(self) -> None:
        self.users: dict[str, DemoUser] = {}
        self.alerts: dict[str, DemoAlert] = {}
        self.outbox: list[dict] = []
        self.ussd_sessions: dict[str, dict] = {}
        self._seed_demo_scenario()

    # -- amorçage --------------------------------------------------------
    def _seed_demo_scenario(self) -> None:
        u = DemoUser(user_id="C123", phone_number="+237690000123", trust_score=88)
        self.users[u.user_id] = u
        # Une alerte déjà en attente, prête pour la démo (jalon S7 du plan :
        # « parcours de bout en bout jouable, même grossièrement »).
        self.trigger_alert_scenario(u.user_id, montant=450_000, type_op="retrait",
                                     destinataire="numero inconnu", heure="02h14")

    # -- transactions / scoring -------------------------------------------
    def score_transaction(self, user_id: str, amount: int, type_op: str,
                           hour: int, destinataire: str = "numero inconnu") -> dict:
        """Reproduit grossièrement la règle documentée par E1 (plan p.4) :
        montant élevé + heure inhabituelle + destinataire jamais vu ⇒ score
        rouge. Sinon score vert, aucune notification."""
        time.sleep(0.05)  # latence simulée, réaliste pour la démo
        risque = amount >= 200_000 and (hour <= 5 or hour >= 22)
        if risque:
            heure_str = f"{hour:02d}h{random.randint(0, 59):02d}"
            alert = self.trigger_alert_scenario(
                user_id, montant=amount, type_op=type_op,
                destinataire=destinataire, heure=heure_str,
            )
            return {
                "is_fraud": True,
                "score": round(random.uniform(0.82, 0.97), 2),
                "motif": alert.motif,
                "latence_ms": random.randint(120, 480),
                "alert_id": alert.alert_id,
            }
        return {
            "is_fraud": False,
            "score": round(random.uniform(0.02, 0.15), 2),
            "motif": "transaction conforme aux habitudes du compte",
            "latence_ms": random.randint(40, 180),
        }

    def trigger_alert_scenario(self, user_id: str, montant: int, type_op: str,
                                destinataire: str, heure: str) -> DemoAlert:
        alert_id = str(uuid.uuid4())[:8]
        motif = f"{type_op} inhabituel : {montant:,} FCFA a {heure}, {destinataire}".replace(",", " ")
        alert = DemoAlert(alert_id=alert_id, user_id=user_id, montant=montant,
                           type_op=type_op, destinataire=destinataire, heure=heure,
                           motif=motif)
        self.alerts[alert_id] = alert
        corps = MESSAGES["alerte_risque_eleve"].format(
            type_op=type_op, montant=f"{montant:,}".replace(",", " "), heure=heure,
        )
        self._send_sms(user_id, corps, alert_id=alert_id)
        return alert

    # -- alertes / réponses -------------------------------------------------
    def get_alerts(self, user_id: str) -> list[dict]:
        return [
            {
                "alert_id": a.alert_id,
                "montant": a.montant,
                "type_op": a.type_op,
                "heure": a.heure,
                "motif": a.motif,
                "statut": a.statut,
                "horodatage": a.horodatage.isoformat(),
            }
            for a in self.alerts.values() if a.user_id == user_id
        ]

    def respond_alert(self, alert_id: str, reponse: int) -> dict:
        alert = self.alerts.get(alert_id)
        if alert is None:
            return {"error": "alerte inconnue"}
        if reponse == 1:
            alert.statut = "confirmee"
            self._send_sms(alert.user_id, MESSAGES["reponse_1"])
        elif reponse == 2:
            alert.statut = "bloquee"
            self._send_sms(alert.user_id, MESSAGES["reponse_2"])
        return {"alert_id": alert_id, "statut": alert.statut}

    # -- comptes / réglages ---------------------------------------------
    def register_user(self, phone_number: str) -> dict:
        user_id = f"C{random.randint(100, 999)}"
        self.users[user_id] = DemoUser(user_id=user_id, phone_number=phone_number)
        self._send_sms(user_id, MESSAGES["confirmation_inscription"])
        return {"user_id": user_id, "phone_number": phone_number}

    def delete_user(self, user_id: str) -> dict:
        if user_id in self.users:
            self._send_sms(user_id, MESSAGES["desinscription"])
            del self.users[user_id]
            return {"deleted": True}
        return {"deleted": False}

    def get_settings(self, user_id: str) -> dict:
        u = self.users.get(user_id)
        if u is None:
            return {}
        return {
            "plafond": u.plafond,
            "plafond_nocturne": u.plafond_nocturne,
            "liste_blanche": u.liste_blanche,
            "canal_prefere": u.canal_prefere,
            "langue": u.langue,
        }

    def put_settings(self, user_id: str, **kwargs) -> dict:
        u = self.users.get(user_id)
        if u is None:
            return {"error": "utilisateur inconnu"}
        for k, v in kwargs.items():
            if hasattr(u, k) and v is not None:
                setattr(u, k, v)
        return self.get_settings(user_id)

    def get_trustscore(self, user_id: str) -> dict:
        u = self.users.get(user_id)
        if u is None:
            return {"score": None}
        return {"score": u.trust_score}

    def report_fraud(self, user_id: str, description: str) -> dict:
        return {"received": True, "reference": str(uuid.uuid4())[:8]}

    # -- USSD --------------------------------------------------------------
    def ussd(self, session_id: str, phone_number: str, text: str) -> dict:
        """Reproduit le protocole CON/END d'un agrégateur USSD réel : à
        chaque requête, `text` contient TOUTE la saisie cumulée depuis le
        début de la session, séparée par des « * »."""
        steps = [s for s in text.split("*") if s != ""] if text else []
        user = self._find_by_phone(phone_number)

        if not steps:
            menu = (
                "CON CamerTrust\n"
                "1. Mon score de confiance\n2. Mes alertes\n3. Mes plafonds\n"
                "4. Mes numeros habituels\n5. Signaler une fraude\n"
                "6. Me desinscrire"
            )
            return {"response": menu}

        choix = steps[0]
        if user is None:
            return {"response": "END Compte inconnu. Composez *888# apres inscription."}

        if choix == "1":
            return {"response": f"END Votre score de confiance : {user.trust_score}/100"}
        if choix == "2":
            alerts = self.get_alerts(user.user_id)
            if not alerts:
                return {"response": "END Aucune alerte recente."}
            derniere = alerts[-1]
            return {"response": (
                f"END Derniere alerte : {derniere['type_op']} {derniere['montant']} "
                f"FCFA a {derniere['heure']} — statut : {derniere['statut']}"
            )}
        if choix == "3":
            if len(steps) == 1:
                return {"response": (
                    f"CON Plafond actuel : {user.plafond} FCFA\n"
                    f"Plafond nocturne : {user.plafond_nocturne} FCFA\n"
                    "1. Modifier le plafond\n2. Retour"
                )}
            if len(steps) == 2 and steps[1] == "1":
                return {"response": "CON Entrez le nouveau plafond (FCFA) :"}
            if len(steps) == 3 and steps[1] == "1":
                try:
                    nouveau = int(steps[2])
                    user.plafond = nouveau
                    return {"response": f"END Plafond mis a jour : {nouveau} FCFA."}
                except ValueError:
                    return {"response": "END Montant invalide."}
            return {"response": "END Session terminee."}
        if choix == "4":
            return {"response": (
                "END Numeros habituels : " +
                (", ".join(user.liste_blanche) if user.liste_blanche else "aucun enregistre")
            )}
        if choix == "5":
            self.report_fraud(user.user_id, "signalement via menu USSD")
            return {"response": "END Signalement enregistre. Un agent vous contactera si besoin."}
        if choix == "6":
            self.delete_user(user.user_id)
            return {"response": "END Vous etes desinscrit. Vos donnees ont ete effacees."}

        return {"response": "END Choix invalide."}

    # -- réponse par SMS (option « 1 » / « 2 » tapée directement dans le
    # fil de messages, sans repasser par le menu USSD) --------------------
    def sms_inbound(self, phone_number: str, texte: str) -> dict:
        user = self._find_by_phone(phone_number)
        if user is None or texte.strip() not in ("1", "2"):
            return {"traite": False}
        alertes_en_attente = [a for a in self.alerts.values()
                               if a.user_id == user.user_id and a.statut == "en_attente"]
        if not alertes_en_attente:
            return {"traite": False}
        alerte = sorted(alertes_en_attente, key=lambda a: a.horodatage)[-1]
        return {"traite": True, **self.respond_alert(alerte.alert_id, int(texte.strip()))}

    # -- outbox / supervision ----------------------------------------------
    def get_outbox(self, phone_number: str | None = None) -> list[dict]:
        if phone_number is None:
            return list(self.outbox)
        user = self._find_by_phone(phone_number)
        if user is None:
            return []
        return [m for m in self.outbox if m["user_id"] == user.user_id]

    def get_admin_stats(self) -> dict:
        total_tx = len(self.alerts) + random.randint(150, 400)
        alertes_jour = len(self.alerts)
        repondues = sum(1 for a in self.alerts.values() if a.statut != "en_attente")
        taux_reponse = round(100 * repondues / alertes_jour, 1) if alertes_jour else 0.0
        bloquees = sum(1 for a in self.alerts.values() if a.statut == "bloquee")
        return {
            "transactions_jour": total_tx,
            "alertes_jour": alertes_jour,
            "taux_reponse_pct": taux_reponse,
            "alertes_bloquees": bloquees,
        }

    def get_admin_alerts(self) -> list[dict]:
        return [
            {
                "alert_id": a.alert_id,
                "user_id": a.user_id,
                "montant": a.montant,
                "type_op": a.type_op,
                "heure": a.heure,
                "statut": a.statut,
                "horodatage": a.horodatage.isoformat(),
            }
            for a in sorted(self.alerts.values(), key=lambda a: a.horodatage, reverse=True)
        ]

    # -- utilitaires internes ----------------------------------------------
    def _find_by_phone(self, phone_number: str) -> DemoUser | None:
        for u in self.users.values():
            if u.phone_number == phone_number:
                return u
        return None

    def _send_sms(self, user_id: str, corps: str, alert_id: str | None = None) -> None:
        user = self.users.get(user_id)
        self.outbox.append({
            "id": str(uuid.uuid4())[:8],
            "user_id": user_id,
            "phone_number": user.phone_number if user else None,
            "body": corps,
            "alert_id": alert_id,
            "horodatage": datetime.utcnow().isoformat(),
        })


# Instance unique partagée par toute la session Streamlit — voir
# api_client.get_backend() qui la range dans st.session_state pour qu'elle
# survive aux ré-exécutions du script (comportement normal de Streamlit).
def new_backend() -> DemoBackend:
    return DemoBackend()
