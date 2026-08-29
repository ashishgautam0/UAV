"use client";

import { useState, useEffect } from "react";
import { getProfile, updateProfile } from "@/lib/api";
import type { UserProfile, UserProfileUpdate } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Save, Loader2 } from "lucide-react";

// ---------------------------------------------------------------------------
// Settings Page
// ---------------------------------------------------------------------------
export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [resumeText, setResumeText] = useState("");

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

  // ------ Save profile ------
  async function handleSave() {
    setSaving(true);
    try {
      const data: UserProfileUpdate = {
        resume_text: resumeText,
      };
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
            Paste your LaTeX resume here. This is used by the JD Analyzer and Resume Tailor.
          </p>
        </CardHeader>
        <CardContent>
          <Textarea
            value={resumeText}
            onChange={(e) => setResumeText(e.target.value)}
            placeholder="Paste your LaTeX resume here..."
            rows={20}
            className="font-mono text-sm"
          />
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
