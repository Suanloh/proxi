import type { ReactNode } from "react";

export function PageHeading({title, description, controls}: {title: string; description?: string; controls?: ReactNode}) {
  return <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
    <div><p className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[.22em] text-primary">Control plane</p><h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>{description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}</div>
    {controls}
  </header>;
}
