"""Popula o banco local com dados de demonstração (idempotente).

Uso:  python manage.py seed_demo

Cria um gestor, alguns terapeutas com login próprio, calendário semanal
(disponibilidade + blocos de atividade/tag), tags com tempo padrão e descrição,
e pacientes (ativos/inativos e aguardando encaminhamento). Serve só para ver as
telas em desenvolvimento — NÃO rodar contra produção.
"""
from datetime import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from principais.models import (
    Abordagem, Associado, HorarioDisponivel, Paciente, Tag, Terapeuta,
)

SENHA_PADRAO = "allos123"


class Command(BaseCommand):
    help = "Popula o banco com dados de demonstração (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Semeando dados de demonstração...")

        # --- Abordagens ---
        tcc, _ = Abordagem.objects.get_or_create(abordagem="TCC")
        psican, _ = Abordagem.objects.get_or_create(abordagem="Psicanálise")

        # --- Tags/atividades (tempo padrão + descrição) ---
        tags = {
            "supervisor": self._tag("supervisor", None, "Marca quem é supervisor."),
            "grupo_estudos": self._tag(
                "Grupo de estudos", Decimal("3"),
                "Grupo de estudo semanal (3h)."),
            "palestra": self._tag(
                "Palestra mensal", Decimal("2"),
                "Palestra aberta uma vez por mês (2h)."),
            "prefeitura": self._tag(
                "prefeitura", Decimal("0"),
                "Paciente isento (valor 0)."),
        }

        # --- Gestor (is_staff) ---
        self._user("gestor", is_staff=True, is_superuser=True,
                   first="Alan", last="Gestor")
        self.stdout.write("  gestor: login 'gestor' / senha 'allos123' (staff)")

        # Ana: 15h no total = 12h de disponibilidade + 3h de Grupo de estudos.
        # Com 2 pacientes ativos: ocupado = 3 (tag) + 2 = 5 → 5/15.
        ana = self._terapeuta(
            "ana", "Ana Terapeuta", tcc, pacientes_max=15,
            tags_atuais=[tags["grupo_estudos"]],
            tags_apto=[tags["palestra"]],
            horarios=[
                (0, time(8, 0), time(10, 0), tags["grupo_estudos"]),  # Seg 08-10 Grupo
                (0, time(10, 0), time(11, 0), None),                  # Seg 10-11 livre
                (2, time(14, 0), time(18, 0), None),                  # Qua 14-18 livre
                (4, time(9, 0), time(16, 0), None),                   # Sex 09-16 livre
                (0, time(11, 0), time(12, 0), tags["grupo_estudos"]), # +1h Grupo (3h total)
            ],
        )
        bruno = self._terapeuta(
            "bruno", "Bruno Supervisor", psican, pacientes_max=12,
            tags_atuais=[tags["supervisor"], tags["palestra"]],
            tags_apto=[tags["grupo_estudos"]],
            horarios=[
                (1, time(8, 0), time(10, 0), tags["palestra"]),  # Ter 08-10 Palestra
                (1, time(10, 0), time(12, 0), None),             # Ter 10-12 livre
                (3, time(13, 0), time(19, 0), None),             # Qui 13-19 livre
            ],
        )
        carla = self._terapeuta(
            "carla", "Carla Terapeuta", tcc, pacientes_max=5,
            tags_atuais=[],
            tags_apto=[tags["grupo_estudos"], tags["palestra"]],
            horarios=[
                (0, time(13, 0), time(18, 0), None),  # Seg 13-18 livre
                (2, time(8, 0), time(12, 0), None),   # Qua 08-12 livre
            ],
            supervisor=bruno,
        )
        for u in ("ana", "bruno", "carla"):
            self.stdout.write(f"  terapeuta: login '{u}' / senha 'allos123'")

        # --- Pacientes ---
        self._paciente("Mariana Souza", ana, True, Decimal("200"),
                       dia=2, hora=time(14, 0), cpf="11144477735")
        self._paciente("João Pereira", ana, True, Decimal("200"),
                       dia=2, hora=time(15, 0), cpf="22255588846")
        self._paciente("Pedro Lima", carla, True, Decimal("180"),
                       dia=0, hora=time(13, 0), cpf=None)  # sem CPF -> flag fiscal
        # Aguardando encaminhamento = ativo sem terapeuta.
        self._paciente("Lucia Fernandes", None, True, Decimal("200"),
                       dia=None, hora=None, cpf="33366699957")
        # Inativo (não conta capacidade).
        self._paciente("Rafael Gomes", None, False, Decimal("0"),
                       dia=None, hora=None, cpf=None)

        self.stdout.write(self.style.SUCCESS("Seed concluído."))

    # ------------------------------------------------------------------ helpers
    def _tag(self, nome, horas, descricao):
        tag, _ = Tag.objects.get_or_create(nome=nome)
        tag.horas_consumidas = horas
        tag.descricao = descricao
        tag.save()
        return tag

    def _user(self, username, is_staff=False, is_superuser=False,
              first="", last=""):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": is_staff, "is_superuser": is_superuser,
                      "first_name": first, "last_name": last},
        )
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(SENHA_PADRAO)
        user.save()
        return user

    def _terapeuta(self, username, nome, abordagem, pacientes_max,
                   tags_atuais, tags_apto, horarios, supervisor=None):
        user = self._user(username, is_staff=False,
                          first=nome.split()[0], last=nome.split()[-1])
        assoc, _ = Associado.objects.get_or_create(
            usuario=user,
            defaults={"nome": nome, "telefone": "31988550000",
                      "email": f"{username}@exemplo.com"},
        )
        ter, _ = Terapeuta.objects.get_or_create(
            fk_associado=assoc,
            defaults={"fk_abordagem": abordagem, "pacientes_max": pacientes_max},
        )
        ter.fk_abordagem = abordagem
        ter.pacientes_max = pacientes_max
        ter.fk_supervisor = supervisor
        ter.save()
        ter.tags.set(tags_atuais)
        ter.tags_apto.set(tags_apto)
        # Recria o calendário do zero para o total bater exatamente (idempotente).
        ter.horarios.all().delete()
        for dia, ini, fim, tag in horarios:
            HorarioDisponivel.objects.create(
                fk_terapeuta=ter, dia_semana=dia, hora_inicio=ini,
                hora_fim=fim, fk_tag=tag,
            )
        return ter

    def _paciente(self, nome, terapeuta, is_active, vlr, dia, hora, cpf):
        Paciente.objects.update_or_create(
            nome=nome,
            defaults={
                "fk_terapeuta": terapeuta,
                "telefone": "31977770000",
                "vlr_sessao": vlr,
                "is_active": is_active,
                "dia_semana_padrao": dia,
                "hora_padrao": hora,
                "cpf": cpf,
            },
        )
