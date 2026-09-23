"""
Tests du simulateur de repli (demo_backend.py).

Ce module est la seule logique « pure Python » d'E3 (le reste est de
l'interface Streamlit, testée manuellement via le parcours de démo — voir
README). Ces tests garantissent que le Plan B reste fiable si l'équipe le
retouche plus tard.

Lancer : `python -m pytest tests/ -v` depuis le dossier `dashboard/`.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_backend import DemoBackend, MESSAGES


class TestInscriptionEtDesinscription(unittest.TestCase):
    def setUp(self):
        self.backend = DemoBackend()

    def test_inscription_cree_un_compte_et_un_sms(self):
        nb_sms_avant = len(self.backend.outbox)
        res = self.backend.register_user("+237699000000")
        self.assertIn("user_id", res)
        self.assertIn(res["user_id"], self.backend.users)
        self.assertEqual(len(self.backend.outbox), nb_sms_avant + 1)
        self.assertIn("active sur votre compte", self.backend.outbox[-1]["body"])

    def test_desinscription_supprime_le_compte(self):
        res = self.backend.register_user("+237699000001")
        uid = res["user_id"]
        suppr = self.backend.delete_user(uid)
        self.assertTrue(suppr["deleted"])
        self.assertNotIn(uid, self.backend.users)


class TestScoringEtAlertes(unittest.TestCase):
    def setUp(self):
        self.backend = DemoBackend()  # C123 pré-chargé avec une alerte en attente

    def test_transaction_normale_ne_declenche_pas_d_alerte(self):
        nb_alertes_avant = len(self.backend.alerts)
        res = self.backend.score_transaction("C123", amount=5_000, type_op="achat", hour=14)
        self.assertFalse(res["is_fraud"])
        self.assertEqual(len(self.backend.alerts), nb_alertes_avant)

    def test_transaction_nocturne_elevee_declenche_une_alerte(self):
        nb_alertes_avant = len(self.backend.alerts)
        res = self.backend.score_transaction("C123", amount=800_000, type_op="retrait", hour=3)
        self.assertTrue(res["is_fraud"])
        self.assertIn("alert_id", res)
        self.assertEqual(len(self.backend.alerts), nb_alertes_avant + 1)

    def test_reponse_1_confirme_l_alerte(self):
        alertes = self.backend.get_alerts("C123")
        alerte_en_attente = next(a for a in alertes if a["statut"] == "en_attente")
        res = self.backend.respond_alert(alerte_en_attente["alert_id"], 1)
        self.assertEqual(res["statut"], "confirmee")

    def test_reponse_2_bloque_le_compte(self):
        alertes = self.backend.get_alerts("C123")
        alerte_en_attente = next(a for a in alertes if a["statut"] == "en_attente")
        res = self.backend.respond_alert(alerte_en_attente["alert_id"], 2)
        self.assertEqual(res["statut"], "bloquee")
        dernier_sms = self.backend.outbox[-1]["body"]
        self.assertEqual(dernier_sms, MESSAGES["reponse_2"])


class TestMenuUSSD(unittest.TestCase):
    def setUp(self):
        self.backend = DemoBackend()

    def test_menu_racine_liste_les_6_options(self):
        res = self.backend.ussd("sess1", "+237690000123", "")
        self.assertTrue(res["response"].startswith("CON"))
        for option in ["1.", "2.", "3.", "4.", "5.", "6."]:
            self.assertIn(option, res["response"])

    def test_option_1_affiche_le_score(self):
        res = self.backend.ussd("sess1", "+237690000123", "1")
        self.assertTrue(res["response"].startswith("END"))
        self.assertIn("/100", res["response"])

    def test_modification_du_plafond_bout_en_bout(self):
        r1 = self.backend.ussd("sess2", "+237690000123", "3")
        self.assertTrue(r1["response"].startswith("CON"))
        r2 = self.backend.ussd("sess2", "+237690000123", "3*1")
        self.assertTrue(r2["response"].startswith("CON"))
        r3 = self.backend.ussd("sess2", "+237690000123", "3*1*750000")
        self.assertTrue(r3["response"].startswith("END"))
        self.assertEqual(self.backend.users["C123"].plafond, 750_000)

    def test_numero_inconnu_refuse_l_acces(self):
        res = self.backend.ussd("sess3", "+237600000000", "1")
        self.assertTrue(res["response"].startswith("END"))
        self.assertIn("inconnu", res["response"])


class TestReponseParSMS(unittest.TestCase):
    def setUp(self):
        self.backend = DemoBackend()

    def test_reponse_2_par_sms_bloque_la_derniere_alerte_en_attente(self):
        res = self.backend.sms_inbound("+237690000123", "2")
        self.assertTrue(res["traite"])
        self.assertEqual(res["statut"], "bloquee")

    def test_texte_non_numerique_est_ignore(self):
        res = self.backend.sms_inbound("+237690000123", "bonjour")
        self.assertFalse(res["traite"])


class TestSupervision(unittest.TestCase):
    def test_statistiques_coherentes(self):
        backend = DemoBackend()
        backend.score_transaction("C123", amount=900_000, type_op="transfert", hour=2)
        stats = backend.get_admin_stats()
        self.assertGreaterEqual(stats["alertes_jour"], 2)  # celle du seed + celle déclenchée
        self.assertGreaterEqual(stats["transactions_jour"], stats["alertes_jour"])


if __name__ == "__main__":
    unittest.main()
