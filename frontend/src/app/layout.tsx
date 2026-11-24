import type { Metadata } from "next";
import type { ReactNode } from "react";
import { cookies } from "next/headers";

import { AppShell } from "@/components/layout/app-shell";
import { ownerCookie } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: "PROXI",
  description: "Personal AI Security & Authority Infrastructure",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const prefs = await cookies();
  return (
    <html lang="en" data-theme={prefs.get("proxi-theme")?.value === "light" ? "light" : "dark"}>
      <body className="min-h-screen font-sans antialiased">
        <AppShell signedIn={prefs.has(ownerCookie)}>{children}</AppShell>
      </body>
    </html>
  );
}
