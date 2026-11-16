import { useState, useEffect } from 'react'
import './App.css'
import {
  loginUser,
  registerUser,
  logoutUser,
  getCurrentUser,
  clearStoredAuth,
  getStoredAuth,
  changePassword,
} from './services/api'
import ToastNotification from './components/ToastNotification'
import AuthCard from './components/AuthCard'
import ProfileView from './components/ProfileView'

const MIN_PASSWORD_LENGTH = 8

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredAuth())
  const [activeTab, setActiveTab] = useState('login') // 'login' | 'register'
  const [toastNotice, setToastNotice] = useState('')
  const [authError, setAuthError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Estados para cambio de contraseña desde perfil
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false)
  const [currentPasswordInput, setCurrentPasswordInput] = useState('')
  const [newPasswordInput, setNewPasswordInput] = useState('')
  const [confirmNewPasswordInput, setConfirmNewPasswordInput] = useState('')
  const [passwordChangeStatus, setPasswordChangeStatus] = useState({
    error: '',
    success: '',
    loading: false,
  })

  // Form states - Login
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  // Form states - Registro
  const [registerUsername, setRegisterUsername] = useState('')
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerConfirmPassword, setRegisterConfirmPassword] = useState('')
  const [agreeTerms, setAgreeTerms] = useState(false)

  // Validar sesión activa al cargar la app
  useEffect(() => {
    if (currentUser?.token) {
      getCurrentUser()
        .then((userData) => {
          setCurrentUser((prev) => ({ ...prev, ...userData }))
        })
        .catch(() => {
          // Token expirado o revocado
          setCurrentUser(null)
          clearStoredAuth()
        })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Limpieza de inputs
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

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setAuthError('')

    try {
      const data = await loginUser(loginEmail.trim(), loginPassword, rememberMe)
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Bienvenido de vuelta, ${data.nombre || data.username}!`)
    } catch (err) {
      setAuthError(err.message || 'Error en las credenciales.')
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
      showToast('Sesión cerrada de forma segura.')
    }
  }

  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
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

    // Si el usuario no ingresó un username explícito, derivar del correo
    const derivedUsername = (
      registerUsername.trim() ||
      registerEmail.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '') ||
      'usuario'
    )

    // Separar nombre y apellido si se ingresó
    const partesNombre = registerName.trim().split(/\s+/)
    const firstName = partesNombre[0] || ''
    const lastName = partesNombre.slice(1).join(' ') || ''

    try {
      const data = await registerUser(
        {
          username: derivedUsername,
          email: registerEmail.trim(),
          password: registerPassword,
          first_name: firstName,
          last_name: lastName,
        },
        rememberMe
      )
      resetFormInputs()
      setCurrentUser(data)
      showToast(`¡Cuenta creada con éxito! Bienvenido a CineRoll, ${data.nombre || data.username}.`)
    } catch (err) {
      setAuthError(err.message || 'Error al crear la cuenta.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleChangePasswordSubmit = async (e) => {
    e.preventDefault()
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
      const res = await changePassword(currentPasswordInput, newPasswordInput)
      setPasswordChangeStatus({
        error: '',
        success: res.mensaje || 'Contraseña actualizada exitosamente.',
        loading: false,
      })
      setCurrentPasswordInput('')
      setNewPasswordInput('')
      setConfirmNewPasswordInput('')
      showToast('Contraseña actualizada con éxito.')
      setTimeout(() => setShowChangePasswordModal(false), 2000)
    } catch (err) {
      setPasswordChangeStatus({
        error: err.message || 'Error al actualizar la contraseña.',
        success: '',
        loading: false,
      })
    }
  }

  return (
    <>
      <ToastNotification message={toastNotice} />

      {currentUser ? (
        <ProfileView
          currentUser={currentUser}
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
          onLogout={handleLogout}
          isLoading={isLoading}
        />
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
      )}
    </>
  )
}
