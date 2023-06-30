#!/bin/bash
python example.py | prettier --stdin-filepath x.html | tee lol.html && xdg-open lol.html
