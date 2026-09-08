"use client";

import { useState, useEffect, useMemo } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, Loader2, Download } from "lucide-react";
import { parseResume, downloadResumePdf, type Block } from "@/lib/resumePdf";

// ---------------------------------------------------------------------------
// A live HTML preview of the résumé, rendered from the same parser that builds
// the PDF — so it always renders (no PDF/iframe plugin needed) and stays in
// sync with the download.
// ---------------------------------------------------------------------------
function ResumePreview({ latex }: { latex: string }) {
  const blocks = useMemo<Block[]>(() => {
    try {
      return parseResume(latex);
    } catch {
      return [];
    }
  }, [latex]);

  if (!latex.trim()) {
    return (
      <div className="flex h-[70vh] items-center justify-center rounded border border-border bg-muted/30 text-sm text-muted-foreground">
        Nothing to preview yet.
      </div>
    );
  }

  return (
    <div className="h-[70vh] overflow-y-auto rounded border border-border bg-white">
      <div className="mx-auto max-w-[720px] px-10 py-8 text-neutral-900">
        {blocks.map((b, i) => {
          switch (b.t) {
            case "name":
              return (
                <h2 key={i} className="text-center text-2xl font-bold tracking-tight">
                  {b.text}
                </h2>
              );
            case "contact":
              return (
                <p key={i} className="mt-1 text-center text-[11px] text-neutral-600">
                  {b.text}
                </p>
              );
            case "section":
              return (
                <h3
                  key={i}
                  className="mt-5 mb-2 border-b border-neutral-400 pb-0.5 text-xs font-bold uppercase tracking-wide"
                >
                  {b.text}
                </h3>
              );
            case "subheading":
              return (
                <div key={i} className="mt-2">
                  <div className="flex justify-between gap-3">
                    <span className="text-[13px] font-bold">{b.left}</span>
                    <span className="shrink-0 text-[12px] text-neutral-600">{b.right}</span>
                  </div>
                  {(b.subLeft || b.subRight) && (
                    <div className="flex justify-between gap-3 italic">
                      <span className="text-[12px] text-neutral-700">{b.subLeft}</span>
                      <span className="shrink-0 text-[12px] text-neutral-600">{b.subRight}</span>
                    </div>
                  )}
                </div>
              );
            case "project":
              return (
                <div key={i} className="mt-2 flex justify-between gap-3">
                  <span className="text-[13px] font-semibold">{b.left}</span>
                  <span className="shrink-0 text-[12px] text-neutral-600">{b.right}</span>
                </div>
              );
            case "item":
              return (
                <div key={i} className="mt-1 flex gap-2 text-[12px] leading-snug text-neutral-800">
                  <span className="mt-[2px]">•</span>
                  <span className="flex-1">{b.text}</span>
                </div>
              );
            case "skill":
              return (
                <p key={i} className="mt-1 text-[12px] leading-snug text-neutral-800">
                  <span className="font-bold">{b.label}: </span>
                  {b.rest}
                </p>
              );
            case "plain":
              return (
                <p key={i} className="mt-1 text-[12px] leading-snug text-neutral-800">
                  {b.text}
                </p>
              );
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Settings Page — the resume is stored and edited as LaTeX source, with a
// live preview of the current draft.
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resumeTex, setResumeTex] = useState("");

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
              How your résumé reads — updates live as you edit.
            </p>
          </CardHeader>
          <CardContent>
            <ResumePreview latex={resumeTex} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
