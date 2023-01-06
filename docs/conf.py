project = 'walnats'
copyright = '2022, @orsinium'
author = '@orsinium'
templates_path = ['_templates']
html_theme = 'alabaster'
autodoc_typehints_format = 'short'
autodoc_preserve_defaults = True
autodoc_member_order = 'bysource'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'myst_parser',
]
