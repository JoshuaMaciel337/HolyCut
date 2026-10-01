#!/bin/sh
# O volume do cache chega como root. O worker roda como holycut, o mesmo usuário da API.
chown holycut:holycut /cache/huggingface
exec gosu holycut "$@"
