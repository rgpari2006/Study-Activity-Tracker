interface ActivityBadgeProps {
  activities: string[];
}

const LABEL_MAP: Record<string, string> = {
  sitting: "Sitting",
  standing: "Standing",
  away: "Away",
  laptop: "Laptop",
  "book/paper": "Book / Paper",
  "phone in hand": "Phone in Hand",
  undefined: "Undefined",
};

export default function ActivityBadge({ activities }: ActivityBadgeProps) {
  if (!activities || activities.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <span className="text-xs uppercase tracking-wider text-gray-400 font-medium">
        Current Detected Activities
      </span>
      <div className="flex items-center justify-center gap-2 flex-wrap">
        {activities.map((act) => {
          const formatted =
            LABEL_MAP[act.toLowerCase()] ||
            act.charAt(0).toUpperCase() + act.slice(1);

          return (
            <span
              key={act}
              className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-medium bg-gray-800 text-gray-200 border border-gray-700 shadow-sm"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 mr-2" />
              {formatted}
            </span>
          );
        })}
      </div>
    </div>
  );
}
