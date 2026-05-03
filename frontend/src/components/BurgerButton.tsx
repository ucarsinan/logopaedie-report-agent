type BurgerButtonProps = {
  isOpen: boolean;
  onClick: () => void;
};

export function BurgerButton({ isOpen, onClick }: BurgerButtonProps) {
  return (
    <button
      onClick={onClick}
      aria-label={isOpen ? "Menü schließen" : "Menü öffnen"}
      aria-expanded={isOpen}
      className="md:hidden flex flex-col justify-center items-center w-8 h-8 gap-1.5 rounded-md hover:bg-surface-elevated transition-colors"
    >
      <span
        className={`block h-0.5 w-5 bg-foreground rounded-full transition-transform duration-200 ${
          isOpen ? "translate-y-2 rotate-45" : ""
        }`}
      />
      <span
        className={`block h-0.5 w-5 bg-foreground rounded-full transition-opacity duration-200 ${
          isOpen ? "opacity-0" : ""
        }`}
      />
      <span
        className={`block h-0.5 w-5 bg-foreground rounded-full transition-transform duration-200 ${
          isOpen ? "-translate-y-2 -rotate-45" : ""
        }`}
      />
    </button>
  );
}
