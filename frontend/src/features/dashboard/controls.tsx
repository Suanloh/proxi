"use client";

import { useRouter } from "next/navigation";
import { startTransition, useActionState, useEffect, useState, type ComponentProps, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { operate, signIn, type Operation } from "./actions";

export function OperationForm({operation, id = "", secondary = "", label, children, confirmation}: {operation: Operation; id?: string; secondary?: string; label: string; children?: ReactNode; confirmation?: string}) {
  const [result, submit, pending] = useActionState(operate.bind(null, operation, id, secondary), null);
  const [ready, setReady] = useState(false);
  useEffect(() => { setReady(true); }, []);
  const needsConfirmation = Boolean(confirmation);
  return <form action={needsConfirmation ? undefined : submit} className="space-y-3" onSubmit={(event) => {
    event.preventDefault();
    if (pending || (confirmation && (!ready || !window.confirm(confirmation)))) return;
    const data = new FormData(event.currentTarget);
    startTransition(() => submit(data));
  }}>
    {children}
    <Button type="submit" size="sm" variant={needsConfirmation ? "outline" : "default"} disabled={pending || (needsConfirmation && !ready)}>{pending ? "Saving…" : label}</Button>
    {needsConfirmation && <noscript>Enable JavaScript to confirm this operation.</noscript>}
    {result && <p role={result.ok ? "status" : "alert"} className={result.ok ? "text-sm text-muted-foreground" : "text-sm text-destructive"}>{result.message}</p>}
  </form>;
}

export function SignInForm() {
  const [result, submit, pending] = useActionState(signIn, null);
  return <form action={submit} className="space-y-4">
    <label className="field">Owner bearer token<Input type="password" name="token" required maxLength={2048} autoComplete="off" spellCheck={false} /></label>
    <Button disabled={pending}>{pending ? "Verifying…" : "Sign in"}</Button>
    {result && <p role="alert" className="text-sm text-destructive">{result.message}</p>}
  </form>;
}

export function Refresh({auto = false}: {auto?: boolean}) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(auto);
  useEffect(() => {
    if (!enabled) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") router.refresh();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [enabled, router]);
  return <div className="flex flex-wrap items-center gap-3">
    {auto && <label className="flex items-center gap-2 text-xs text-muted-foreground"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} /> Refresh every 15 s</label>}
    <Button variant="outline" size="sm" onClick={() => router.refresh()}>Refresh now</Button>
  </div>;
}

export function ThemeSettings() {
  const [theme, setTheme] = useState("dark");
  useEffect(() => { setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark"); }, []);
  const change = (next: string) => {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    document.cookie = `proxi-theme=${next}; Path=/; Max-Age=31536000; SameSite=Strict${location.protocol === "https:" ? "; Secure" : ""}`;
  };
  return <fieldset className="flex flex-wrap gap-4 text-sm"><legend className="mb-2 font-medium">Color theme</legend>
    {["dark", "light"].map((choice) => <label key={choice} className="flex items-center gap-2 capitalize"><input type="radio" name="theme" checked={theme === choice} onChange={() => change(choice)} /> {choice}</label>)}
  </fieldset>;
}

export function Select(props: ComponentProps<"select">) { return <select {...props} className="control" />; }
export function Textarea(props: ComponentProps<"textarea">) { return <textarea {...props} className="control min-h-20 py-2 font-mono" />; }
