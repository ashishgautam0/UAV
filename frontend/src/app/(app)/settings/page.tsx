"use client";

import { useState, useEffect, useRef } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, Loader2, Download } from "lucide-react";
import { buildResumePdf, downloadResumePdf } from "@/lib/resumePdf";

// ---------------------------------------------------------------------------
// Settings Page — the resume is stored and edited as LaTeX source, with a
// live PDF preview of the current draft.
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resumeTex, setResumeTex] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState(false);
  const urlRef = useRef<string | null>(null);

  // ------ Load profile on mount ------
  useEffect(() => {
    async function load() {
      try {
        const profile: UserProfile = await getProfile();
        setResumeTex(profile.resume_text ?? "");
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ------ Live PDF preview (debounced) — reflects the current draft, not the
  //        saved value, so you see edits before saving. ------
  useEffect(() => {
    if (!resumeTex.trim()) {
      setPreviewUrl(null);
      return;
    }
    const t = setTimeout(() => {
      try {
        const blob = buildResumePdf(resumeTex).output("blob");
        const url = URL.createObjectURL(blob);
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = url;
        setPreviewUrl(url);
        setPreviewError(false);
      } catch {
        setPreviewError(true);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [resumeTex]);

  // Revoke the last blob URL on unmount.
  useEffect(() => {
    return () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  // ------ Save profile ------
  async function handleSave() {
    if (!resumeTex.trim()) {
      toast.error("Resume is empty.");
      return;
    }
    setSaving(true);
    try {
      const data: UserProfileUpdate = { resume_text: resumeTex };
      await updateProfile(data);
      toast.success("Resume saved");
    } catch {
      toast.error("Failed to save resume");
    } finally {
      setSaving(false);
    }
  }

  // ------ Download the résumé as a PDF (generated in-browser) ------
  function handleDownload() {
    if (!resumeTex.trim()) {
      toast.error("Resume is empty.");
      return;
    }
    try {
      downloadResumePdf(resumeTex, "Subidh Khanal Resume.pdf");
    } catch {
      toast.error("Could not generate the PDF");
    }
  }

  // ------ Loading state ------
  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // ------ Render ------
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ---- Editor ---- */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle>Resume (LaTeX)</CardTitle>
                <p className="mt-1 text-sm text-muted-foreground">
                  Edit the LaTeX source. The preview updates as you type; changes
                  are saved only when you click Save.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="mr-1.5 h-3.5 w-3.5" />
                Download PDF
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <Textarea
              value={resumeTex}
              onChange={(e) => setResumeTex(e.target.value)}
              placeholder="\documentclass{article} ..."
              rows={28}
              spellCheck={false}
              className="font-mono text-xs leading-relaxed"
            />
            <p className="text-xs text-muted-foreground">
              {resumeTex.length.toLocaleString()} characters
            </p>
          </CardContent>
        </Card>

        {/* ---- Live preview ---- */}
        <Card className="lg:sticky lg:top-6 self-start">
          <CardHeader>
            <CardTitle>Preview</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Live preview of the PDF you&apos;ll download.
            </p>
          </CardHeader>
          <CardContent>
            {previewError ? (
              <div className="flex h-[80vh] items-center justify-center rounded border border-border bg-muted/30 p-4 text-center text-sm text-muted-foreground">
                Couldn&apos;t render a preview from the current LaTeX.
              </div>
            ) : previewUrl ? (
              <iframe
                key={previewUrl}
                src={previewUrl}
                title="Resume preview"
                className="h-[80vh] w-full rounded border border-border bg-white"
              />
            ) : (
              <div className="flex h-[80vh] items-center justify-center rounded border border-border bg-muted/30 text-sm text-muted-foreground">
                Nothing to preview yet.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
