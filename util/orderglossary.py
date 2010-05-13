# -*- coding: utf-8 -*-

import lxml.html
import sys

oldfile, newfile = sys.argv[1:3]

glossary = lxml.html.parse(oldfile)
root = glossary.getroot()
dl = root.get_element_by_id('book').find('dl')
defs = dl.getchildren()

data = {}
for dt, dd in (defs[i:i+2] for i in xrange(0, len(defs), 2)):
    text = dt.text.lower() if dt.text is not None else ''
    for child in dt.getchildren():
        if child.text is not None:
            text += child.text.lower()
    if dt.tail is not None:
        text += tail.text.lower()
    data[text.strip()] = (dt, dd)
    dl.remove(dt)
    dl.remove(dd)

for k in sorted(data.keys()):
    dt, dd = data[k]
    dl.append(dt)
    dl.append(dd)

result = lxml.html.tostring(root, pretty_print=True)
for old, new in [('\r', ''),
                 # because apparently doing this stuff on Windows (and maybe
                 # without the explicit encoding support of Py3k) is crazy
                 ('&#195;&#160;', 'à'), ('&#195;&#168;', 'è'), ('&#195;&#172;', 'ì'),
                 ('&#195;&#178;', 'ò'), ('&#195;&#185;', 'ù'), ('&#195;&#169;', 'é'),
                 # trimming useless HTML closed tags
                 ('</p>', ''), ('</dd>', ''), ('</dt>', ''), ('</li>', ''), ('</html>', ''),
                 # more HTML trimming, for useless open/closed tags
                 ('<body>', ''), ('</body>', ''), ('<head>', ''), ('</head>', ''),
                 # adjust newlines
                 ('\n\n', '\n')]:
    result = result.replace(old, new)

with open(newfile, 'w') as f:
    f.write(result)