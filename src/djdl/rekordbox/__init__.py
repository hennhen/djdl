"""The rekordbox 7 bridge.

rekordbox's own database is encrypted and unsafe to write to, so the supported
route in is a `rekordbox.xml` library file (`xml`) that rekordbox is pointed at
via its preferences file (`settings`).
"""


def escape_attr(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def unescape_attr(value):
    return (
        str(value)
        .replace("&quot;", '"')
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
    )
