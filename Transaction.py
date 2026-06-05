from datetime import datetime
from typing import Optional, List

class Transaction:
    def _init_(self, id_trans: int, montant: float, libelle: str, date: str = None, category=None):
        self.id_trans = id_trans
        self.montant = float(montant)
        self.libelle = libelle
        if date is None:
            self.date = datetime.now()
        elif isinstance(date, str):
            self.date = datetime.strptime(date, "%Y-%m-%d")
        else:
            self.date = date
        self.category = category

    def _str_(self):
        cat = f" | {self.category.libelle_cat}" if self.category else ""
        sign = "+" if self.montant > 0 else ""
        return f"[{self.id_trans}] {self.date.strftime('%d/%m/%Y')} | {sign}{self.montant:.2f}€ | {self.libelle}{cat}"

    def faire_transaction(self):
        """Simule la création d'une transaction"""
        print(f" Transaction {self.id_trans} effectuée : {self}")

    def annuler_transaction(self):
        """Annule une transaction (met le montant à 0)"""
        print(f" Transaction {self.id_trans} annulée.")
        self.montant = 0.0

    def afficher_detail_transaction(self):
        """Affiche les détails complets d'une transaction"""
        print("\n" + "-"*50)
        print(f"DETAIL TRANSACTION #{self.id_trans}")
        print("-"*50)
        print(f"Montant     : {self.montant:+.2f} €")
        print(f"Libellé     : {self.libelle}")
        print(f"Date        : {self.date.strftime('%d/%m/%Y')}")
        if self.category:
            print(f"Catégorie   : {self.category.libelle_cat}")
        print("-"*50)

    @staticmethod
    def rechercher_transaction(transactions: List['Transaction'], recherche: str):
        """Recherche une transaction par libellé ou ID"""
        results = [t for t in transactions if 
                  recherche.lower() in t.libelle.lower() or str(t.id_trans) == recherche]
        return results

    @staticmethod
    def consulter_solde(transactions: List['Transaction']) -> float:
        """Calcule le solde total"""
        return sum(t.montant for t in transactions)
