import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function RoleGuard({ roles, children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/entrar" replace />
  if (!roles.includes(user.role)) return <Navigate to="/" replace />
  return children
}
