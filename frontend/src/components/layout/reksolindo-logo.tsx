import Image from "next/image";

interface ReksolindoLogoProps {
  className?: string;
  showText?: boolean;
  size?: number;
  variant?: "light" | "dark";
}

export function ReksolindoLogo({
  className = "",
  showText = true,
  size = 32,
  variant = "light",
}: ReksolindoLogoProps) {
  const isDark = variant === "dark" || className.includes("text-white");

  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className}`}>
      {/* Official Reksolindo Swirl Logo Mark */}
      <div className="relative shrink-0 flex items-center justify-center">
        <Image
          src="/reksolindo-logo.png"
          alt="Reksolindo Logo"
          width={size}
          height={size}
          className="object-contain"
          priority
        />
      </div>

      {showText && (
        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span
              className={`text-base font-bold tracking-tight font-sans ${
                isDark ? "text-white" : "text-foreground"
              }`}
            >
              PRISM
            </span>
            <span
              className={`rounded px-1.5 py-0.2 text-[9px] font-extrabold uppercase tracking-wider ${
                isDark
                  ? "bg-blue-500/20 text-blue-300 ring-1 ring-blue-400/30"
                  : "bg-blue-50 text-blue-700 ring-1 ring-blue-700/10"
              }`}
            >
              Document Assurance
            </span>
          </div>
          <span
            className={`text-[9px] font-medium tracking-tight -mt-0.5 ${
              isDark ? "text-border" : "text-muted-foreground"
            }`}
          >
            Document Assurance Platform
          </span>
        </div>
      )}
    </div>
  );
}
