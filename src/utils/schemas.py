"""
Module that contains some schemas that can be used to granularize the outputs from the crawler
"""
fedro_filetypes = ['pdf', 'html', 
                   'legal_xml', 'xml',
                   'zip', 
                   'xlsx', 'xls', 'docx', 'doc', 'dotx', 'pptx', 'ppt', 
                   'jpg', 'png',
                   'dxf', 'dwg', 'mpg']

fedro_filesplit = {'pdf': 'pdf',
                   'html': 'html',
                   'legal_xml': 'legal',
                   'zip': 'zip',
                   'xls': 'excel',
                   'xlsx': 'excel',
                   'doc': 'word',
                   'docx': 'word',
                   'dotx': 'word',
                   'pptx': 'powerpoint',
                   'ppt': 'powerpoint',
                   'jpg': 'images',
                   'png': 'images',
                   'dxf': 'cad',
                   'dwg': 'cad',
                   'xml': 'else',
                   'mpg': 'else',
                   'else': 'else'}