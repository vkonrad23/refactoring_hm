import datetime


def _split_name(name):
    parts = name.split(" ")
    return [part for part in parts if part]


def _format_last_name_first(name, uppercase_last_name=False):
    parts = _split_name(name)
    if len(parts) == 2:
        last_name = parts[1].upper() if uppercase_last_name else parts[1]
        return f"{last_name}, {parts[0]}"
    if len(parts) == 3:
        last_name = parts[2].upper() if uppercase_last_name else parts[2]
        return f"{last_name}, {parts[0]} {parts[1]}"
    return name


def format_name(name):
    return _format_last_name_first(name)


def format_name_for_report(name):
    return _format_last_name_first(name, uppercase_last_name=True)


def format_name_for_email(name):
    parts = _split_name(name)
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1][0]}."
    return name


def validate_email(email):
    if not email:
        return False

    parts = email.split("@")
    if len(parts) != 2:
        return False

    local_part, domain = parts
    return bool(local_part and domain and "." in domain)


def validate_phone(phone):
    if phone is None:
        return False
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10 or len(digits) > 15:
        return False
    return True


def get_letter_grade(avg):
    if avg >= 90:
        return "A"
    if avg >= 80:
        return "B"
    if avg >= 70:
        return "C"
    if avg >= 60:
        return "D"
    return "F"


def get_current_semester():
    month = datetime.datetime.now().month
    if 1 <= month <= 5:
        return "Spring"
    if 6 <= month <= 8:
        return "Summer"
    return "Fall"


def log_action(action, details):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {action}: {details}")
