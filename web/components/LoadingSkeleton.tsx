export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-36 animate-pulse rounded-lg bg-surface-2"
          aria-hidden
        />
      ))}
    </div>
  );
}

export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="h-10 animate-pulse bg-surface-2" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse border-t border-border bg-surface-1" />
      ))}
    </div>
  );
}
