interface ActiveAppBadgeProps {
  activeApp: { name: string; title: string } | null;
}

export default function ActiveAppBadge({ activeApp }: ActiveAppBadgeProps) {
  if (!activeApp) {
    return (
      <div className="flex flex-col items-center gap-1.5 p-3 rounded-lg bg-gray-800/60 border border-gray-700/60 max-w-lg mx-auto w-full text-center">
        <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
          Active Window
        </span>
        <span className="text-sm text-gray-400 font-mono italic">
          None / Desktop
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-1.5 p-3.5 rounded-lg bg-gray-800/80 border border-gray-700 max-w-lg mx-auto w-full shadow-sm text-center">
      <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
        Active Window
      </span>
      <div className="flex items-center gap-2 max-w-full">
        <span className="px-2.5 py-0.5 rounded text-xs font-mono font-semibold bg-gray-700 text-gray-200 border border-gray-600 shrink-0">
          {activeApp.name}
        </span>
        <span
          className="text-sm text-gray-200 truncate font-medium"
          title={activeApp.title}
        >
          {activeApp.title}
        </span>
      </div>
    </div>
  );
}
