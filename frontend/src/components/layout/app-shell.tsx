import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { signOut } from "@/features/dashboard/actions";
import { Navigation } from "@/features/dashboard/navigation";

export function AppShell({ children, signedIn }: { children: ReactNode; signedIn: boolean }) {
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:start-4 focus:top-4 focus:z-10 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to content
      </a>
      <header className="border-b border-border bg-card text-card-foreground">
        <div className="mx-auto flex max-w-[100rem] items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3"><span aria-hidden className="grid size-8 place-items-center rounded-md border border-primary/40 bg-accent font-mono font-bold text-primary">P</span><span className="font-mono text-sm font-semibold tracking-[.23em]">PROXI</span><span className="hidden border-l border-border pl-3 text-xs text-muted-foreground sm:inline">Agent security control plane</span></div>
          {signedIn && <form action={signOut}><Button variant="ghost" size="sm">Sign out</Button></form>}
        </div>
      </header>
      <div className={`mx-auto max-w-[100rem] ${signedIn ? "lg:grid lg:grid-cols-[14rem_minmax(0,1fr)]" : ""}`}>
        {signedIn && <aside className="border-b border-border bg-card p-3 lg:min-h-[calc(100vh-3.5rem)] lg:border-r lg:border-b-0 lg:px-4 lg:py-7"><p className="mb-3 px-2 font-mono text-[10px] uppercase tracking-[.2em] text-muted-foreground">Owner workspace</p><Navigation /></aside>}
        <main id="main-content" tabIndex={-1} className="min-w-0 space-y-4 px-4 py-6 sm:px-6 lg:p-8">
          {children}
        </main>
      </div>
    </>
  );
}
