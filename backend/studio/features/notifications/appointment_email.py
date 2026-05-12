from django.contrib.auth.models import User

from studio.models import Appointment, UserProfile


def recipient_emails_for_appointment(appointment: Appointment) -> list[str]:
    """Destinatarios para e-mails transacionais de agendamento (HU19)."""
    emails: set[str] = set()
    ce = (appointment.client.email or "").strip()
    if ce:
        emails.add(ce.lower())
    contact = (appointment.tattooer.contact or "").strip()
    if "@" in contact:
        emails.add(contact.lower())
    for u in User.objects.filter(profile__role=UserProfile.ROLE_STUDIO).only("email"):
        e = (u.email or "").strip()
        if e:
            emails.add(e.lower())
    return sorted(emails)
