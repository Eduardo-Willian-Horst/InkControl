import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { ROLES } from './lib/constants'
import { AppointmentFormPage } from './pages/AppointmentFormPage'
import { AppointmentsPage } from './pages/AppointmentsPage'
import { ClientFormPage } from './pages/ClientFormPage'
import { ClientsPage } from './pages/ClientsPage'
import { HealthFormFormPage } from './pages/HealthFormFormPage'
import { HealthFormsPage } from './pages/HealthFormsPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { TattooerFormPage } from './pages/TattooerFormPage'
import { TattooerProfilePage } from './pages/TattooerProfilePage'
import { TattooersPage } from './pages/TattooersPage'
import { StudioSettingsPage } from './pages/StudioSettingsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { ProtectedRoute } from './routes/ProtectedRoute'
import { RoleGuard } from './routes/RoleGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<LoginPage />} />
      <Route path="/cadastro" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/tatuadores" replace />} />
        <Route
          path="clientes"
          element={
            <RoleGuard roles={[ROLES.studio, ROLES.tattooer]}>
              <ClientsPage />
            </RoleGuard>
          }
        />
        <Route
          path="clientes/novo"
          element={
            <RoleGuard roles={[ROLES.studio]}>
              <ClientFormPage />
            </RoleGuard>
          }
        />
        <Route
          path="clientes/:id/editar"
          element={
            <RoleGuard roles={[ROLES.studio]}>
              <ClientFormPage />
            </RoleGuard>
          }
        />
        <Route path="tatuadores" element={<TattooersPage />} />
        <Route
          path="tatuadores/novo"
          element={
            <RoleGuard roles={[ROLES.studio]}>
              <TattooerFormPage />
            </RoleGuard>
          }
        />
        <Route
          path="tatuadores/:id/editar"
          element={
            <RoleGuard roles={[ROLES.studio]}>
              <TattooerFormPage />
            </RoleGuard>
          }
        />
        <Route
          path="tatuadores/:tattooerId/agendar"
          element={
            <RoleGuard roles={[ROLES.studio, ROLES.client]}>
              <AppointmentFormPage />
            </RoleGuard>
          }
        />
        <Route path="tatuadores/:id" element={<TattooerProfilePage />} />
        <Route path="agendamentos" element={<AppointmentsPage />} />
        <Route path="agendamentos/:id/editar" element={<AppointmentFormPage />} />
        <Route path="notificacoes" element={<NotificationsPage />} />
        <Route
          path="estudio/horario"
          element={
            <RoleGuard roles={[ROLES.studio]}>
              <StudioSettingsPage />
            </RoleGuard>
          }
        />
        <Route path="fichas-saude" element={<HealthFormsPage />} />
        <Route
          path="fichas-saude/novo"
          element={
            <RoleGuard roles={[ROLES.studio, ROLES.client]}>
              <HealthFormFormPage />
            </RoleGuard>
          }
        />
        <Route path="fichas-saude/:id/editar" element={<HealthFormFormPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/tatuadores" replace />} />
    </Routes>
  )
}
