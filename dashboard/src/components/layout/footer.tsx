import { REPO_URL } from '@/constants/Project'
import { FC } from 'react'

const FooterContent = () => {
  return (
    <p className="flex flex-grow items-center justify-center gap-1.5 text-center text-xs text-gray-500">
      <a
        href={REPO_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="dev-by-hpx focus-visible:ring-ring inline-flex items-center gap-1 rounded-sm font-mono text-[11px] font-bold tracking-[0.14em] uppercase focus-visible:ring-2 focus-visible:outline-none"
        aria-label="dev by hpx on GitHub"
      >
        <span className="dev-by-hpx__label">dev by hpx</span>
      </a>
    </p>
  )
}

export const Footer: FC = ({ ...props }) => {
  return (
    <div className="relative flex w-full pt-1 pb-3" {...props}>
      <FooterContent />
    </div>
  )
}
