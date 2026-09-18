"use client";

import { useEffect, useRef, useState } from "react";
import { activateResumeProfile, getResumeProfileStatus, uploadResumePdf } from "@/lib/api";
import type { ResumeFact, ResumeProfile, ResumeProfileReview } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { CheckCircle2, FileText, Loader2, Plus, Trash2, Upload } from "lucide-react";

const MAX_BYTES = 10 * 1024 * 1024;
const evidence = (item: ResumeFact) => item.evidence?.map((e) => e.excerpt).filter(Boolean).join(" · ") || "User review required";

function toReview(profile: ResumeProfile): ResumeProfileReview {
  const f = profile.facts || {};
  return {
    skills: (f.skills || []).map((x) => x.name || "").filter(Boolean),
    certifications: (f.certifications || []).map((x) => x.name || "").filter(Boolean),
    experience: (f.experience || []).map((x) => ({ id: x.id, label: x.label, role: x.role, company: x.company, start: x.start, end: x.end })),
    education: (f.education || []).map((x) => ({ id: x.id, level: x.level || "bachelor", credential: x.credential || "", field: x.field, institution: x.institution })),
    review_notes: "",
  };
}

export default function SettingsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [active, setActive] = useState<ResumeProfile | null>(null);
  const [candidate, setCandidate] = useState<ResumeProfile | null>(null);
  const [review, setReview] = useState<ResumeProfileReview | null>(null);

  useEffect(() => {
    getResumeProfileStatus().then((s) => {
      setActive(s.active);
      const latest = s.latest?.status === "pending_review" ? s.latest : null;
      setCandidate(latest);
      if (latest) setReview(toReview(latest));
    }).catch(() => toast.error("Failed to load resume status")).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file); setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function choose(next?: File) {
    if (!next) return;
    if (next.type !== "application/pdf" || !next.name.toLowerCase().endsWith(".pdf")) return toast.error("Only PDF resume uploads are supported");
    if (next.size > MAX_BYTES) return toast.error("Resume PDF must be 10 MB or smaller");
    setFile(next);
  }

  async function upload() {
    if (!file) return;
    setBusy(true);
    try {
      const next = await uploadResumePdf(file); setCandidate(next); setReview(toReview(next));
      toast.success("PDF extracted. Review every fact before activating it.");
    } catch (e) { toast.error(e instanceof Error ? e.message : "Resume upload failed"); }
    finally { setBusy(false); }
  }

  async function activate() {
    if (!candidate || !review) return;
    setBusy(true);
    try {
      const saved = await activateResumeProfile(candidate.id, review);
      setActive(saved); setCandidate(null); setReview(null); setFile(null);
      toast.success(`Profile v${saved.version} is active; earlier analysis is stale and will be rescored.`);
    } catch (e) { toast.error(e instanceof Error ? e.message : "Profile activation failed"); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="flex h-[60vh] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin" /></div>;
  return <div className="mx-auto max-w-5xl space-y-6">
    <div><h1 className="text-2xl font-bold">Resume profile</h1><p className="mt-1 text-sm text-muted-foreground">Upload a text-based PDF, then verify extracted facts and evidence. DOCX, text, and LaTeX input are not accepted.</p></div>
    {active && <div className="flex gap-2 rounded-md bg-emerald-500/10 p-3 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" />Active: v{active.version} · {active.source_filename} · {active.readability.status || "unknown readability"}</div>}
    <div className="grid gap-6 lg:grid-cols-2">
      <Card><CardHeader><CardTitle>Resume PDF</CardTitle></CardHeader><CardContent className="space-y-4">
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(e) => choose(e.target.files?.[0])} />
        <button type="button" onClick={() => inputRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); choose(e.dataTransfer.files?.[0]); }} className="flex min-h-40 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center"><Upload className="mb-3 h-8 w-8 text-muted-foreground" /><span className="font-medium">{file?.name || "Choose or drop a PDF"}</span><span className="text-xs text-muted-foreground">PDF only · 10 MB · 30 pages</span></button>
        <Button className="w-full" disabled={!file || busy} onClick={upload}>{busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}Extract for review</Button>
      </CardContent></Card>
      <Card><CardHeader><CardTitle>PDF preview</CardTitle></CardHeader><CardContent>{preview ? <iframe src={preview} title="Selected resume PDF" className="h-[55vh] w-full rounded border bg-white" /> : <div className="flex h-[55vh] items-center justify-center rounded border bg-muted/30"><FileText className="h-10 w-10 text-muted-foreground" /></div>}</CardContent></Card>
    </div>
    {candidate && review && <Card><CardHeader><CardTitle>Review profile v{candidate.version}</CardTitle><p className="text-sm text-muted-foreground">Corrections remain separate; the extracted PDF text and hash never change.</p></CardHeader><CardContent className="space-y-6">
      <div><label className="text-sm font-medium">Skills (comma separated)</label><Textarea value={review.skills.join(", ")} onChange={(e) => setReview({ ...review, skills: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} /><p className="mt-1 text-xs text-muted-foreground">Evidence: {(candidate.facts.skills || []).map(evidence).join(" · ") || "None extracted"}</p></div>
      <div><label className="text-sm font-medium">Certifications (comma separated)</label><Textarea value={review.certifications.join(", ")} onChange={(e) => setReview({ ...review, certifications: e.target.value.split(",").map((v) => v.trim()).filter(Boolean) })} /><p className="mt-1 text-xs text-muted-foreground">Evidence: {(candidate.facts.certifications || []).map(evidence).join(" · ") || "None extracted"}</p></div>
      <div className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-medium">Experience</h3><Button type="button" variant="outline" size="sm" onClick={() => setReview({ ...review, experience: [...review.experience, { id: "", label: "", role: "", company: "", start: "", end: "" }] })}><Plus className="mr-1 h-3.5 w-3.5" />Add verified entry</Button></div>{review.experience.length === 0 && <p className="text-sm text-amber-600">No dated experience was extracted. Experience eligibility will remain unknown unless you add and verify an entry.</p>}{review.experience.map((item, i) => <div key={item.id || `new-experience-${i}`} className="grid gap-2 rounded border p-3 sm:grid-cols-2">
        {(["role", "company", "start", "end"] as const).map((key) => <Input key={key} value={item[key] || ""} placeholder={key === "start" ? "YYYY-MM" : key === "end" ? "YYYY-MM or present" : key} onChange={(e) => { const experience = [...review.experience]; experience[i] = { ...item, [key]: e.target.value }; setReview({ ...review, experience }); }} />)}
        <p className="text-xs text-muted-foreground">Evidence: {evidence((candidate.facts.experience || []).find((fact) => fact.id === item.id) || {})}</p><Button type="button" variant="ghost" size="sm" className="justify-self-end text-red-500" onClick={() => setReview({ ...review, experience: review.experience.filter((_, index) => index !== i) })}><Trash2 className="mr-1 h-3.5 w-3.5" />Remove</Button>
      </div>)}</div>
      <div className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-medium">Education</h3><Button type="button" variant="outline" size="sm" onClick={() => setReview({ ...review, education: [...review.education, { id: "", level: "bachelor", credential: "", field: "", institution: "" }] })}><Plus className="mr-1 h-3.5 w-3.5" />Add verified entry</Button></div>{review.education.map((item, i) => <div key={item.id || `new-education-${i}`} className="grid gap-2 rounded border p-3 sm:grid-cols-2">
        {(["level", "credential", "field", "institution"] as const).map((key) => <Input key={key} value={item[key] || ""} placeholder={key} onChange={(e) => { const education = [...review.education]; education[i] = { ...item, [key]: e.target.value }; setReview({ ...review, education }); }} />)}
        <p className="text-xs text-muted-foreground">Evidence: {evidence((candidate.facts.education || []).find((fact) => fact.id === item.id) || {})}</p><Button type="button" variant="ghost" size="sm" className="justify-self-end text-red-500" onClick={() => setReview({ ...review, education: review.education.filter((_, index) => index !== i) })}><Trash2 className="mr-1 h-3.5 w-3.5" />Remove</Button>
      </div>)}</div>
      <div><label className="text-sm font-medium">Review notes</label><Textarea value={review.review_notes || ""} onChange={(e) => setReview({ ...review, review_notes: e.target.value })} /></div>
      <Button disabled={busy} onClick={activate}>{busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}Confirm facts and activate v{candidate.version}</Button>
    </CardContent></Card>}
  </div>;
}
