import re
import phonenumbers
from typing import Tuple, Optional


class PhoneNumberHandler:
    # Common country codes mapping
    COUNTRY_CODES = {
        "1": "US",  # USA/Canada
        "44": "GB",  # UK
        "91": "IN",  # India
        "61": "AU",  # Australia
        "86": "CN",  # China
        "49": "DE",  # Germany
        "33": "FR",  # France
        "81": "JP",  # Japan
        "7": "RU",  # Russia/Kazakhstan
        "52": "MX",  # Mexico
        "55": "BR",  # Brazil
        "34": "ES",  # Spain
        "39": "IT",  # Italy
        "82": "KR",  # South Korea
    }

    @staticmethod
    def normalize(number: str, default_country: str = "US") -> str:
        """
        Normalize phone number by removing spaces, +, 00 and formatting consistently
        """
        if not number:
            return ""

        # Remove all non-digit characters except +
        number = re.sub(r"[^\d+]", "", number.strip())

        # Handle 00 prefix (international)
        if number.startswith("00"):
            number = "+" + number[2:]

        # Ensure + prefix for international
        if not number.startswith("+"):
            # Check if it might be international without +
            if len(number) > 10:  # Suspiciously long for local
                # Try to detect country code
                for code in sorted(
                    PhoneNumberHandler.COUNTRY_CODES.keys(), key=len, reverse=True
                ):
                    if number.startswith(code):
                        number = "+" + number
                        break

        return number

    @staticmethod
    def validate(number: str, country: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Validate phone number and return (is_valid, normalized_number, error_message)
        """
        try:
            # Normalize first
            normalized = PhoneNumberHandler.normalize(number)

            # Parse the number
            if normalized.startswith("+"):
                parsed = phonenumbers.parse(normalized, None)
            else:
                # Use default country if provided, else try to detect
                if not country:
                    # Try to detect from first digits
                    for code, cntry in PhoneNumberHandler.COUNTRY_CODES.items():
                        if normalized.startswith(code):
                            country = cntry
                            break
                parsed = phonenumbers.parse(normalized, country or "US")

            # Validate
            if phonenumbers.is_valid_number(parsed):
                # Format in international format
                international = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
                e164 = phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )
                return True, e164, ""
            else:
                return False, normalized, "Invalid phone number"

        except Exception as e:
            return False, number, str(e)

    @staticmethod
    def extract_country_code(number: str) -> Tuple[Optional[str], str]:
        """
        Extract country code from number
        Returns (country_code, remaining_number)
        """
        normalized = PhoneNumberHandler.normalize(number)

        if normalized.startswith("+"):
            # Match longest possible country code first
            for i in range(1, 4):  # Country codes are 1-3 digits
                if i <= len(normalized) - 1:
                    potential_code = normalized[1 : i + 1]
                    if potential_code in PhoneNumberHandler.COUNTRY_CODES:
                        return potential_code, normalized[i + 1 :]

        return None, normalized

    @staticmethod
    def format_pretty(number: str, country: Optional[str] = None) -> str:
        """Format number in a human-readable way"""
        try:
            if number.startswith("+"):
                parsed = phonenumbers.parse(number, None)
            else:
                parsed = phonenumbers.parse(number, country or "US")

            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.NATIONAL
                )
            return number
        except:
            return number


# Convenience functions
def normalize_phone(number: str, default_country: str = "US") -> str:
    """Quick normalize function"""
    return PhoneNumberHandler.normalize(number, default_country)


def validate_phone(number: str, country: Optional[str] = None) -> bool:
    """Quick validate function"""
    is_valid, _, _ = PhoneNumberHandler.validate(number, country)
    return is_valid


def clean_phone_number(number: str, country: Optional[str] = None) -> str:
    """
    One-step function to normalize and validate
    Returns normalized E.164 format if valid, empty string if invalid
    """
    is_valid, normalized, error = PhoneNumberHandler.validate(number, country)
    return normalized if is_valid else ""


# Initialize handler
handler = PhoneNumberHandler()

# Test various formats
test_numbers = [
    "+1 212 555 1234",
    "001 212 555 1234",
    "2125551234",
    "+44 20 7946 0958",
    "0044 20 7946 0958",
    "+91 98765 43210",
    "9876543210",  # Local Indian number (needs country detection)
    "+49 30 123456",
    "030 123456",  # Local German number
]

for number in test_numbers:
    normalized = handler.normalize(number)
    is_valid, e164, error = handler.validate(number)
    country_code, remaining = handler.extract_country_code(number)
    pretty = handler.format_pretty(number)

    print(f"Original: {number}")
    print(f"Normalized: {normalized}")
    print(f"Valid: {is_valid}")
    if is_valid:
        print(f"E.164: {e164}")
        print(f"Pretty: {pretty}")
    else:
        print(f"Error: {error}")
    print(f"Country code: {country_code}, Remaining: {remaining}")
    print("-" * 50)

# Quick one-step cleaning
cleaned = clean_phone_number("+1 (212) 555-1234")
print(f"Cleaned: {cleaned}")  # +12125551234

# Validate only
if validate_phone("+44 20 7946 0958"):
    print("Valid UK number")
