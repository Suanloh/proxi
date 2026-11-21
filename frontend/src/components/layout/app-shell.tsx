import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-10 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <header className="border-b border-border bg-card text-card-foreground">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <span className="font-mono text-sm font-semibold tracking-widest">PROXI</span>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-20">
        {children}
      </main>
    </>
  );
}
