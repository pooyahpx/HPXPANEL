import { Navigate, useSearchParams } from 'react-router'

/** Legacy route — ICMP tunnels live under HPX Pulse. */
export default function HpxTunnelPage() {
  const [searchParams] = useSearchParams()
  const next = new URLSearchParams(searchParams)
  next.set('tab', 'icmp')
  return <Navigate to={`/hpx-pulse?${next.toString()}`} replace />
}
