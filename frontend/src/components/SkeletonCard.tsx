export default function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-900 rounded-3xl p-6 shadow-sm animate-pulse">
      {/* 1. Header Skeleton */}
      <div className="flex justify-between items-center mb-4">
        <div className="w-32 h-3 bg-zinc-100 dark:bg-zinc-900 rounded"></div>
        <div className="w-20 h-5 bg-zinc-100 dark:bg-zinc-900 rounded-md"></div>
      </div>

      <div className="flex gap-6 items-center">
        {/* 2. Visual Anchor Skeleton */}
        <div className="w-20 h-20 rounded-2xl bg-zinc-50 dark:bg-zinc-900 flex-none shadow-inner"></div>

        <div className="flex-1 space-y-3">
          {/* 4. Crop Name Skeleton */}
          <div className="w-24 h-6 bg-zinc-100 dark:bg-zinc-900 rounded"></div>
          
          {/* 5. Decision Skeleton */}
          <div className="w-32 h-8 bg-zinc-200 dark:bg-zinc-800 rounded"></div>
        </div>
      </div>

      {/* 6. Insight Skeleton */}
      <div className="mt-6 w-3/4 h-4 bg-zinc-100 dark:bg-zinc-900 rounded"></div>

      {/* 7. Timing Skeleton */}
      <div className="mt-3 w-1/2 h-3 bg-zinc-100 dark:bg-zinc-900 rounded"></div>

      {/* 8. Tags Skeleton */}
      <div className="mt-6 flex gap-2">
        <div className="w-16 h-5 bg-zinc-50 dark:bg-zinc-900 rounded-full"></div>
        <div className="w-20 h-5 bg-zinc-50 dark:bg-zinc-900 rounded-full"></div>
      </div>

      {/* 9. Footer Skeleton */}
      <div className="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-900 flex justify-between items-center">
        <div className="w-24 h-3 bg-zinc-50 dark:bg-zinc-900 rounded"></div>
        <div className="w-24 h-8 bg-zinc-100 dark:bg-zinc-900 rounded-xl"></div>
      </div>
    </div>
  );
}
