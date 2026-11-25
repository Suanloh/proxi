import { cookies } from "next/headers";
import { ownerCookie } from "@/lib/api";
import { Refresh, SignInForm } from "@/features/dashboard/controls";
import { Overview } from "@/features/dashboard/overview";
import { Panel } from "@/features/dashboard/shared";
import { PageHeading } from "@/features/dashboard/heading";

export default async function Home() {
  if (!(await cookies()).has(ownerCookie)) return <div className="mx-auto mt-10 max-w-md space-y-5 sm:mt-20">
    <PageHeading title="Owner sign-in" description="Manage your agents, policies, and security decisions." />
    <Panel title="Connect to PROXI"><SignInForm /></Panel>
  </div>;
  return <>
    <PageHeading title="Security overview" description="Agent activity, review queue, and integration status." controls={<Refresh />} />
    <Overview />
  </>;
}
