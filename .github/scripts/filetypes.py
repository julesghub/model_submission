import filetype

# Hack to suport SVG files
# Are there any other files that filetype doesn't natively recognise?
class Svg(filetype.Type):
    MIME = 'image/svg+xml'
    EXTENSION = 'svg'

    def __init__(self):
        super(Svg, self).__init__(
            mime = Svg.MIME,
            extension = Svg.EXTENSION
            )

    def match(self, buf):
        """
        BY_AI: Always returns False because SVG detection is not implemented via magic bytes.

        SVG files are XML-based and do not have a unique binary signature, so byte-level
        detection is not used here. The filetype library will rely on MIME type information
        provided by the HTTP response headers instead.

        Parameters:
            buf (bytes): The byte buffer to examine.

        Returns:
            bool: Always False.
        """
        return False
