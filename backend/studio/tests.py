from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthAndClientsAPITests(APITestCase):
    def test_register_login_and_manage_clients(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "name": "Teste Studio",
                "email": "studio.teste@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "studio",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        me_response = self.client.get(reverse("me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "studio.teste@inkcontrol.dev")

        create_client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Maria",
                "phone": "54999999999",
                "email": "maria@cliente.com",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_client_response.status_code, status.HTTP_201_CREATED)

        list_clients_response = self.client.get(reverse("client-list"))
        self.assertEqual(list_clients_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_clients_response.data["results"]), 1)

    def test_manage_tattooers_and_appointment_conflict(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "name": "Studio Admin",
                "email": "studio@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "studio",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Agenda",
                "phone": "54988888888",
                "email": "cliente.agenda@inkcontrol.dev",
            },
            format="json",
        )
        self.assertEqual(client_response.status_code, status.HTTP_201_CREATED)

        tattooer_response = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador 1",
                "artistic_style": "Old School",
                "contact": "54977777777",
            },
            format="json",
        )
        self.assertEqual(tattooer_response.status_code, status.HTTP_201_CREATED)

        appointment_payload = {
            "client": client_response.data["id"],
            "tattooer": tattooer_response.data["id"],
            "scheduled_at": "2026-06-10T14:00:00-03:00",
            "description": "Fechamento braco",
            "status": "confirmed",
        }
        first_appointment = self.client.post(
            reverse("appointment-list"),
            appointment_payload,
            format="json",
        )
        self.assertEqual(first_appointment.status_code, status.HTTP_201_CREATED)

        conflicting_appointment = self.client.post(
            reverse("appointment-list"),
            appointment_payload,
            format="json",
        )
        self.assertEqual(conflicting_appointment.status_code, status.HTTP_400_BAD_REQUEST)

    def test_appointment_period_filters_and_status_transition_rules(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "name": "Studio Agenda",
                "email": "agenda@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "studio",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Filtro",
                "phone": "54966666666",
                "email": "cliente.filtro@inkcontrol.dev",
            },
            format="json",
        )
        tattooer_response = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador Filtro",
                "artistic_style": "Fine Line",
                "contact": "54955555555",
            },
            format="json",
        )
        self.assertEqual(client_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(tattooer_response.status_code, status.HTTP_201_CREATED)

        base_payload = {
            "client": client_response.data["id"],
            "tattooer": tattooer_response.data["id"],
            "description": "Sessao teste",
            "status": "requested",
        }
        first_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-06-10T14:00:00-03:00"},
            format="json",
        )
        second_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-06-11T14:00:00-03:00"},
            format="json",
        )
        third_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-07-01T14:00:00-03:00"},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(third_response.status_code, status.HTTP_201_CREATED)

        day_response = self.client.get(reverse("appointment-list"), {"period": "day", "date": "2026-06-10"})
        self.assertEqual(day_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(day_response.data["results"]), 1)

        week_response = self.client.get(reverse("appointment-list"), {"period": "week", "date": "2026-06-10"})
        self.assertEqual(week_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(week_response.data["results"]), 2)

        month_response = self.client.get(reverse("appointment-list"), {"period": "month", "date": "2026-06-10"})
        self.assertEqual(month_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(month_response.data["results"]), 2)

        appointment_id = first_response.data["id"]
        invalid_transition = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appointment_id}),
            {"status": "done"},
            format="json",
        )
        self.assertEqual(invalid_transition.status_code, status.HTTP_400_BAD_REQUEST)

        valid_transition_1 = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appointment_id}),
            {"status": "confirmed"},
            format="json",
        )
        valid_transition_2 = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appointment_id}),
            {"status": "in_progress"},
            format="json",
        )
        valid_transition_3 = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appointment_id}),
            {"status": "done"},
            format="json",
        )
        self.assertEqual(valid_transition_1.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_transition_2.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_transition_3.status_code, status.HTTP_200_OK)

    def test_search_filters_pagination_and_health_form(self):
        register_response = self.client.post(
            reverse("register"),
            {
                "name": "Studio Busca",
                "email": "busca@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "studio",
            },
            format="json",
        )
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_a = self.client.post(
            reverse("client-list"),
            {"name": "Ana Silva", "phone": "5411111111", "email": "ana@dev.com"},
            format="json",
        ).data
        self.client.post(
            reverse("client-list"),
            {"name": "Bruno Lima", "phone": "5422222222", "email": "bruno@dev.com"},
            format="json",
        )

        tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Rafa Traço",
                "artistic_style": "Blackwork",
                "contact": "5433333333",
            },
            format="json",
        ).data

        clients_search = self.client.get(reverse("client-list"), {"q": "Ana"})
        self.assertEqual(clients_search.status_code, status.HTTP_200_OK)
        self.assertEqual(clients_search.data["count"], 1)

        appointment = self.client.post(
            reverse("appointment-list"),
            {
                "client": client_a["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-08-10T14:00:00-03:00",
                "description": "Leao realista",
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(appointment.status_code, status.HTTP_201_CREATED)

        appointments_search = self.client.get(
            reverse("appointment-list"),
            {"q": "Leao", "status": "confirmed"},
        )
        self.assertEqual(appointments_search.status_code, status.HTTP_200_OK)
        self.assertEqual(appointments_search.data["count"], 1)

        health_form_create = self.client.post(
            reverse("health-form-list"),
            {
                "client": client_a["id"],
                "allergies": "Niquel",
                "chronic_diseases": "Nenhuma",
                "healing_history": "Boa cicatrizacao",
                "notes": "Cliente tranquilo",
            },
            format="json",
        )
        self.assertEqual(health_form_create.status_code, status.HTTP_201_CREATED)

        health_form_list = self.client.get(reverse("health-form-list"), {"q": "Niquel"})
        self.assertEqual(health_form_list.status_code, status.HTTP_200_OK)
        self.assertEqual(health_form_list.data["count"], 1)

    def test_role_based_permissions(self):
        studio_token = self.client.post(
            reverse("register"),
            {
                "name": "Studio Perm",
                "email": "studio.perm@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "studio",
            },
            format="json",
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        base_client = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Base",
                "phone": "54944444444",
                "email": "cliente.base@inkcontrol.dev",
            },
            format="json",
        ).data
        base_tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador Base",
                "artistic_style": "Fineline",
                "contact": "54944440000",
            },
            format="json",
        ).data
        self.client.credentials()

        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Perm",
                "email": "cliente.perm@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]

        tattooer_token = self.client.post(
            reverse("register"),
            {
                "name": "Tattooer Perm",
                "email": "tattooer.perm@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "tattooer",
            },
            format="json",
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        denied_client_create_client = self.client.post(
            reverse("client-list"),
            {
                "name": "Nao Pode",
                "phone": "000",
                "email": "naopode@inkcontrol.dev",
            },
            format="json",
        )
        self.assertEqual(denied_client_create_client.status_code, status.HTTP_403_FORBIDDEN)

        allowed_client_create_appointment = self.client.post(
            reverse("appointment-list"),
            {
                "client": base_client["id"],
                "tattooer": base_tattooer["id"],
                "scheduled_at": "2026-10-10T10:00:00-03:00",
                "description": "Cliente pode solicitar",
                "status": "requested",
            },
            format="json",
        )
        self.assertEqual(allowed_client_create_appointment.status_code, status.HTTP_201_CREATED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {tattooer_token}")
        denied_tattooer_delete_client = self.client.delete(
            reverse("client-detail", kwargs={"pk": base_client["id"]})
        )
        self.assertEqual(denied_tattooer_delete_client.status_code, status.HTTP_403_FORBIDDEN)

        allowed_tattooer_list_clients = self.client.get(reverse("client-list"))
        self.assertEqual(allowed_tattooer_list_clients.status_code, status.HTTP_200_OK)
