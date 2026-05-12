from django.contrib import admin

from .models import (
    Appointment,
    AppointmentChangeRequest,
    Client,
    ClientHealthForm,
    InAppNotification,
    StudioBilling,
    StudioSettings,
    Tattooer,
    UserProfile,
)

admin.site.register(Client)
admin.site.register(UserProfile)
admin.site.register(Tattooer)
admin.site.register(Appointment)
admin.site.register(ClientHealthForm)
admin.site.register(StudioSettings)
admin.site.register(StudioBilling)
admin.site.register(AppointmentChangeRequest)
admin.site.register(InAppNotification)
