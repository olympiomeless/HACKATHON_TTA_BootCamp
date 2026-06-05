#Création de la classe User
class User():
     def __init__(self, Id_user, name, email, password, Date_de_Naissance, adresse, category, ledger,  phone_number, gender, id_compte, active=True):
        self.name = name
        self.email = email
        self.password = password
        self.Date_de_Naissance = Date_de_Naissance
        self.adresse = adresse
        self.category = category
        self.categories = [] #On n'est pas obligés de mettre la liste vide le __init__
        self.ledger = ledger
        self.Id_user = Id_user
        self.phone_number = phone_number
        self.gender = gender
        self.id_compte = id_compte
        self.active = active
    #CREATION DES DIFFERENTES METHODES DE LA CLASSE

    #Méthode pour afficher les informations de l'utilisateur
     def afficher(self):
        if not self.active:
         print("Compte désactivé, action impossible")
        else:
         print(f"Id_user : {self.Id_user},\n name : {self.name},\n email : {self.email},\n password : {self.password},\n Date_de_Naissance : {self.Date_de_Naissance},\n adresse : {self.adresse},\n category : {self.category},\n ledger : {self.ledger},\n phone_number : {self.phone_number},\n gender  : {self.gender},\n id_compte = {self.id_compte}")  
            
    #Méthode pour mettre à jour les informations de l'utilisateur
     def update_profile(self, new_name=None, new_email=None, new_password=None, new_Date_de_Naissance=None, new_adresse=None, new_category=None, new_ledger=None, new_phone_number=None):
        if new_name is not None:
            self.name = new_name

        if new_email is not None:
            self.email = new_email

        if new_password is not None:
            self.password = new_password 

        if new_Date_de_Naissance is not None:
            self.Date_de_Naissance = new_Date_de_Naissance

        if new_adresse is not None:
            self.adresse = new_adresse

        if new_category is not None:
            self.category = new_category

        if new_ledger is not None:
            self.ledger = new_ledger

        if new_phone_number is not None:
            self.phone_number = new_phone_number

        print(f"User {self.Id_user} profile has been updated.")

    #Méthode pour supprimer le compte de l'utilisateur
     def delete_account(self):
       self.active = False
       print(f"User {self.Id_user} account has been deleted.")

    #Creation de Ajouter_Category
     def Ajouter_Category(self,new_category):
       if not self.active:
        print("Compte désactivé, vous ne pouvez pas ajouter de catégorie")
       else:
          self.categories.append(new_category)

       if new_category not in self.categories:
            print("Catégorie ajoutée")
       else:
            print("Catégorie déjà existante")
       print(self.categories)


     def Ajouter_Category(self, new_category):
      if not self.active:
        print("Compte désactivé, Vous ne pouvez pas ajouter de catégorie")
        return 
      if new_category in self.categories:
            print("Catégorie déjà existante")
      else:
            self.categories.append(new_category)
            print("Catégorie ajoutée")

            print(self.categories)
            print("Catégories de l'utilisateur :")
      for cat in self.categories:
            print("-", cat)
    #  def Supprimer_Category(self, category_to_remove):
    #   if not self.active:
    #     print("Compte désactivé, Vous ne pouvez pas supprimer de catégorie")
    #     return 
    #   if category_to_remove in self.categories:
    #         self.categories.remove(category_to_remove)
    #         print("Catégorie supprimée")
    #   else:
    #         print("Catégorie non trouvée")
    #   #print(self.categories)
     def Faire_Transaction(self,numero_destinataire, Montant, code_de_validation):
        if not self.active:
            print("Compte désactivé, Vous ne pouvez pas effectuer de transaction")
            return 
        print(f"Transaction effectuée : Numéro_destinataire {numero_destinataire}, Montant {Montant}")

user1 = User("001", "Alice", "alice@example.com", "password123", "01/01/1990", "123 Main St", "admin", "ledger1", "123-456-7890", "female", "compte1")
user2 = User("002", "Bob", "bob@example.com", "password456", "02/02/1991", "456 Oak Ave", "user", "ledger2", "098-765-4321", "male", "compte2")
#user1.afficher()
# user1.update_profile(new_name="Alice Smith")
#user1.delete_account()
# user2.afficher()
#user1.Faire_Transaction("123-456-7890", 100, "code123")
