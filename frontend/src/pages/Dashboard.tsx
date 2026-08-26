import { useEffect, useState } from "react";

import { getHealth } from "../api/client";

type BackendStatus = "checking" | "online" | "offline";

export default function Dashboard() {
  const [status, setStatus] = useState<BackendStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then(() => {
        if (!cancelled) setStatus("online");
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
      <p className="mt-2 text-slate-600">
        This is a placeholder. Overview widgets (recent resumes, recent job
        descriptions, recent analyses) will be added in a later sprint.
      </p>

      <div className="mt-6 inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
        <span
          className={[
            "h-2 w-2 rounded-full",
            status === "online"
              ? "bg-green-500"
              : status === "offline"
                ? "bg-red-500"
                : "bg-yellow-500",
          ].join(" ")}
        />
        <span className="text-slate-700">
          Backend API:{" "}
          {status === "checking"
            ? "checking..."
            : status === "online"
              ? "connected"
              : "unreachable"}
        </span>
      </div>
    </section>
  );
}
