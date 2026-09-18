"use client";

import { useEffect, useRef, useState } from "react";
import { getProfile, uploadResumePdf } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { CheckCircle2, FileText, Loader2, Upload } from "lucide-react";

const MAX_RESUME_BYTES = 10 * 1024 * 1024;

export default function SettingsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [savedCharacters, setSavedCharacters] = useState(0);

  useEffect(() => {
    async function load() {
      try {
        const profile = await getProfile();
        setSavedCharacters(profile.resume_text?.length ?? 0);
      } catch {
        toast.error("Failed to load resume status");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  function chooseFile(file: File | undefined) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      toast.error("Please choose a PDF file");
      return;
    }
    if (file.size > MAX_RESUME_BYTES) {
      toast.error("Resume PDF must be 10 MB or smaller");
      return;
    }
    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      toast.error("Choose a resume PDF first");
      return;
    }

    setUploading(true);
    try {
      const profile = await uploadResumePdf(selectedFile);
      setSavedCharacters(profile.resume_text?.length ?? 0);
      toast.success("Resume uploaded and ready for job screening");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Resume upload failed");
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload the PDF resume that Job Search HQ should use for matching and screening.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Resume PDF</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose a text-based PDF up to 10 MB. Its text is extracted and saved
              securely for ATS checks, job screening, and draft generation.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(event) => chooseFile(event.target.files?.[0])}
            />

            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                chooseFile(event.dataTransfer.files?.[0]);
              }}
              className="flex min-h-48 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/20 px-6 text-center transition-colors hover:border-primary/60 hover:bg-muted/40"
            >
              <Upload className="mb-3 h-8 w-8 text-muted-foreground" />
              <span className="font-medium">
                {selectedFile ? selectedFile.name : "Choose or drop your resume PDF"}
              </span>
              <span className="mt-1 text-xs text-muted-foreground">
                PDF only · maximum 10 MB
              </span>
            </button>

            {selectedFile && (
              <div className="flex items-center gap-3 rounded-md border border-border p-3">
                <FileText className="h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{selectedFile.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
            )}

            <Button className="w-full" onClick={handleUpload} disabled={!selectedFile || uploading}>
              {uploading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              {uploading ? "Uploading…" : "Upload resume"}
            </Button>

            {savedCharacters > 0 && (
              <div className="flex items-start gap-2 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <p>
                  A resume is ready for screening ({savedCharacters.toLocaleString()} extracted
                  characters). Upload another PDF anytime to replace it.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="self-start lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle>PDF preview</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              Preview the selected file before uploading it.
            </p>
          </CardHeader>
          <CardContent>
            {previewUrl ? (
              <iframe
                src={previewUrl}
                title="Selected resume PDF"
                className="h-[70vh] w-full rounded border border-border bg-white"
              />
            ) : (
              <div className="flex h-[70vh] flex-col items-center justify-center rounded border border-border bg-muted/30 px-6 text-center">
                <FileText className="mb-3 h-10 w-10 text-muted-foreground/60" />
                <p className="text-sm text-muted-foreground">
                  Select a PDF to preview it here.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
