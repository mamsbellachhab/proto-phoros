ORDINALS = {
    1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
    6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th",
}

COMPANY_LETTERS = ["A", "B", "C", "D", "E", "F"]

FIRST_NAMES = [
    "Marcus", "Elena", "Karim", "Sofia", "David", "Amara", "Lucas",
    "Fatima", "Nikolai", "Priya", "Tomas", "Aisha", "Viktor", "Layla",
    "Hugo", "Nadia", "Ismael", "Clara", "Rashid", "Noor",
]

LAST_NAMES = [
    "Voss", "Hidalgo", "Mansour", "Petrov", "Castillo", "Okafor",
    "Lindqvist", "Benali", "Santos", "Kowalski", "Reyes", "Haddad",
    "Bergman", "Duarte", "Novak", "Achour",
]


def ordinal(n):
    return ORDINALS.get(n, f"{n}th")
