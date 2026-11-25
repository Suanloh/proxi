import Link from "next/link";
import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiMessage } from "@/lib/api";
import { InputError } from "@/lib/validation";

export function Panel({title, children}: {title: string; children: ReactNode}) {
  return <Card className="min-w-0"><CardHeader><CardTitle>{title}</CardTitle></CardHeader><CardContent>{children}</CardContent></Card>;
}

export function Status({value}: {value: string | null}) {
  const label = value ?? "Unknown";
  const color = ["ALLOW", "active", "APPROVED", "enabled", "connected"].includes(label) ? "bg-decision-allow text-decision-allow-foreground" : ["HOLD", "PENDING", "warning", "restricted", "pending_approval"].includes(label) ? "bg-decision-hold text-decision-hold-foreground" : ["BLOCK", "REJECTED", "critical", "revoked", "suspended"].includes(label) ? "bg-decision-block text-decision-block-foreground" : "bg-muted text-foreground";
  return <Badge variant="outline" className={`${color} border-transparent font-mono`}>{label.replaceAll("_", " ")}</Badge>;
}

export function Empty({children = "No records found."}: {children?: ReactNode}) {
  return <p className="rounded-md border border-dashed border-border px-4 py-6 text-sm text-muted-foreground">{children}</p>;
}

export function Fault({error}: {error: unknown}) {
  return <p role="alert" className="rounded-md border border-destructive/40 px-4 py-3 text-sm text-destructive">{error instanceof InputError ? error.message : apiMessage(error)}</p>;
}

export async function Data<T>({load, children}: {load: () => Promise<T>; children: (value: T) => ReactNode}) {
  try { return children(await load()); } catch (error) { return <Fault error={error} />; }
}

export function Records({columns, rows, empty}: {columns: string[]; rows: ReactNode[][]; empty?: string}) {
  if (!rows.length) return <Empty>{empty}</Empty>;
  return <div className="overflow-x-auto rounded-md border border-border" tabIndex={0} role="region" aria-label={`${columns[0]} table`}>
    <table className="w-full text-left text-sm"><thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground"><tr>{columns.map((column) => <th scope="col" key={column} className="px-3 py-2.5 font-medium">{column}</th>)}</tr></thead>
      <tbody className="divide-y divide-border">{rows.map(([key, ...cells]) => <tr key={String(key)} className="align-top hover:bg-muted/30">{cells.map((cell, i) => <td key={columns[i]} className="px-3 py-3">{cell}</td>)}</tr>)}</tbody>
    </table>
  </div>;
}

export function Facts({items}: {items: [string, ReactNode][]}) {
  return <dl className="space-y-2 text-sm">{items.map(([label, value]) => <div key={label} className="grid gap-1 border-b border-border/60 pb-2 sm:grid-cols-[10rem_minmax(0,1fr)]"><dt className="text-muted-foreground">{label}</dt><dd className="wrap-anywhere">{value ?? "—"}</dd></div>)}</dl>;
}
export function Id({value}: {value: string | null}) { return <span className="font-mono text-xs wrap-anywhere">{value ?? "—"}</span>; }
export function AgentLink({id, name}: {id: string; name?: string}) { return <Link className="data-link" href={`/agents/${id}`}>{name ?? <Id value={id} />}</Link>; }
export function Stamp({value}: {value: string | null}) {
  return value ? <time dateTime={value} className="font-mono text-xs whitespace-nowrap">{value.slice(0, 19).replace("T", " ")}{/Z$|[+-]00:00$/.test(value) ? " UTC" : value.slice(19)}</time> : <span className="text-muted-foreground">—</span>;
}
export function Values({values}: {values: string[]}) {
  return values.length ? <ul className="space-y-1">{values.map((value) => <li key={value}><Id value={value} /></li>)}</ul> : <span className="text-muted-foreground">None</span>;
}
