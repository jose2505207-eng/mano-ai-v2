"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, User, Clock, Heart, Settings } from "lucide-react";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/profile", label: "Profile", icon: User },
  { href: "/history", label: "History", icon: Clock },
  { href: "/sponsor-stack", label: "Sponsors", icon: Heart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`hidden md:flex flex-col h-screen sticky top-0 border-r border-mano-border bg-mano-darker transition-all duration-200 z-30 ${
          expanded ? "w-60" : "w-16"
        }`}
        onMouseEnter={() => setExpanded(true)}
        onMouseLeave={() => setExpanded(false)}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-4 h-14 border-b border-mano-border">
          <div className="w-8 h-8 rounded-lg bg-mano-primary flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-sm">M</span>
          </div>
          {expanded && (
            <span className="text-mano-text font-bold text-lg whitespace-nowrap">
              Mano AI
            </span>
          )}
        </div>

        {/* Nav items */}
        <nav className="flex-1 flex flex-col gap-1 p-2 mt-2">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? "bg-mano-primary/15 text-mano-primary"
                    : "text-mano-muted hover:bg-mano-surface hover:text-mano-text"
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {expanded && (
                  <span className="text-sm font-medium whitespace-nowrap">
                    {label}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Version footer */}
        {expanded && (
          <div className="px-4 py-3 border-t border-mano-border">
            <p className="text-xs text-mano-muted">Mano AI v0.1.0</p>
          </div>
        )}
      </aside>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-mano-darker border-t border-mano-border flex items-center justify-around h-16">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center gap-1 px-3 py-1.5 rounded-lg transition-colors ${
                isActive
                  ? "text-mano-primary"
                  : "text-mano-muted"
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium">{label}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
