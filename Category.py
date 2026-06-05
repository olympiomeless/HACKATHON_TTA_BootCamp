from datetime import datetime
from typing import List


class Category:
    def _init_(self, id_cat: int, libelle_cat: str, description: str = ""):
        self.id_cat = id_cat
        self.libelle_cat = libelle_cat
        self.description = description
        self.transactions: List[Transaction] = []

    def _str_(self):
        return f"Catégorie #{self.id_cat} - {self.libelle_cat} ({len(self.transactions)} tx)"

    @staticmethod
    def creation_category(categories: dict, id_cat: int, libelle_cat: str, description: str = ""):
        """Crée une nouvelle catégorie"""
        if libelle_cat in categories:
            print(f" Catégorie '{libelle_cat}' existe déjà.")
            return categories[libelle_cat]
        
        cat = Category(id_cat, libelle_cat, description)
        categories[libelle_cat] = cat
        print(f" Catégorie créée : {cat}")
        return cat

    def modification_cat(self, nouveau_libelle: str = None, nouvelle_description: str = None):
        """Modifie une catégorie"""
        if nouveau_libelle:
            self.libelle_cat = nouveau_libelle
        if nouvelle_description:
            self.description = nouvelle_description
        print(f" Catégorie modifiée : {self}")

    def suppression_cat(self, categories: dict):
        """Supprime une catégorie"""
        if self.libelle_cat in categories:
            del categories[self.libelle_cat]
            print(f" Catégorie '{self.libelle_cat}' supprimée.")
        else:
            print("Catégorie non trouvée.")

    def afficher_cat(self):
        """Affiche les détails de la catégorie"""
        print(f"\n=== {self.libelle_cat} ===")
        print(f"Description : {self.description}")
        print(f"Transactions: {len(self.transactions)}")
        for tx in self.transactions:
            print(f"   • {tx}")
        print("=" * 30)
    