type BrandLogoProps = {
  className?: string;
  compact?: boolean;
  showSubtitle?: boolean;
};

export function BrandLogo({ className = "", compact = false }: BrandLogoProps) {
  const markSize = compact ? 34 : 46;

  return (
    <div
      aria-label="Praxis für Logopädie Şimşek"
      className={`inline-flex shrink-0 items-center ${className}`}
      role="img"
    >
      <svg
        width={markSize}
        height={markSize}
        viewBox="0 0 46 46"
        aria-hidden="true"
        className="shrink-0"
      >
        <rect width="46" height="46" rx="10" fill="#2a7f6f" />
        <path
          d="M12 20.7c0-5 4.2-9 9.6-9 5.3 0 9.6 4 9.6 9s-4.3 9-9.6 9h-3.2l-5 3.6 1.2-5.2A8.5 8.5 0 0 1 12 20.7Z"
          fill="#ffffff"
        />
        <path
          d="M21.6 16.9a3 3 0 1 1 0 6 3 3 0 0 1 0-6Zm-5.3 9c1-2.3 2.9-3.4 5.3-3.4 2.5 0 4.4 1.1 5.4 3.4"
          fill="none"
          stroke="#2a7f6f"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.2"
        />
        <path
          d="M31.5 15.5h3.3c1.5 0 2.7 1.2 2.7 2.7v11.1c0 1.5-1.2 2.7-2.7 2.7h-7.1M31.6 21h3.1M30.4 26h4.3"
          fill="none"
          stroke="#d08a63"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2.3"
        />
      </svg>
    </div>
  );
}
