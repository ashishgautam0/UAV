"use client";

import { useEffect, useState } from "react";
import { getDesktopPrompt } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Copy, Loader2 } from "lucide-react";

export function DesktopPrompt() {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getDesktopPrompt()
      .then(({ content }) => setContent(content))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  async function copy() {
    if (!content) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard API unavailable");
      await navigator.clipboard.writeText(content);
      toast.success("Desktop prompt copied — paste it into Claude Desktop");
    } catch {
      const fallback = document.createElement("textarea");
      fallback.value = content;
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
        Copy and paste into Claude Desktop (Cowork) to browse Naukri, Instahyre, Cutshort, and Wellfound using Computer Use. Finds AI/ML entry-level roles and auto-applies.
      </p>
    </CardHeader>
    <CardContent className="space-y-3">
      <div className="rounded-lg border p-3">
        <div role="toolbar" aria-label="Desktop prompt actions" className="mb-3 flex flex-wrap gap-2">
          <Button disabled={!content || loading} onClick={copy}>
            <Copy className="mr-2 h-4 w-4" />Copy prompt for Claude Desktop
          </Button>
        </div>
        {loading && <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading prompt…</div>}
        {error && <p role="alert" className="text-sm text-destructive">Could not load the desktop prompt. Check that the backend is running.</p>}
        {content && <details>
          <summary className="cursor-pointer text-sm">View prompt</summary>
          <Textarea readOnly value={content} rows={18} aria-label="Claude Desktop job search prompt" />
        </details>}
      </div>
      <p className="text-xs text-muted-foreground">
        Log into Naukri, Instahyre, Cutshort, and Wellfound in your browser before starting. The agent reads your resume from ~/Documents/resume.pdf and applies to up to 10 jobs per portal.
      </p>
    </CardContent>
  </Card>;
}
