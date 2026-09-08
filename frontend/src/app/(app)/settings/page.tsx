"use client";

import { useState, useEffect } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, Loader2, Download } from "lucide-react";
import { downloadResumePdf } from "@/lib/resumePdf";

// ---------------------------------------------------------------------------
// Settings Page — the resume is stored and edited as LaTeX source.
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
      downloadResumePdf(resumeTex, "resume.pdf");
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
    <div className="mx-auto max-w-3xl space-y-6">
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

      {/* ---- Resume (LaTeX) ---- */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>Resume (LaTeX)</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Your resume is stored as LaTeX source. Edit it here and Save —
                this is what the hourly outreach agents read. Use Download PDF to
                get a ready-to-attach PDF (generated in your browser).
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
            rows={26}
            spellCheck={false}
            className="font-mono text-xs leading-relaxed"
          />
          <p className="text-xs text-muted-foreground">
            {resumeTex.length.toLocaleString()} characters
          </p>
        </CardContent>
      </Card>

      {/* ---- Bottom Save ---- */}
      <div className="flex justify-end pb-8">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Save className="mr-2 h-4 w-4" />
          )}
          Save
        </Button>
      </div>
    </div>
  );
}
