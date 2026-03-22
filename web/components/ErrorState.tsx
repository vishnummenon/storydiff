export function ErrorState({
  title,
  code,
  message,
}: {
  title?: string;
  code?: string;
  message: string;
}) {
  return (
    <div
      className="rounded-lg border border-[var(--color-danger-border)] bg-[var(--color-danger-bg)] px-6 py-8 text-center"
      role="alert"
    >
      <p className="font-medium text-[var(--color-danger-text)]">
        {title ?? "Something went wrong"}
      </p>
      {code ? (
        <p className="mt-1 font-mono text-xs text-[var(--color-danger-muted)]">
          {code}
        </p>
      ) : null}
      <p className="mt-2 text-sm text-[var(--color-danger-text)]">{message}</p>
    </div>
  );
}
