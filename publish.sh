#!/bin/bash
rm dist/*.whl
rm dist/*.tar.gz

uv build
uv publish