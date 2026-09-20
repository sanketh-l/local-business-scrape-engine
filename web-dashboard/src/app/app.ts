import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

type RunStatus = {
  id: number;
  name: string;
  status: string;
  conclusion: string | null;
  html_url: string;
  created_at: string;
};

type Job = {
  id: string;
  city: string;
  country: string;
  category: string;
  status: string;
  areas_total: number;
  areas_completed: number;
  squares_total: number;
  squares_completed: number;
  raw_rows: number;
  unique_businesses: number;
  message: string;
  created_at: string;
};

type Area = { area_name: string; status: string; squares_total: number; squares_completed: number; raw_rows: number; unique_businesses: number };
type Lead = Record<string, string | number | null>;

@Component({
  imports: [FormsModule],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {
  private readonly http = inject(HttpClient);

  readonly categories = [
    'plumber', 'electrician', 'roofing contractor', 'HVAC contractor', 'house cleaning service', 'pressure washing service',
    'roof cleaning service', 'gutter cleaning service', 'gutter installation service', 'water damage restoration service',
    'mold removal service', 'pest control service', 'tree service', 'landscaper', 'lawn care service', 'painting contractor',
    'general contractor', 'bathroom remodeler', 'kitchen remodeler', 'flooring contractor', 'fence contractor', 'deck builder',
    'concrete contractor', 'masonry contractor', 'siding contractor', 'window installation service', 'garage door repair',
    'handyman', 'carpenter', 'carpet cleaning service', 'solar panel cleaning', 'window cleaning', 'pool cleaning service',
    'pool contractor', 'chimney sweep', 'septic system service', 'drain cleaning service', 'sewer contractor', 'excavation contractor',
    'foundation repair', 'basement waterproofing', 'driveway contractor', 'asphalt contractor', 'paving contractor',
    'snow removal service', 'irrigation system contractor', 'junk removal service', 'moving company', 'storage facility', 'locksmith',
    'auto repair shop', 'mobile mechanic', 'auto body shop', 'car detailing service', 'towing service', 'barber shop', 'hair salon',
    'nail salon', 'beauty salon', 'massage therapist', 'spa', 'gym', 'personal trainer', 'yoga studio', 'dog groomer',
    'veterinary clinic', 'wedding photographer', 'photographer', 'videographer', 'event planner', 'DJ service', 'wedding venue',
    'caterer', 'florist', 'accountant', 'CPA', 'tax preparation service', 'bookkeeper', 'insurance agency', 'mortgage broker',
    'real estate agency', 'property management company', 'home inspector', 'architect', 'interior designer', 'dentist',
    'chiropractor', 'physical therapist', 'optometrist', 'commercial cleaning service', 'janitorial service', 'commercial electrician',
    'commercial plumber', 'commercial HVAC', 'security system installer', 'CCTV installer', 'fire protection service', 'sign shop',
    'printing service', 'commercial landscaper', 'epoxy flooring', 'cabinet painter', 'countertop installer', 'tile contractor',
    'drywall contractor', 'insulation contractor', 'crawl space repair', 'radon mitigation', 'air duct cleaning', 'dryer vent cleaning',
    'appliance repair'
  ];

  city = 'Bengaluru';
  country = 'India';
  area = '';
  category = 'plumber';
  coverage = 'Street-level, many small squares';
  maxAreas = 25;
  workerLimit = 1;
  realScrape = false;
  complianceAck = false;

  readonly busy = signal(false);
  readonly message = signal('');
  readonly error = signal('');
  readonly runs = signal<RunStatus[]>([]);
  readonly jobs = signal<Job[]>([]);
  readonly selectedJob = signal<Job | null>(null);
  readonly areas = signal<Area[]>([]);
  readonly leads = signal<Lead[]>([]);

  constructor() {
    this.refreshRuns();
    this.refreshJobs();
    setInterval(() => {
      this.refreshJobs();
      const job = this.selectedJob();
      if (job) this.openJob(job.id);
    }, 15000);
  }

  startJob(): void {
    this.error.set('');
    this.message.set('');
    if (this.realScrape && !this.complianceAck) {
      this.error.set('Real scraping requires legal/compliance acknowledgement.');
      return;
    }
    this.busy.set(true);
    this.http.post<{ message: string; job_id: string }>('/api/start', {
      city: this.city,
      country: this.country,
      area: this.area,
      category: this.category,
      coverage: this.coverage,
      max_areas: this.maxAreas,
      worker_limit: this.workerLimit,
      real_scrape: this.realScrape,
      compliance_ack: this.complianceAck,
    }).subscribe({
      next: (response) => {
        this.message.set(response.message || 'Job started. Refresh status in a few seconds.');
        this.busy.set(false);
        if (response.job_id) this.openJob(response.job_id);
        setTimeout(() => this.refreshRuns(), 5000);
        setTimeout(() => this.refreshJobs(), 5000);
      },
      error: (err) => {
        this.error.set(err?.error?.error || 'Could not start job. Check Cloudflare function secrets.');
        this.busy.set(false);
      }
    });
  }

  refreshRuns(): void {
    this.http.get<{ runs: RunStatus[] }>('/api/runs').subscribe({
      next: (response) => this.runs.set(response.runs || []),
      error: () => this.runs.set([]),
    });
  }

  refreshJobs(): void {
    this.http.get<{ jobs: Job[] }>('/api/jobs').subscribe({
      next: (response) => {
        this.jobs.set(response.jobs || []);
        if (!this.selectedJob() && response.jobs?.length) this.openJob(response.jobs[0].id);
      },
      error: () => this.jobs.set([]),
    });
  }

  openJob(jobId: string): void {
    this.http.get<{ job: Job; areas: Area[]; leads: Lead[] }>(`/api/job?job_id=${encodeURIComponent(jobId)}`).subscribe({
      next: (response) => {
        this.selectedJob.set(response.job);
        this.areas.set(response.areas || []);
        this.leads.set(response.leads || []);
      }
    });
  }

  artifactUrl(runId: number): string {
    return `/api/artifact?run_id=${runId}`;
  }

  exportUrl(jobId: string): string {
    return `/api/export?job_id=${encodeURIComponent(jobId)}`;
  }
}
