"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  ["/", "Overview", "01"], ["/agents", "Agents", "02"], ["/policies", "Policies", "03"],
  ["/approvals", "Approval centre", "04"], ["/monitor", "Security monitor", "05"],
  ["/trust", "Trust & risk", "06"], ["/audit", "Audit logs", "07"],
  ["/integrations", "Integrations", "08"], ["/settings", "Settings", "09"],
];

export function Navigation() {
  const pathname = usePathname();
  return <nav aria-label="Control plane" className="grid grid-cols-2 gap-1 sm:grid-cols-3 lg:grid-cols-1">
    {links.map(([href, label, number]) => {
      const active = pathname === href || (href !== "/" && pathname.startsWith(`${href}/`));
      return <Link key={href} href={href} aria-current={active ? "page" : undefined} className={`flex items-center gap-2 rounded-md border px-2.5 py-2 text-sm ${active ? "border-primary/30 bg-accent font-medium text-accent-foreground" : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"}`}><span aria-hidden className="font-mono text-[10px] opacity-70">{number}</span>{label}</Link>;
    })}
  </nav>;
}
