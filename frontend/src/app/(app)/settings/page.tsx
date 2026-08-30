"use client";

import { useState, useEffect, useRef } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, Loader2, Upload, FileText } from "lucide-react";

// ---------------------------------------------------------------------------
// Extract plain text from a PDF, in the browser, via pdf.js.
// Loaded dynamically so pdf.js never runs during SSR / build.
// ---------------------------------------------------------------------------
async function extractPdfText(file: File): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
  const buf = await file.arrayBuffer();
  const pdf = await pdfjs.getDocument({ data: buf }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    // Join items; insert line breaks on large vertical jumps so the text
    // keeps a readable structure rather than one long run.
    let lastY: number | null = null;
    let line = "";
    const out: string[] = [];
    for (const item of content.items as Array<{ str: string; transform: number[] }>) {
      const y = item.transform[5];
      if (lastY !== null && Math.abs(y - lastY) > 4) {
        out.push(line.trim());
        line = "";
      }
      line += item.str + " ";
      lastY = y;
    }
    if (line.trim()) out.push(line.trim());
    pages.push(out.join("\n"));
  }
  return pages.join("\n\n").replace(/\n{3,}/g, "\n\n").trim();
}

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const [resumeText, setResumeText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // ------ Load profile on mount ------
  useEffect(() => {
    async function load() {
      try {
        const profile: UserProfile = await getProfile();
        setResumeText(profile.resume_text ?? "");
      } catch {
        toast.error("Failed to load profile");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ------ Handle a picked PDF ------
  async function handleFile(file: File | undefined | null) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Please upload a PDF file.");
      return;
    }
    setParsing(true);
    try {
      const text = await extractPdfText(file);
      if (!text) {
        toast.error("Couldn't read any text — is this a scanned/image PDF?");
        return;
      }
      setResumeText(text);
      setFileName(file.name);
      toast.success(`Extracted ${text.length.toLocaleString()} characters from ${file.name}`);
    } catch {
      toast.error("Failed to read the PDF.");
    } finally {
      setParsing(false);
    }
  }

  // ------ Save profile ------
  async function handleSave() {
    setSaving(true);
    try {
      const data: UserProfileUpdate = { resume_text: resumeText };
      await updateProfile(data);
      toast.success("Profile saved successfully");
    } catch {
      toast.error("Failed to save profile");
    } finally {
      setSaving(false);
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

      {/* ---- Resume ---- */}
      <Card>
        <CardHeader>
          <CardTitle>Resume</CardTitle>
          <p className="text-sm text-muted-foreground">
            Upload your resume as a PDF. The text is extracted and used by the
            JD Analyzer, Resume Tailor, and the hourly outreach agents.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Drop / pick a PDF */}
          <div
            onClick={() => fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFile(e.dataTransfer.files?.[0]);
            }}
            className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center transition-colors hover:bg-muted/50"
          >
            {parsing ? (
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            ) : (
              <Upload className="h-6 w-6 text-muted-foreground" />
            )}
            <p className="text-sm font-medium">
              {parsing ? "Reading PDF…" : "Click to upload or drag a PDF here"}
            </p>
            {fileName && !parsing && (
              <p className="flex items-center gap-1.5 text-xs text-emerald-400">
                <FileText className="h-3.5 w-3.5" />
                {fileName} — extracted
              </p>
            )}
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>

          {/* Extracted text — editable before saving */}
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              Extracted text (review and edit if needed, then Save)
            </p>
            <Textarea
              value={resumeText}
              onChange={(e) => setResumeText(e.target.value)}
              placeholder="Upload a PDF above, or paste your resume text here…"
              rows={18}
              className="text-sm"
            />
          </div>
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
