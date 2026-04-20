import re
import phonenumbers
from typing import Tuple, Optional


class PhoneNumberHandler:

    @staticmethod
    def normalize(number: str) -> str:
        """
        Normalize phone number by removing spaces, brackets, and handling '00' international prefix.
        """
        if not number:
            return ""

        # Remove all non-digit characters except +
        number = re.sub(r"[^\d+]", "", number.strip())

        # Handle European/Asian 00 prefix (international)
        if number.startswith("00"):
            number = "+" + number[2:]

        return number

    @staticmethod
    def validate(number: str, country: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Validate phone number and return (is_valid, normalized_number, error_message)
        """
        try:
            # 1. Strip spaces and letters
            normalized = PhoneNumberHandler.normalize(number)
            parsed = None

            # 2. Try parsing it exactly as it arrived
            if normalized.startswith("+"):
                parsed = phonenumbers.parse(normalized, None)
            else:
                # Try parsing it as a local number for the default country (e.g., US)
                try:
                    parsed = phonenumbers.parse(normalized, country or "US")
                    if not phonenumbers.is_valid_number(parsed):
                        raise ValueError("Invalid local number")
                except Exception:
                    # ⚡️ THE MAGIC FIX: It failed as a local number, so let's assume
                    # the user uploaded an international number but forgot the '+' sign!
                    try:
                        parsed = phonenumbers.parse("+" + normalized, None)
                    except Exception as e:
                        return False, normalized, f"Could not parse: {str(e)}"

            # 3. Final Validation Check
            if parsed and phonenumbers.is_valid_number(parsed):
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
        Extract country code from number cleanly using the Google library.
        Returns (country_code, remaining_number)
        """
        # Let our smart validate function figure out the actual number first
        is_valid, e164, _ = PhoneNumberHandler.validate(number)

        if is_valid:
            # Parse the clean + format
            parsed = phonenumbers.parse(e164, None)
            return str(parsed.country_code), str(parsed.national_number)

        # If it's a totally invalid number, just return the raw digits
        normalized = PhoneNumberHandler.normalize(number).replace("+", "")
        return None, normalized

    @staticmethod
    def format_pretty(number: str, country: Optional[str] = None) -> str:
        """Format number in a human-readable way"""
        is_valid, e164, _ = PhoneNumberHandler.validate(number, country)
        if is_valid:
            parsed = phonenumbers.parse(e164, None)
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            )
        return number


# Convenience functions
def normalize_phone(number: str) -> str:
    """Quick normalize function"""
    return PhoneNumberHandler.normalize(number)


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
