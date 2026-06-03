import { BadgeCheck, Boxes, Download, ScanSearch } from "lucide-react";

function formatNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}

export default function MetadataPanel({
  metadata,
  beforeUrl,
  afterUrl,
  uploadedFileName,
}) {
  const cards = [
    {
      label: "Component Class",
      value: metadata?.component_class || "Unavailable",
      icon: ScanSearch,
      tone: "text-goldTemple",
    },
    {
      label: "Before Points",
      value: formatNumber(metadata?.before_points),
      icon: Boxes,
      tone: "text-creamTemple",
    },
    {
      label: "After Points",
      value: formatNumber(metadata?.after_points),
      icon: Boxes,
      tone: "text-saffronTemple",
    },
    {
      label: "Confidence",
      value:
        typeof metadata?.confidence === "number"
          ? `${Math.round(metadata.confidence * 100)}%`
          : "N/A",
      icon: BadgeCheck,
      tone: "text-goldTemple",
    },
  ];

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-glow">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-goldTemple/70">
            Reconstruction Metadata
          </p>
          <h3 className="mt-2 font-serifTemple text-3xl text-creamTemple">
            Model intelligence summary
          </h3>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <a
            href={beforeUrl}
            download={uploadedFileName || "original-model"}
            className="inline-flex items-center justify-center gap-2 rounded-full border border-goldTemple/35 bg-goldTemple/10 px-5 py-3 text-sm font-medium text-goldTemple transition hover:bg-goldTemple/20"
          >
            <Download className="h-4 w-4" />
            Download Original
          </a>
          <a
            href={afterUrl}
            download="reconstructed-model"
            className="inline-flex items-center justify-center gap-2 rounded-full border border-saffronTemple/35 bg-saffronTemple/10 px-5 py-3 text-sm font-medium text-saffronTemple transition hover:bg-saffronTemple/20"
          >
            <Download className="h-4 w-4" />
            Download Reconstructed
          </a>
        </div>
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon, tone }) => (
          <div
            key={label}
            className="rounded-[1.5rem] border border-white/10 bg-nightTemple/70 p-5"
          >
            <div className={`flex items-center gap-3 ${tone}`}>
              <Icon className="h-5 w-5" />
              <p className="text-xs uppercase tracking-[0.25em] text-creamTemple/55">
                {label}
              </p>
            </div>
            <p className="mt-4 text-xl font-semibold text-creamTemple">
              {value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
