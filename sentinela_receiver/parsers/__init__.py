from .contact_id import ContactIdParser

PARSERS = {
    'contact_id': ContactIdParser,
}


def get_parser(name):
    cls = PARSERS.get(name)
    if not cls:
        raise ValueError(f"Unknown parser: {name}. Available: {list(PARSERS)}")
    return cls()
