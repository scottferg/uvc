# monkeypatch the urlparse module so that it understands ssh URLs
# properly

import urlparse

if "ssh" not in urlparse.uses_netloc:
    urlparse.uses_netloc.append("ssh")
