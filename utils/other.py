

def pluralization_string(number: int, words: list[str]):
    """
    >>> self.utils.pluralization_string(num, ["жизнь", "жизни", "жизней"])
    >>> self.utils.pluralization_string(num, ["рубль", "рубля", "рублей"])
    >>> self.utils.pluralization_string(num, ["ручка", "ручки", "ручек"])
    >>> self.utils.pluralization_string(num, ["апельсин", "апельсина", "апельсинов"])
    """
    if number % 10 == 1 and number % 100 != 11:
        return f"{number} {words[0]}"
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return f"{number} {words[1]}"
    else:
        return f"{number} {words[2]}"
