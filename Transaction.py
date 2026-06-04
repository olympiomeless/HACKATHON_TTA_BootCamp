class Transaction :
    def __init__(self, amount, date, description):
        self.amount = amount
        self.date = date
        self.description = description

    def __str__(self):
        return f"Transaction(amount={self.amount}, date={self.date}, description={self.description})"
    