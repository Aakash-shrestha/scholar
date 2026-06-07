"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { MessageSquare, BookOpen, Network } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar";

const NAV = [
  { href: "/", label: "Ask", icon: MessageSquare },
  { href: "/papers", label: "Papers", icon: BookOpen },
  { href: "/graph", label: "Graph", icon: Network },
];

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border px-2 py-2">
        <div className="flex items-center group-data-[collapsible=icon]:justify-center">
          <Link href="/" className="group-data-[collapsible=icon]:hidden">
            <Image
              src="/scholar_logo.png"
              width={72}
              height={72}
              alt="Scholar"
              className="shrink-0"
            />
          </Link>
          <SidebarTrigger className="ml-auto text-muted-foreground hover:text-foreground transition-colors group-data-[collapsible=icon]:ml-0" />
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2 py-2">
        <SidebarMenu>
          {NAV.map(({ href, label, icon: Icon }) => (
            <SidebarMenuItem key={href}>
              <SidebarMenuButton
                render={<Link href={href} />}
                isActive={pathname === href}
                tooltip={label}
                className={cn(
                  "gap-3 text-sm font-medium transition-colors duration-150",
                  pathname === href
                    ? "text-sidebar-accent-foreground"
                    : "text-muted-foreground"
                )}
              >
                <Icon className="size-4.5 shrink-0" />
                <span>{label}</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
    </Sidebar>
  );
}
