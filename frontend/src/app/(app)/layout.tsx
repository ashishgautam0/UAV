"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { cn } from "@/lib/utils";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <main className={cn("transition-all duration-300", collapsed ? "md:ml-16" : "md:ml-60")}>
        <div className="mx-auto max-w-7xl overflow-x-hidden p-4 pt-16 sm:p-6 sm:pt-16 md:pt-6">{children}</div>
      </main>
    </div>
  );
}
