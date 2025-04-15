import re
from typing import Union
from collections import Counter
import datefinder


def number_str_cleanup(text):
    # remove currency string
    currencies = [
        "$",
        "€",
        "£",
        "¥",
        "₹",
        "₺",
        "₦",
        "₨",
        "₫",
        "₭",
        "₮",
        "₯",
        "₰",
        "₱",
        "₲",
        "₳",
        "₴",
        "₵",
        "₶",
        "₷",
        "₸",
        "₹",
        "₪",
        "₫",
        "Kč",
        "Ft",
        "zł",
        "lei",
        "₹",
        "Rs",
        "Rp",
        "RM",
        "CHF",
        "SEK",
        "DKK",
        "NOK",
        "ISK",
        "HRK",
        "BGN",
        "CZK",
        "HUF",
        "PLN",
        "RON",
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "INR",
        "TRY",
        "NGN",
        "PKR",
        "VND",
        "LAK",
        "MNT",
        "GRD",
        "PHP",
        "PYG",
        "ARS",
        "UAH",
        "GHS",
        "KZT",
        "NPR",
        "ZAR",
        "ILS",
        "VND",
        "CZK",
        "HUF",
        "PLN",
        "RON",
        "NOK",
        "LKR",
        "IDR",
        "MYR",
        "SGD",
        "CHF",
        "SEK",
        "DKK",
        "NOK",
        "ISK",
        "HRK",
        "BGN",
        "CZK",
        "HUF",
        "PLN",
        "RON",
        "United States Dollar",
        "Euro",
        "Pound Sterling",
        "Japanese Yen",
        "Indian Rupee",
        "Turkish Lira",
        "Nigerian Naira",
        "Pakistani Rupee",
        "Vietnamese Dong",
        "Lao Kip",
        "Mongolian Tugrik",
        "Greek Drachma",
        "Philippine Peso",
        "Paraguayan Guarani",
        "Argentine Peso",
        "Ukrainian Hryvnia",
        "Ghanaian Cedi",
        "Kazakhstani Tenge",
        "Nepalese Rupee",
        "South African Rand",
        "Israeli Shekel",
        "Vietnamese Dong",
        "Czech Koruna",
        "Hungarian Forint",
        "Polish Zloty",
        "Romanian Leu",
        "Norwegian Krone",
        "Sri Lankan Rupee",
        "Indonesian Rupiah",
        "Malaysian Ringgit",
        "Singapore Dollar",
        "Swiss Franc",
        "Swedish Krona",
        "Danish Krone",
        "Norwegian Krone",
        "Icelandic Krona",
        "Croatian Kuna",
        "Bulgarian Lev",
        "Czech Koruna",
        "Hungarian Forint",
        "Polish Zloty",
        "Romanian Leu",
    ]
    if not text:
        return 0.0
    for currency in currencies:
        text = text.replace(currency, "")
    # remove commas
    text = text.replace(",", "")
    # remove dots
    num_dots = Counter(text)["."]
    if num_dots > 1:
        text = (
            ".".join(text.split(".")[:-1]).replace(".", "") + "." + text.split(".")[-1]
        )
    # spaces cleanup
    text = text.strip()
    # trying to convert to float
    try:
        return float(text)
    except Exception as e:
        raise TypeError(f"Unable to convert text={text} to float with error:{e}")
        


def date_transformer(text):
    if not text:
        return None
    if "desember" in text.lower():
        text = text.lower().replace("desember", "december")
    matches = list(datefinder.find_dates(text))
    if matches:
        return str(matches[0])
    raise TypeError(f"Date with value={text}, is not currently supported by date_transformer!")


def full_address_concat(address, pin, state, city=""):
    return address + ", " + city + ", " + state + ", " + pin


def GetYear(date_string: str) -> int:
    """Returns the year for a given string."""
    match = re.search(r"\b(\d{4})\b", date_string)
    return int(match.group(1)) if match else 0


def GetQuarter(input_string: str) -> str:
    """Returns the quarter of the year for a given string."""
    match = re.search(r"([1-4])[Qq]", input_string)
    return f"{match.group(1)}Q" if match else ""


def GetCurrency(deal_string: str) -> str:
    """Extracts the currency symbol from a string."""
    # Define a dictionary to map currency symbols to their respective codes
    currency_map = {
        "$": "USD",
        "€": "EUR",
        "£": "GBP",
        "¥": "JPY",
        "kr": "SEK",
        "AUD": "AUD",
        "CAD": "CAD",
        "CHF": "CHF",
        "CNY": "CNY",
        "EUR": "EUR",
        "GBP": "GBP",
        "INR": "INR",
        "JPY": "JPY",
        "USD": "USD",
    }

    # Check if the input string contains a currency code (e.g., "AUD")
    code_match = re.search(r"[A-Z]{3}", deal_string)
    if code_match:
        # If a code is found, return it
        return code_match.group()
        # Check if the input string contains a currency symbol (e.g., "\$", "€")
    symbol_match = re.search(r"[\$€£¥]", deal_string)
    if symbol_match:
        # If a symbol is found, return its corresponding code
        return currency_map[symbol_match.group()]

    # If no code or symbol is found, return "Unknown"
    return "Unknown"


def GetDealAmount(deal_size_str: str) -> float:
    """Parse a deal size string and return the deal size as a float."""
    match = re.search(r"([\$€£¥]?)([\d\.]+)([KMB]?)", deal_size_str, re.IGNORECASE)
    if not match:
        return 0.0

    num = float(match.group(2))
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(
        match.group(3).upper(), 1
    )

    return num * multiplier


def identity(item_1: Union[str, int, float, bool]) -> Union[str, int, float, bool]:
    """Returns the value of item_1 without modification."""
    return item_1