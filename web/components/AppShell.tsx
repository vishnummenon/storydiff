import Link from "next/link";

const navLink =
  "rounded-md px-3 py-2 text-sm font-medium text-fg-muted transition-colors hover:bg-surface-2 hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-surface-0">
      <header className="border-b border-border bg-surface-1">
        <div className="mx-auto flex h-14 max-w-content items-center justify-between gap-4 px-4 sm:px-6">
          <Link
            href="/"
            className="text-lg font-semibold tracking-tight text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            StoryDiff
          </Link>
          <nav className="flex items-center gap-1" aria-label="Primary">
            <Link className={navLink} href="/">
              Feed
            </Link>
            <Link className={navLink} href="/media">
              Media
            </Link>
            <Link className={navLink} href="/search">
              Search
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-content flex-1 px-4 py-8 sm:px-6">
        {children}
      </main>
      <footer className="border-t border-border py-6 text-center text-xs text-fg-muted">
        Read-only view of consensus and coverage — data from StoryDiff API
      </footer>
    </div>
  );
}
