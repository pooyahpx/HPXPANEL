import { useEffect, useState } from 'react'
import { numberWithCommas } from '@/utils/formatByte'

interface CountUpProps {
  end: number
  duration?: number
}

export const CountUp = ({ end, duration = 800 }: CountUpProps) => {
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (!end && end !== 0) {
      setCount(0)
      return
    }

    let startTimestamp: number | null = null
    const startValue = count
    let animationFrameId: number | null = null

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp
      const progress = Math.min((timestamp - startTimestamp) / duration, 1)
      // Using easeOutQuad for a softer animation
      const eased = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2
      const currentCount = Math.floor(eased * (end - startValue) + startValue)

      setCount(currentCount)

      if (progress < 1) {
        animationFrameId = window.requestAnimationFrame(step)
      } else {
        setCount(end)
      }
    }

    animationFrameId = window.requestAnimationFrame(step)

    return () => {
      if (animationFrameId !== null) {
        window.cancelAnimationFrame(animationFrameId)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [end, duration])

  return <>{numberWithCommas(count)}</>
}
