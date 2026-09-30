#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala o locale pt_BR.UTF-8 (formatação de datas/moeda).
apt-get update && apt-get install -y --no-install-recommends locales
sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen
dpkg-reconfigure --frontend=noninteractive locales

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
