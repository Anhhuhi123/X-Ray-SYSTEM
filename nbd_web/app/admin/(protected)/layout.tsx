"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  LayoutDashboard, 
  Users, 
  MessageSquare, 
  Search, 
  BarChart3, 
  Activity, 
  LogOut,
  Cpu,
  ShieldAlert
} from "lucide-react";
import { useAtomValue } from "jotai";
import { currentUserAtom } from "@/atoms/user/user-query.atoms";
import { useGlobalLoadingEffect } from "@/hooks/use-global-loading";
import { getBearerToken, redirectToLogin, logout } from "@/lib/auth-utils";

const sidebarLinks = [
  { name: "Overview", href: "/admin", icon: LayoutDashboard },
  { name: "Users", href: "/admin/users", icon: Users },
  { name: "RAG Observability", href: "/admin/rag/observability", icon: Search },
  { name: "RAG Analytics", href: "/admin/rag/analytics", icon: BarChart3 },
];

export default function ProtectedAdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading } = useAtomValue(currentUserAtom);


  const isCheckingAuth = isLoading || !user;

  useGlobalLoadingEffect(isLoading);

  useEffect(() => {
    if (isLoading) return;

    const token = getBearerToken();
    if (!token) {
      redirectToLogin();
      return;
    }

    if (user && !user.is_superuser) {
      router.push("/dashboard");
    }
  }, [user, isLoading, router]);

  if (isCheckingAuth) {
    return null;
  }

  if (!user?.is_superuser) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  return (
    <div className="flex min-h-screen bg-black text-white selection:bg-blue-500/30">
      {/* Sidebar */}
      <aside className="w-64 border-r border-neutral-800 bg-neutral-950 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-neutral-800">
          <ShieldAlert className="w-6 h-6 mr-2 text-blue-500" />
          <span className="font-semibold text-lg tracking-tight">Admin Dashboard</span>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {sidebarLinks.map((link) => (
            <Link 
              key={link.name} 
              href={link.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-neutral-400 hover:text-white hover:bg-neutral-900 transition-colors"
            >
              <link.icon className="w-4 h-4" />
              {link.name}
            </Link>
          ))}
        </nav>

        <div className="p-4 border-t border-neutral-800">
          <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2.5 w-full rounded-md text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-950/30 transition-colors cursor-pointer">
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-neutral-950">
        <div className="flex-1 overflow-y-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
