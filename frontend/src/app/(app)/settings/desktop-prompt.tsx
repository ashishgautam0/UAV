"use client";

import { useEffect, useState } from "react";
import { getDesktopPrompt } from "@/lib/api";
import type { DesktopPromptResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export function DesktopPrompt() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [generated, setGenerated] = useState<DesktopPromptResponse | null>(null);

  async function load() {
    setBusy(true);
    try {
      const data = await getDesktopPrompt();
      setText(data.template);
      setGenerated(data);
      setLoadError(false);
    } catch (e) {
      setLoadError(true);
      toast.error(e instanceof Error ? e.message : "Desktop prompt could not be generated");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

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
        Paste into Claude Desktop (Cowork) to browse eleven portals using Computer Use — LinkedIn, Indeed, Naukri, Instahyre, Cutshort, Wellfound, Shine, Glassdoor India, FirstNaukri, Unstop and Apna. On every portal it skips jobs you already applied to or dismissed, applies to matching entry-level AI/ML roles, and records each one in your tracker. This agent is the only thing that finds jobs — nothing scrapes on your behalf.
      </p>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="rounded-lg border p-3">
        <div role="toolbar" aria-label="Desktop prompt actions" className="mb-3 flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => void load()}>{busy ? "Working…" : "Generate prompt"}</Button>
          <Button variant="outline" disabled={busy || !generated?.content} onClick={copy}>Copy prompt</Button>
        </div>
        <label htmlFor="prompt-desktop" className="text-sm font-medium">Desktop prompt</label>
        <Textarea id="prompt-desktop" readOnly value={text} rows={16} />
      </div>
      <p className="text-xs text-muted-foreground">
        Log into all eleven portals in your browser before starting. Generate resolves the live tracker API and resume links. No application cap and no time limit — it keeps applying until you tell it to stop. Placeholders: {"{{seen_urls_url}}"}, {"{{record_url}}"}, {"{{resume_url}}"}, {"{{resume_filename}}"}, {"{{resume_sha256}}"}.
      </p>
      <p className="text-xs text-muted-foreground">
        This prompt ships with the app and is not editable here, so improvements reach the agent on the next Generate. The answers it fills into forms — notice period, compensation, location, education — live in the prompt text itself.
      </p>
      {loadError && <p role="alert" className="text-sm text-destructive">Could not load the desktop prompt. Check that the backend is running.</p>}
      {generated && <>
        {generated.issues.length > 0 && <ul role="alert" className="list-disc pl-5 text-sm">{generated.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>}
        <details><summary className="cursor-pointer text-sm">Generated prompt preview</summary>
          <Textarea readOnly value={generated.content} rows={16} aria-label="Generated desktop prompt" />
        </details>
      </>}
    </CardContent>
  </Card>;
}
