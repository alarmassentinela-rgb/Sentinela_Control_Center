import re


class ContactIdParser:
    name = 'contact_id'
    pattern = re.compile(
        r"\[(?P<account>\w{1,4})\s*(?P<prefix>\w{2})\s*"
        r"(?P<qualifier>[ER])(?P<code>\w{3})\s*"
        r"(?P<partition>\w{2})\s*(?P<zone>\w{3})\]"
    )

    def parse(self, data: bytes):
        text = data.decode('utf-8', errors='ignore')
        m = self.pattern.search(text)
        if not m:
            return None
        return {
            'account': m.group('account').zfill(4),
            'qualifier': m.group('qualifier'),
            'code': m.group('code'),
            'partition': m.group('partition'),
            'zone': m.group('zone'),
        }
