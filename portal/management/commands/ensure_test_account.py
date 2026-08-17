"""Create the deterministic local test account documented for this prototype."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


EMAIL = "admin@example.com"
PASSWORD = "123456"


class Command(BaseCommand):
    help = "Create or reset the local MedAI test account."

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=EMAIL,
            defaults={"email": EMAIL},
        )
        user.email = EMAIL
        user.set_password(PASSWORD)
        user.save(update_fields=["email", "password"])
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} local test account {EMAIL}."))
