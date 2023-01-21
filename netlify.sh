#!/bin/bash
# This script is used by netlify
python3 -m pip install '.[docs]'
sphinx-build -W docs docs/build
