"use client";

import { useState } from "react";
import { getRenderedOutreachPrompt, updateApplicationPromptSettings } from "@/lib/api";
import type { RenderedApplicationPrompt } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export function OutreachPrompt({ kind, title, description, initialValue }: {
  kind: "hr_email" | "followup" | "cold_dm"; title: string; description: string; initialValue: string;
}) {
  const [text, setText] = useState(initialValue);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [generated, setGenerated] = useState<RenderedApplicationPrompt | null>(null);
  async function generate(save: boolean) {
    setBusy(true);
    setGenerated(null);
    try {
      if (save) {
        if (!text.trim()) throw new Error("Enter a prompt before saving.");
        const saved = await updateApplicationPromptSettings({ [kind + "_template"]: text });
        setText(saved[`${kind}_template`]);
        setDirty(false);
        toast.success(`${title} saved for every device.`);
      }
      setGenerated(await getRenderedOutreachPrompt(`${window.location.origin}/dashboard`, kind));
    } catch (e) { toast.error(e instanceof Error ? e.message : "Prompt could not be generated"); }
    finally { setBusy(false); }
  }
  return <Card>
    <CardHeader><CardTitle>{title}</CardTitle><p className="text-sm text-muted-foreground">{description}</p></CardHeader>
    <CardContent className="space-y-3">
      <div className="rounded-lg border p-3">
        <div role="toolbar" aria-label={`${title} actions`} className="mb-3 flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => generate(true)}>{busy ? "Working…" : "Save prompt"}</Button>
          <Button variant="outline" disabled={busy || dirty} onClick={() => generate(false)}>Generate prompt</Button>
          <Button variant="outline" disabled={busy || dirty || !generated?.prompt} onClick={async () => {
            if (!generated?.prompt) return;
            try {
              if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
              await navigator.clipboard.writeText(generated.prompt);
              toast.success(`${title} copied`);
            } catch {
              const fallback = document.createElement("textarea");
              fallback.value = generated.prompt;
              fallback.style.position = "fixed";
              fallback.style.opacity = "0";
              document.body.appendChild(fallback);
              fallback.select();
              try {
                if (document.execCommand("copy")) toast.success(`${title} copied`);
                else toast.error("Open the preview to select and copy the prompt.");
              } catch { toast.error("Open the preview to select and copy the prompt."); }
              finally { fallback.remove(); }
            }
          }}>Copy prompt</Button>
        </div>
        <label htmlFor={`prompt-${kind}`} className="text-sm font-medium">Editable {title.toLowerCase()}</label>
        <Textarea id={`prompt-${kind}`} value={text} rows={14} maxLength={12000} disabled={busy}
          onChange={(e) => { setText(e.target.value); setDirty(true); }} />
      </div>
      <p className="text-xs text-muted-foreground">{kind === "cold_dm"
        ? "Generate embeds eligible due Tracker jobs and their saved Cold DM notes in a fixed batch. Generate again to refresh it; recheck each job’s due date before sending. Nothing is sent from Settings."
        : "Only this workflow runs. Generate refreshes the app and PDF links. It checks the live queue or records when executed; it does not send anything from Settings."}</p>
      {dirty && <p role="status" className="text-sm text-amber-600">Unsaved changes — save before copying.</p>}
      {generated && <>
        {generated.issues.length > 0 && <ul role="alert" className="list-disc pl-5 text-sm">{generated.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>}
        {kind === "cold_dm" && <p className="text-xs text-muted-foreground">Fixed batch: {generated.job_count} eligible due job{generated.job_count === 1 ? "" : "s"}. Ineligible or missing-draft jobs are omitted.</p>}
        <details><summary className="cursor-pointer text-sm">Generated prompt preview{dirty ? " (previous version)" : ""}</summary>
          <Textarea readOnly value={generated.prompt} rows={14} aria-label={`Generated ${title.toLowerCase()}`} />
        </details>
      </>}
    </CardContent>
  </Card>;
}
