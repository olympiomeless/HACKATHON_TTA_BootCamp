# class User :
#     def __init__(self, name, email):
#         self.name = name
#         self.email = email

#     def __str__(self):
#         return f"User(name={self.name}, email={self.email})"
    
class User():
     def __init__(self, name, age,email, password):
        self.name = name
        self.age = age
        self.email = email
        self.password = password

        def __str__(self):
            return f"User(name={self.name}, age={self.age}, email={self.email}, password={self.password})"  
        def afficher(self):
            print(f"User(name={self.name}, age={self.age}, email={self.email}, password={self.password})")  

user1 = User("Alice", 30, "alice@example.com", "password123")
user1.afficher()