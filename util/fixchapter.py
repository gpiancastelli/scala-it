#!/usr/bin/env python

import lxml.html
import sys

filename = sys.argv[1]

d = lxml.html.parse(filename).getroot()

for comment in d.find_class('comment_container'):
    parent = comment.getparent()
    parent.remove(comment)

form = d.get_element_by_id('comment_form_main')
form.getparent().remove(form)

print lxml.html.tostring(d, pretty_print=True)
