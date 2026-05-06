"""Global configuration parameters for the M@TE (Model Atlas of The Earth) project."""

# Example of global parameters

# DOIS
MATE_DOI = 'http://dx.doi.org/10.25914/yrzp-g882'
MATE_WEBSITE = 'https://mate.science/'
MATE_GITHUB = 'https://github.com/ModelAtlasofTheEarth/'
MATE_GADI = '/g/data/nm08/MATE/'

#MATE_THREDDS_BASE = "https://dapds00.nci.org.au/thredds/catalog/nm08/MATE/{}/catalog.html"
#updated version: https://opus.nci.org.au/display/NDP/THREDDS+Upgrade
MATE_THREDDS_BASE = "https://thredds.nci.org.au/thredds/catalog/nm08/MATE/{}/catalog.html"

#URIs

#json-ld type records
NCI_RECORD = {'@type': 'Organization',
                 '@id': 'https://ror.org/04yx6dh41',
                 'name': 'National Computational Infrastructure'}

AUSCOPE_RECORD = {'@type': 'Organization',
                    '@id': 'https://ror.org/04s1m4564',
                    'name': 'AuScope'}
