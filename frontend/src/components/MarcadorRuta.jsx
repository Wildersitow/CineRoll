import { useParams } from 'react-router-dom'

export default function MarcadorRuta({ titulo, descripcion }) {
  const params = useParams()

  return (
    <main style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
      <section className="profile-info-card">
        <h1 style={{ marginTop: 0 }}>{titulo}</h1>
        <p>{descripcion}</p>
        {Object.entries(params).map(([clave, valor]) => (
          <p key={clave} style={{ color: '#94a3b8' }}>
            <strong>{clave}:</strong> {valor}
          </p>
        ))}
      </section>
    </main>
  )
}
