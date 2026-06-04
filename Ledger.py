class Ledger :
    def __init__(self):
        self.transactions = []

    def add_transaction(self, transaction):
        self.transactions.append(transaction)

    def get_balance(self):
        return sum(transaction.amount for transaction in self.transactions)

    def __str__(self):
        return f"Ledger(transactions={self.transactions})"