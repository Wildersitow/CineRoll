import { lazy, Suspense, useEffect, useState } from 'react'
import './App.css'
import {
  changePassword,
  clearStoredAuth,
  getCurrentUser,
  getStoredAuth,
  loginUser,
  logoutUser,
  registerUser,
} from './services/api'
import CatalogView from './components/CatalogView'
import AuthCard from './components/AuthCard'
import ToastNotification from './components/ToastNotification'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import MainLayout from './components/MainLayout'
import CinemaState from './components/CinemaState'
import RutaProtegida from './components/RutaProtegida'

const MediaDetailView = lazy(() => import('./components/MediaDetailView'))
const CinemaDirectory = lazy(() => import('./components/CinemaDirectory'))
const ProfileView = lazy(() => import('./components/ProfileView'))
const PublicProfileView = lazy(() => import('./components/PublicProfileView'))

const MIN_PASSWORD_LENGTH = 8

export default function App() {
  const navigate = useNavigate()
  const [currentUser, setCurrentUser] = useState(() => getStoredAuth())
  const [activeTab, setActiveTab] = useState('login')
  const [toastNotice, setToastNotice] = useState('')
  const [authError, setAuthError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false)
  const [currentPasswordInput, setCurrentPasswordInput] = useState('')
  const [newPasswordInput, setNewPasswordInput] = useState('')
  const [confirmNewPasswordInput, setConfirmNewPasswordInput] = useState('')
  const [passwordChangeStatus, setPasswordChangeStatus] = useState({
    error: '',
    success: '',
    loading: false,
  })

  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  const [registerUsername, setRegisterUsername] = useState('')
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)

  useEffect(() => {
    if (currentUser?.token) {
      getCurrentUser()
        .then((userData) => {
          setCurrentUser((previousUser) => ({ ...previousUser, ...userData }))
        })
        .catch(() => {
          setCurrentUser(null)
          clearStoredAuth()
        })
    }
    // The initial stored session is checked once when the app mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const manejarSesionVencida = () => {
      setCurrentUser(null)
      clearStoredAuth()
      setAuthError('Tu sesión venció. Inicia sesión nuevamente.')
      setActiveTab('login')
      navigate('/acceso', { replace: true })
    }

    window.addEventListener('cineroll:session-expired', manejarSesionVencida)
    return () => window.removeEventListener('cineroll:session-expired', manejarSesionVencida)
  }, [navigate])

  const resetFormInputs = () => {
    setLoginEmail('')
    setLoginPassword('')
    setRegisterUsername('')
    setRegisterName('')
    setRegisterEmail('')
    setRegisterPassword('')
    setRegisterConfirmPassword('')
    setAgreeTerms(false)
    setAuthError('')
  }

  const resetPasswordChangeInputs = () => {
    setCurrentPasswordInput('')
    setNewPasswordInput('')
    setConfirmNewPasswordInput('')
    setPasswordChangeStatus({ error: '', success: '', loading: false })
  }

  const switchTab = (tab) => {
    resetFormInputs()
    setActiveTab(tab)
  }

  const showToast = (message, duration = 3500) => {
    setToastNotice(message)
    setTimeout(() => setToastNotice(''), duration)
  }

  const handleLoginSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)
    setAuthError('')

    try {
      const data = await loginUser(loginEmail.trim(), loginPassword, rememberMe)
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Bienvenido de vuelta, ${data.nombre || data.username}!`)
      navigate('/perfil', { replace: true })
    } catch (error) {
      setAuthError(error.message || 'Error en las credenciales.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = async () => {
    setIsLoading(true)
    try {
      await logoutUser()
    } finally {
      resetFormInputs()
      resetPasswordChangeInputs()
      setShowChangePasswordModal(false)
      setActiveTab('login')
      setCurrentUser(null)
      setIsLoading(false)
      navigate('/acceso', { replace: true })
      showToast('Sesión cerrada de forma segura.')
    }
  }

  const handleRegisterSubmit = async (event) => {
    event.preventDefault()
    setIsLoading(true)
    setAuthError('')

    if (registerPassword !== registerConfirmPassword) {
      setAuthError('Las contraseñas no coinciden.')
      setIsLoading(false)
      return
    }

    if (registerPassword.length < MIN_PASSWORD_LENGTH) {
      setAuthError(`La contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`)
      setIsLoading(false)
      return
    }

    if (/^\d+$/.test(registerPassword)) {
      setAuthError('La contraseña no puede ser solo números.')
      setIsLoading(false)
      return
    }

    const emailUsername = registerEmail.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '')
    const derivedUsername = (
      registerUsername.trim() ||
      (/^\d+$/.test(emailUsername) ? `usuario_${emailUsername}` : emailUsername) ||
      'usuario'
    )
    const nameParts = registerName.trim().split(/\s+/)

    try {
      const escala = new FormData(event.currentTarget).get('escala_calificacion')
      const data = await registerUser(
        {
          username: derivedUsername,
          email: registerEmail.trim(),
          password: registerPassword,
          first_name: nameParts[0] || '',
          last_name: nameParts.slice(1).join(' '),
          ...(escala && { escala_calificacion: Number(escala) }),
        },
        rememberMe
      )
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Cuenta creada con éxito! Bienvenido a CineRoll, ${data.nombre || data.username}.`)
      navigate('/perfil', { replace: true })
    } catch (error) {
      setAuthError(error.message || 'Error al crear la cuenta.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePasswordSubmit = async (event) => {
    event.preventDefault()
    setPasswordChangeStatus({ error: '', success: '', loading: true })

    if (newPasswordInput !== confirmNewPasswordInput) {
      setPasswordChangeStatus({
        error: 'La nueva contraseña y su confirmación no coinciden.',
        success: '',
        loading: false,
      })
      return
    }

    if (newPasswordInput.length < MIN_PASSWORD_LENGTH) {
      setPasswordChangeStatus({
        error: `La nueva contraseña debe tener al menos ${MIN_PASSWORD_LENGTH} caracteres.`,
        success: '',
        loading: false,
      })
      return
    }

    try {
      const response = await changePassword(currentPasswordInput, newPasswordInput)
      setPasswordChangeStatus({
        error: '',
        success: response.mensaje || 'Contraseña actualizada exitosamente.',
        loading: false,
      })
      setCurrentPasswordInput('')
      setNewPasswordInput('')
      setConfirmNewPasswordInput('')
      showToast('Contraseña actualizada con éxito.')
      setTimeout(() => setShowChangePasswordModal(false), 2000)
    } catch (error) {
      setPasswordChangeStatus({
        error: error.message || 'Error al actualizar la contraseña.',
        success: '',
        loading: false,
      })
    }
  }

  return (
    <>
      <ToastNotification message={toastNotice} />
      <Routes>
        <Route element={<MainLayout currentUser={currentUser} onLogout={handleLogout} isLoading={isLoading} />}>
          <Route
            index
            element={<CatalogView />}
          />
          <Route
            path="acceso"
            element={
              currentUser ? (
                <Navigate to="/perfil" replace />
              ) : (
                <AuthCard
                  activeTab={activeTab}
                  onSwitchTab={switchTab}
                  authError={authError}
                  isLoading={isLoading}
                  loginEmail={loginEmail}
                  setLoginEmail={setLoginEmail}
                  loginPassword={loginPassword}
                  setLoginPassword={setLoginPassword}
                  rememberMe={rememberMe}
                  setRememberMe={setRememberMe}
                  onLoginSubmit={handleLoginSubmit}
                  registerUsername={registerUsername}
                  setRegisterUsername={setRegisterUsername}
                  registerName={registerName}
                  setRegisterName={setRegisterName}
                  registerEmail={registerEmail}
                  setRegisterEmail={setRegisterEmail}
                  registerPassword={registerPassword}
                  setRegisterPassword={setRegisterPassword}
                  registerConfirmPassword={registerConfirmPassword}
                  setRegisterConfirmPassword={setRegisterConfirmPassword}
                  agreeTerms={agreeTerms}
                  setAgreeTerms={setAgreeTerms}
                  onRegisterSubmit={handleRegisterSubmit}
                />
              )
            }
          />
          <Route
            path="perfil"
            element={
              <RutaProtegida usuario={currentUser}>
                <Suspense fallback={<p className="cinema-page" role="status">Cargando perfil…</p>}>
                  <ProfileView
                    currentUser={currentUser}
                    onProfileSaved={(data) => {
                      setCurrentUser((previous) => previous ? { ...previous, ...data } : previous)
                      showToast('Perfil actualizado.')
                    }}
                    showChangePasswordModal={showChangePasswordModal}
                    setShowChangePasswordModal={setShowChangePasswordModal}
                    currentPasswordInput={currentPasswordInput}
                    setCurrentPasswordInput={setCurrentPasswordInput}
                    newPasswordInput={newPasswordInput}
                    setNewPasswordInput={setNewPasswordInput}
                    confirmNewPasswordInput={confirmNewPasswordInput}
                    setConfirmNewPasswordInput={setConfirmNewPasswordInput}
                    passwordChangeStatus={passwordChangeStatus}
                    onChangePasswordSubmit={handleChangePasswordSubmit}
                    onResetPasswordInputs={resetPasswordChangeInputs}
                  />
                </Suspense>
              </RutaProtegida>
            }
          />
          <Route
            path="media/:id"
            element={<Suspense fallback={<p className="cinema-page" role="status">Cargando ficha…</p>}><MediaDetailView /></Suspense>}
          />
          <Route
            path="cines"
            element={<Suspense fallback={<p className="cinema-page" role="status">Cargando Cines…</p>}><CinemaDirectory /></Suspense>}
          />
          <Route
            path="usuarios/:username"
            element={<Suspense fallback={<p className="cinema-page" role="status">Cargando perfil…</p>}><PublicProfileView currentUser={currentUser} /></Suspense>}
          />
          <Route path="*" element={<CinemaState error={{ status: 404 }} page />} />
        </Route>
      </Routes>
    </>
  )
}
