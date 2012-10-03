from django.core.management.base import BaseCommand
from tenclouds.imagescale2 import server

from urlannotator.settings import imagescale2


class Command(BaseCommand):
    args = ''
    help = 'Starts the imagescale2 server'

    def handle(self, *args, **options):
        server.main([], conf_module=imagescale2)
