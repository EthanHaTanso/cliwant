"""
Data masking utilities for displaying sensitive information.
"""


def mask_account_number(account_number: str) -> str:
    """
    Mask account number for display.

    Examples:
        "123-456-789012" -> "***-***-789012"
        "1234567890123" -> "**********123"

    Args:
        account_number: Full account number

    Returns:
        Masked account number showing only last 4-6 digits
    """
    if not account_number:
        return ""

    # Remove any formatting
    clean = account_number.replace("-", "").replace(" ", "")

    if len(clean) <= 4:
        return clean

    # Show last 4-6 characters
    visible_length = min(6, len(clean) // 2)
    visible_part = clean[-visible_length:]

    # Reconstruct with original formatting if present
    if "-" in account_number:
        # Try to maintain dash formatting
        parts = account_number.split("-")
        masked_parts = []
        chars_remaining = len(clean) - visible_length

        for part in parts:
            if chars_remaining >= len(part):
                masked_parts.append("*" * len(part))
                chars_remaining -= len(part)
            elif chars_remaining > 0:
                masked_parts.append("*" * chars_remaining + part[chars_remaining:])
                chars_remaining = 0
            else:
                masked_parts.append(part)

        return "-".join(masked_parts)

    # No dashes - simple masking
    return "*" * (len(clean) - visible_length) + visible_part


def mask_email(email: str) -> str:
    """
    Mask email for display.

    Examples:
        "user@example.com" -> "u***@example.com"
        "john.doe@company.co.kr" -> "j*******@company.co.kr"

    Args:
        email: Full email address

    Returns:
        Masked email showing first letter and domain
    """
    if not email or "@" not in email:
        return email

    local, domain = email.rsplit("@", 1)

    if len(local) <= 1:
        return email

    masked_local = local[0] + "*" * (len(local) - 1)
    return f"{masked_local}@{domain}"
