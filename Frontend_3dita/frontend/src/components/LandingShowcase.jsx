import { motion } from "framer-motion";
import {
  Archive,
  ArrowUpRight,
  Boxes,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

const workflow = [
  {
    step: "01",
    title: "Upload damaged geometry",
    description:
      "Drop `.ply` or `.obj` temple scans into the intake modal and prepare them for AI-assisted interpretation.",
    icon: Archive,
    accent: "text-goldTemple",
  },
  {
    step: "02",
    title: "Reconstruct missing form",
    description:
      "The backend analyzes the fractured structure, infers continuity, and prepares a reconstructed model for visual comparison.",
    icon: Sparkles,
    accent: "text-saffronTemple",
  },
  {
    step: "03",
    title: "Compare in synchronized 3D",
    description:
      "Inspect both states side by side with linked camera movement, metadata, and download-ready outputs.",
    icon: Boxes,
    accent: "text-goldTemple",
  },
];

const metrics = [
  { label: "Supported Formats", value: ".PLY / .OBJ" },
  { label: "Comparison Mode", value: "Synced Split Viewer" },
  { label: "Processing Pattern", value: "Mock + Live API Ready" },
  { label: "Preservation Focus", value: "Cultural Heritage Assets" },
];

const pillars = [
  {
    title: "Architectural reading",
    body: "Designed for broken temple fragments, partial point clouds, and restoration-oriented visual review.",
    icon: ScanSearch,
  },
  {
    title: "Confidence-aware output",
    body: "Metadata panels surface class prediction, point counts, and confidence so interpretation stays transparent.",
    icon: ShieldCheck,
  },
  {
    title: "Research presentation",
    body: "Cinematic visual language makes the interface suitable for demos, labs, and heritage-tech showcases.",
    icon: ArrowUpRight,
  },
];

export default function LandingShowcase({ onBegin }) {
  return (
    <section className="relative border-t border-white/5 px-6 pb-20 sm:px-10 lg:px-16">
      <div className="absolute inset-x-0 top-0 h-48 bg-[radial-gradient(circle_at_top,rgba(184,134,11,0.12),transparent_65%)]" />
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="grid gap-6 rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-glow lg:grid-cols-[1.2fr_0.8fr]"
        >
          <div className="space-y-4">
            <p className="text-sm uppercase tracking-[0.3em] text-goldTemple/80">
              Reconstruction Workflow
            </p>
            <h2 className="max-w-3xl font-serifTemple text-4xl text-creamTemple sm:text-5xl">
              A single-page workspace for damaged temple recovery
            </h2>
            <p className="max-w-2xl text-sm leading-7 text-creamTemple/70 sm:text-base">
              The interface now carries the full story before upload: what the
              system does, how the reconstruction is evaluated, and why the
              split viewer matters for preservation teams and research demos.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {metrics.map((item) => (
              <div
                key={item.label}
                className="rounded-[1.5rem] border border-goldTemple/20 bg-nightTemple/70 p-4"
              >
                <p className="text-xs uppercase tracking-[0.25em] text-creamTemple/50">
                  {item.label}
                </p>
                <p className="mt-3 text-base font-semibold text-creamTemple">
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="rounded-[2rem] border border-white/10 bg-nightTemple/75 p-6 shadow-glow"
          >
            <div className="space-y-6">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-saffronTemple/80">
                  Process Stages
                </p>
                <h3 className="mt-2 font-serifTemple text-3xl text-creamTemple">
                  From fractured scan to reconstructed form
                </h3>
              </div>

              <div className="grid gap-4">
                {workflow.map(({ step, title, description, icon: Icon, accent }) => (
                  <div
                    key={step}
                    className="relative rounded-[1.5rem] border border-white/10 bg-white/5 p-5"
                  >
                    <div className="absolute bottom-0 left-10 top-0 hidden w-px bg-gradient-to-b from-goldTemple/0 via-goldTemple/20 to-goldTemple/0 md:block" />
                    <div className="flex items-start gap-4">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
                        <Icon className={`h-5 w-5 ${accent}`} />
                      </div>
                      <div className="space-y-2">
                        <p className="text-xs uppercase tracking-[0.25em] text-creamTemple/45">
                          Step {step}
                        </p>
                        <h4 className="text-lg font-semibold text-creamTemple">
                          {title}
                        </h4>
                        <p className="text-sm leading-7 text-creamTemple/68">
                          {description}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.75, ease: "easeOut", delay: 0.05 }}
            className="grid gap-6"
          >
            <div className="rounded-[2rem] border border-goldTemple/20 bg-[linear-gradient(180deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))] p-6 shadow-glow">
              <div className="space-y-4">
                <p className="text-sm uppercase tracking-[0.3em] text-goldTemple/80">
                  Preview Narrative
                </p>
                <h3 className="font-serifTemple text-3xl text-creamTemple">
                  A temple-themed system, not just a file uploader
                </h3>
                <p className="text-sm leading-7 text-creamTemple/68">
                  The application is now framed as a heritage reconstruction
                  environment, with contextual sections that prepare the user
                  before they ever open the upload dialog.
                </p>
              </div>

              <div className="mt-6 rounded-[1.75rem] border border-white/10 bg-nightTemple/80 p-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-[1.5rem] border border-goldTemple/20 bg-goldTemple/10 p-4">
                    <p className="text-xs uppercase tracking-[0.25em] text-goldTemple/80">
                      Original State
                    </p>
                    <div className="relative mt-4 h-36 overflow-hidden rounded-[1.25rem] bg-[radial-gradient(circle_at_50%_40%,rgba(184,134,11,0.45),transparent_26%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))]">
                      <div className="absolute inset-x-8 bottom-6 h-10 rounded-full bg-goldTemple/15 blur-xl" />
                      <div className="absolute inset-x-10 bottom-8 top-6 rounded-[40%_40%_18%_18%/42%_42%_12%_12%] border border-goldTemple/25 bg-[linear-gradient(180deg,rgba(255,230,176,0.18),rgba(255,255,255,0.02))]" />
                    </div>
                  </div>
                  <div className="rounded-[1.5rem] border border-saffronTemple/20 bg-saffronTemple/10 p-4">
                    <p className="text-xs uppercase tracking-[0.25em] text-saffronTemple/90">
                      Reconstructed State
                    </p>
                    <div className="relative mt-4 h-36 overflow-hidden rounded-[1.25rem] bg-[radial-gradient(circle_at_50%_35%,rgba(255,107,53,0.5),transparent_26%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01))]">
                      <div className="absolute inset-x-8 bottom-6 h-10 rounded-full bg-saffronTemple/15 blur-xl" />
                      <div className="absolute inset-x-10 bottom-8 top-4 rounded-[38%_38%_16%_16%/38%_38%_10%_10%] border border-saffronTemple/25 bg-[linear-gradient(180deg,rgba(255,214,183,0.22),rgba(255,255,255,0.03))]" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-glow">
              <p className="text-sm uppercase tracking-[0.3em] text-goldTemple/80">
                Why It Matters
              </p>
              <div className="mt-5 grid gap-4">
                {pillars.map(({ title, body, icon: Icon }) => (
                  <div
                    key={title}
                    className="rounded-[1.5rem] border border-white/10 bg-nightTemple/70 p-4"
                  >
                    <div className="flex items-start gap-4">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-goldTemple/20 bg-goldTemple/10 text-goldTemple">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div>
                        <h4 className="text-base font-semibold text-creamTemple">
                          {title}
                        </h4>
                        <p className="mt-2 text-sm leading-7 text-creamTemple/68">
                          {body}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={onBegin}
                className="mt-6 inline-flex items-center rounded-full border border-goldTemple/35 bg-goldTemple/10 px-5 py-3 text-sm font-medium text-goldTemple transition hover:bg-goldTemple/20"
              >
                Open Upload Dialog
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
