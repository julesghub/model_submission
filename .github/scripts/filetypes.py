import filetype

# Hack to support SVG files
# Are there any other files that filetype doesn't natively recognise?
class Svg(filetype.Type):
    """A custom filetype.Type subclass adding support for SVG image files."""

    MIME = 'image/svg+xml'
    EXTENSION = 'svg'

    def __init__(self):
        """Initialise the Svg type with its MIME type and file extension."""
        super().__init__(
            mime=Svg.MIME,
            extension=Svg.EXTENSION
        )

    def match(self, buf):
        """Return False; SVG matching is not implemented (files are identified externally).

        Args:
            buf: File buffer (unused).

        Returns:
            bool: Always False.
        """
        return False
