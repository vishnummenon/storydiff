export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <div
      className="rounded-lg border border-dashed border-border bg-surface-1 px-6 py-12 text-center"
      role="status"
    >
      <p className="font-medium text-fg">{title}</p>
      {detail ? (
        <p className="mt-2 text-sm text-fg-muted">{detail}</p>
      ) : null}
    </div>
  );
}
