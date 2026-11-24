from typing import Annotated

import email_validator
from pydantic import AfterValidator


def parse_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Enter an email address.")
    try:
        result = email_validator.validate_email(value.strip(), check_deliverability=False, test_environment=True)
    except email_validator.EmailNotValidError as exc:
        raise ValueError("Enter a valid email address.") from exc
    return result.normalized


EmailAddress = Annotated[str, AfterValidator(parse_email)]
