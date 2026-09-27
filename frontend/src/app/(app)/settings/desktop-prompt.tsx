"use client";

import { useEffect, useState } from "react";
import { getDesktopPrompt, updateApplicationPromptSettings } from "@/lib/api";
import type { DesktopPromptResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export function DesktopPrompt() {
  const [text, setText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [generated, setGenerated] = useState<DesktopPromptResponse | null>(null);

  useEffect(() => {
    getDesktopPrompt()
      .then((data) => { setText(data.template); setGenerated(data); })
      .catch(() => setLoadError(true))
      .finally(() => setBusy(false));
  }, []);

  async function run(save: boolean) {
    setBusy(true);
    try {
      if (save) {
        if (!text.trim()) throw new Error("Enter a prompt before saving.");
        await updateApplicationPromptSettings({ desktop_prompt_template: text });
        setDirty(false);
        toast.success("Desktop prompt saved for every device.");
      }
      const data = await getDesktopPrompt();
      setText(data.template);
      setGenerated(data);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Desktop prompt could not be generated");
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    const prompt = generated?.content;
    if (!prompt) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(prompt);
      toast.success("Desktop prompt copied — paste it into Claude Desktop");
    } catch {
      const fallback = document.createElement("textarea");
      fallback.value = prompt;
      fallback.style.position = "fixed";
      fallback.style.opacity = "0";
      document.body.appendChild(fallback);
      fallback.select();
      try {
        if (document.execCommand("copy")) toast.success("Desktop prompt copied — paste it into Claude Desktop");
        else toast.error("Open the preview to select and copy the prompt.");
      } catch { toast.error("Open the preview to select and copy the prompt."); }
      finally { fallback.remove(); }
    }
  }

  return <Card>
    <CardHeader>
      <CardTitle>Claude Desktop job search prompt</CardTitle>
      <p className="text-sm text-muted-foreground">
        Paste into Claude Desktop (Cowork) to browse LinkedIn, Naukri, Instahyre, Cutshort, and Wellfound using Computer Use. It skips jobs already in your database, applies to matching entry-level AI/ML roles, and records each one in your tracker.
      </p>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="rounded-lg border p-3">
        <div role="toolbar" aria-label="Desktop prompt actions" className="mb-3 flex flex-wrap gap-2">
          <Button disabled={busy || loadError} onClick={() => run(true)}>{busy ? "Working…" : "Save prompt"}</Button>
          <Button variant="outline" disabled={busy || dirty || loadError} onClick={() => run(false)}>Generate prompt</Button>
          <Button variant="outline" disabled={busy || dirty || !generated?.content} onClick={copy}>Copy prompt</Button>
        </div>
        <label htmlFor="prompt-desktop" className="text-sm font-medium">Editable desktop prompt</label>
        <Textarea id="prompt-desktop" value={text} rows={16} maxLength={40000} disabled={busy || loadError}
          onChange={(e) => { setText(e.target.value); setDirty(true); }} />
      </div>
      <p className="text-xs text-muted-foreground">
        Log into all five portals in your browser before starting. Generate resolves the live tracker API and resume links; the agent applies to at most 10 jobs per portal and has no overall time limit. Placeholders: {"{{seen_urls_url}}"}, {"{{record_url}}"}, {"{{resume_url}}"}, {"{{resume_filename}}"}, {"{{resume_sha256}}"}, {"{{dedup_window_days}}"}.
      </p>
      {loadError && <p role="alert" className="text-sm text-destructive">Could not load the desktop prompt. Check that the backend is running.</p>}
      {dirty && <p role="status" className="text-sm text-amber-600">Unsaved changes — save before copying.</p>}
      {generated && <>
        {generated.issues.length > 0 && <ul role="alert" className="list-disc pl-5 text-sm">{generated.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>}
        {!generated.customized && <p className="text-xs text-muted-foreground">Showing the shipped default. Saving stores your own copy.</p>}
        <details><summary className="cursor-pointer text-sm">Generated prompt preview{dirty ? " (previous version)" : ""}</summary>
          <Textarea readOnly value={generated.content} rows={16} aria-label="Generated desktop prompt" />
        </details>
      </>}
    </CardContent>
  </Card>;
}
