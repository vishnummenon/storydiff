export function PageHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-8 border-b border-border pb-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight text-fg md:text-4xl">
        {title}
      </h1>
      {description ? (
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-fg-muted">
          {description}
        </p>
      ) : null}
    </div>
  );
}
