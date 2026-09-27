import React from 'react';

interface AuraBrandMarkProps {
  className?: string;
}

export const AuraBrandMark: React.FC<AuraBrandMarkProps> = ({ className = '' }) => (
  <span className={`aura-mark ${className}`} aria-hidden="true">
    <svg viewBox="0 0 32 32" fill="none">
      <path d="M16 4.5 19.1 12.9 27.5 16l-8.4 3.1L16 27.5l-3.1-8.4L4.5 16l8.4-3.1L16 4.5Z" fill="currentColor" />
      <circle cx="24.5" cy="7.5" r="2" fill="currentColor" opacity=".65" />
    </svg>
  </span>
);
