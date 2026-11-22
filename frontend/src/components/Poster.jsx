import { useState } from 'react'
import CinemaIcon from './CinemaIcon'

export default function Poster({ url, eager = false }) {
  const [failedUrl, setFailedUrl] = useState(null)
  return (
    <div className="cinema-poster">
      {url && url !== failedUrl
        ? <img src={url} alt="" loading={eager ? 'eager' : 'lazy'} onError={() => setFailedUrl(url)} />
        : <CinemaIcon name="film" />}
    </div>
  )
}
