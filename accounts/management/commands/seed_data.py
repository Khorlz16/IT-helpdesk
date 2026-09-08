from django.core.management.base import BaseCommand
from requests.models import Category
from accounts.models import Branch, User

class Command(BaseCommand):
    help = 'Seed branches, categories, and central admin'

    def handle(self, *args, **options):
        categories = [
            'Hardware & Equipment', 'Network & Connectivity',
            'Software & Applications', 'Account & Access',
            'Email & Communication', 'Other'
        ]
        for name in categories:
            Category.objects.get_or_create(name=name)

        branch_data = [
            ('Ikeja', 'IKE'),
            ('LASU Gate', 'LSG'),
            ('Ikorodu', 'IKD'),
        ]
        for name, code in branch_data:
            Branch.objects.get_or_create(name=name, code=code)

        admin_pzc = 'PZC0001CTR'
        admin_password = 'king1000'   # <-- change this!
        ikeja = Branch.objects.get(code='IKE')

        admin, created = User.objects.get_or_create(pzc=admin_pzc, defaults={
            'username': 'Central_Admin',
            'role': User.Role.IT_ADMIN,
            'is_central_admin': True,
            'branch': ikeja,
            'is_staff': True,
            'is_superuser': True,
        })
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created central admin {admin_pzc}'))
        else:
            admin.is_central_admin = True
            admin.is_staff = True
            admin.is_superuser = True
            admin.branch = ikeja
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Updated central admin {admin_pzc}'))

        self.stdout.write(self.style.SUCCESS('Seeding completed'))
