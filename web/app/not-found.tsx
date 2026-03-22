import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-16 text-center">
      <p className="font-display text-4xl font-semibold text-fg">404</p>
      <p className="mt-2 text-fg-muted">This page could not be found.</p>
      <Link
        href="/"
        className="mt-6 inline-block text-sm font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Back to feed
      </Link>
    </div>
  );
}
