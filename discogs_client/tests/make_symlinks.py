#!/usr/bin/env python
import os
import sys
from itertools import permutations

for name in sys.argv[1:]:
    print("doing {}".format(name))
    root, next = name.split('?')
    data, ext = next.split('.')
    elems = data.split('&')
    for permut in permutations(elems):
        link_name = "{}?{}.{}".format(root, '&'.join(permut), ext)
        if link_name == name:
            continue
        os.symlink(name, link_name)
        print("wrote {}".format(link_name))
