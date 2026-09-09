"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8011";
type Stage = { stage_name: string; status: string; error?: string | null };
type Job = { id: string; topic: string; status: string };
type JobResponse = { job: Job; stages: Stage[] };
type Landscape = { clusters: { name: string; description: string; paper_indices: number[] }[]; relationships: { source_cluster: string; target_cluster: string; relationship: string }[]; tensions: string[]; open_problems: string[]; reading_list: { order: number; arxiv_id: string; title: string; url: string; relevance_score: number | null; reason: string }[] };
const stageLabels: Record<string, string> = { fetch: "Discover papers", rerank: "Rank by relevance", extract: "Read key findings", synthesize: "Map the landscape" };
function statusLabel(status: string) { return status.replaceAll("_", " "); }

export default function Home() {
  const [topic, setTopic] = useState("");
  const [papersPerSearch, setPapersPerSearch] = useState(8);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [landscape, setLandscape] = useState<Landscape | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!jobId || job?.job.status === "completed" || job?.job.status === "failed" || job?.job.status === "no_papers") return;
    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/jobs/${jobId}`, { cache: "no-store" });
        if (!response.ok) throw new Error("Could not read job status.");
        const nextJob: JobResponse = await response.json();
        setJob(nextJob);
        if (nextJob.job.status === "completed") {
          const landscapeResponse = await fetch(`${API_BASE}/api/landscape/${jobId}`, { cache: "no-store" });
          if (!landscapeResponse.ok) throw new Error("Landscape was not available.");
          setLandscape(await landscapeResponse.json());
        }
      } catch (pollError) { setError(pollError instanceof Error ? pollError.message : "The API could not be reached."); }
    };
    poll();
    const interval = window.setInterval(poll, 2500);
    return () => window.clearInterval(interval);
  }, [jobId, job?.job.status]);

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (topic.trim().length < 2) return;
    setIsSubmitting(true); setError(null); setLandscape(null); setJob(null);
    try {
      const response = await fetch(`${API_BASE}/api/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic: topic.trim(), papers_per_search: papersPerSearch }) });
      if (!response.ok) throw new Error("Search could not be started.");
      setJobId((await response.json()).job_id);
    } catch (submitError) { setError(submitError instanceof Error ? submitError.message : "The API could not be reached."); }
    finally { setIsSubmitting(false); }
  }
  const isWorking = Boolean(job && !["completed", "failed", "no_papers"].includes(job.job.status));

  return (
    <div className={styles.page}>
      <header className={styles.header}><Link className={styles.wordmark} href="/">Research<span>Map</span></Link><div className={styles.headerNote}>Evidence, arranged.</div></header>
      <main className={styles.main}>
        <section className={styles.hero}><p className={styles.eyebrow}>Research intelligence / 01</p><h1>See the field<br /><em>take shape.</em></h1><p className={styles.deck}>Turn a research question into a living map of the papers, methods, disagreements, and next questions shaping it.</p><form className={styles.searchForm} onSubmit={submitSearch}><label htmlFor="topic">What are you investigating?</label><div className={styles.inputRow}><input id="topic" value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="e.g. efficient multimodal agents" minLength={2} required /><button type="submit" disabled={isSubmitting || isWorking}>{isSubmitting ? "Starting..." : "Map the field"}<span aria-hidden="true">↗</span></button></div><div className={styles.formMeta}><span>arXiv discovery + Gemini synthesis</span><label>papers <select value={papersPerSearch} onChange={(event) => setPapersPerSearch(Number(event.target.value))}><option value={5}>5</option><option value={8}>8</option><option value={12}>12</option></select></label></div></form></section>
        {error && <div className={styles.alert} role="alert">{error}</div>}
        {job && <section className={styles.progressSection} aria-live="polite"><div className={styles.sectionHeading}><div><p className={styles.eyebrow}>Live pipeline</p><h2>{job.job.topic}</h2></div><span className={`${styles.status} ${job.job.status === "completed" ? styles.success : ""}`}>{statusLabel(job.job.status)}</span></div><div className={styles.stageGrid}>{job.stages.map((stage) => <div className={`${styles.stage} ${stage.status === "running" ? styles.active : ""}`} key={stage.stage_name}><span className={styles.stageDot} /><div><strong>{stageLabels[stage.stage_name] ?? stage.stage_name}</strong><small>{stage.error || statusLabel(stage.status)}</small></div></div>)}</div></section>}
        {landscape && <section className={styles.results}><div className={styles.sectionHeading}><div><p className={styles.eyebrow}>Synthesis complete</p><h2>How the field is organized</h2></div><span className={styles.resultCount}>{landscape.clusters.length} clusters</span></div><div className={styles.clusterGrid}>{landscape.clusters.map((cluster, index) => <article className={styles.cluster} key={cluster.name}><span className={styles.clusterNumber}>0{index + 1}</span><h3>{cluster.name}</h3><p>{cluster.description}</p><span className={styles.paperCount}>{cluster.paper_indices.length} connected papers</span></article>)}</div><div className={styles.insightGrid}><div><p className={styles.eyebrow}>Points of tension</p><ul>{landscape.tensions.map((tension) => <li key={tension}>{tension}</li>)}</ul></div><div><p className={styles.eyebrow}>Open problems</p><ul>{landscape.open_problems.map((problem) => <li key={problem}>{problem}</li>)}</ul></div></div>{landscape.relationships.length > 0 && <div className={styles.relationships}><p className={styles.eyebrow}>Connections</p>{landscape.relationships.map((relationship) => <div className={styles.relationship} key={`${relationship.source_cluster}-${relationship.target_cluster}`}><strong>{relationship.source_cluster}</strong><span>→</span><strong>{relationship.target_cluster}</strong><p>{relationship.relationship}</p></div>)}</div>}<div className={styles.readingList}><div className={styles.sectionHeading}><div><p className={styles.eyebrow}>Reading list</p><h2>Where to begin</h2></div><span className={styles.resultCount}>{landscape.reading_list.length} papers</span></div><div className={styles.readingItems}>{landscape.reading_list.map((paper) => <article className={styles.readingItem} key={paper.arxiv_id}><span className={styles.clusterNumber}>0{paper.order}</span><div><h3><a href={paper.url} target="_blank" rel="noreferrer">{paper.title}</a></h3><p>{paper.reason}</p><small>arXiv:{paper.arxiv_id}{paper.relevance_score === null ? "" : ` · relevance ${paper.relevance_score.toFixed(4)}`}</small></div></article>)}</div></div></section>}
      </main>
      <footer className={styles.footer}><span>ResearchMap</span><span>Built for the first hour of a new question.</span></footer>
    </div>
  );
}
