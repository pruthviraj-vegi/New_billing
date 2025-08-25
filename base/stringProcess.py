class StringProcessor:
    """
    This class processes strings by cleaning them (removing spaces, slashes, question marks, and commas)
    and converting them to different cases. It also handles the case where None or an empty string is passed.
    """

    def __init__(self, input_string=None):
        """
        Initializes the StringProcessor object.

        Args:
            input_string (str, optional): The input string to be processed. Defaults to None.
        """
        if input_string is None:
            self.input_string = ""
            self.cleaned_string = ""
        else:
            self.input_string = input_string
            self.clean()

    def clean(self):
        """
        Cleans the input string by removing spaces, slashes, question marks, and commas.
        """
        cleaned_string = " ".join(self.input_string.split())
        cleaned_string = (
            cleaned_string.replace("/", "").replace("?", "").replace(",", "")
        )
        self.cleaned_string = cleaned_string.upper()

    def toUppercase(self):
        """
        Returns the cleaned string in uppercase.

        Returns:
            str: The cleaned string in uppercase.
        """
        return self.cleaned_string

    def toLowercase(self):
        """
        Returns the cleaned string in lowercase.

        Returns:
            str: The cleaned string in lowercase.
        """
        return self.cleaned_string.lower()

    def toTitle(self):
        """
        Returns the cleaned string in title case (first letter of each word capitalized).

        Returns:
            str: The cleaned string in title case.
        """
        return self.cleaned_string.title()

    def toCapitalize(self):
        """
        Returns the cleaned string with only the first letter capitalized.

        Returns:
            str: The cleaned string with the first letter capitalized.
        """
        return self.cleaned_string.capitalize()


def currency_inr(amount):
    if amount is None:
        return "0.00"
    
    try:
        decimal_amount = float(amount)
        formatted = "{:,.2f}".format(decimal_amount)
        # Convert to Indian format
        parts = formatted.split('.')
        parts[0] = parts[0].replace(',', '')
        parts[0] = '{:,}'.format(int(parts[0]))[::-1].replace(',', ',', 1)[::-1]
        return f"{'.'.join(parts)}"
    except:
        return f"{amount}"
    

def adjust_name(name, length=10):
    """Truncate or pad name to specified length"""
    if len(name) > length:
        return name[:length] + '...'
    return name.ljust(length)
