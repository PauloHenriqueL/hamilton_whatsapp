#!/usr/bin/env bash
# exit on error
set -o errexit

# Locale pt_BR.UTF-8 (formatação de datas/moeda) — best-effort: em ambientes
# sem apt-get/root (ex.: runtime nativo do Render) não deve quebrar o build.
# O Django cai no fallback de formatação se o locale não existir.
(
  apt-get update \
  && apt-get install -y --no-install-recommends locales \
  && sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen \
  && dpkg-reconfigure --frontend=noninteractive locales
) || echo "Locale pt_BR não instalado (sem apt-get/root) — seguindo sem ele."

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
