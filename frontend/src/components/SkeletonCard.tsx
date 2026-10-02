export default function SkeletonCard() {
  return (
    <div className="elite-card rounded-3xl p-7 sm:p-8">
      <div className="mb-7 flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="skeleton h-14 w-14 rounded-2xl" />
          <div className="space-y-2">
            <div className="skeleton h-2.5 w-24 rounded" />
            <div className="skeleton h-6 w-28 rounded" />
          </div>
        </div>
        <div className="skeleton h-10 w-10 rounded-xl" />
      </div>

      <div className="space-y-3 border-b border-border pb-7">
        <div className="skeleton h-11 w-40 rounded" />
        <div className="skeleton h-3.5 w-52 rounded" />
      </div>

      <div className="flex gap-6 pt-5">
        <div className="skeleton h-3 w-20 rounded" />
        <div className="skeleton h-3 w-24 rounded" />
      </div>
    </div>
  );
}
