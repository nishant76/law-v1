// Local, zero-network "brief strength" heuristic. Runs synchronously on every keystroke so the
// meter + checklist update in realtime. The AI pass (POST /filing/brief-check) is kept ONLY for
// the smart, type-specific clarifying questions — the score itself is computed here, instantly,
// with no data leaving the browser.
//
// Rules are deliberately STRICT per dimension (a bare offence noun or city name is not enough) so
// the local score tracks the AI's fairly closely and never over-claims completeness.

export interface BriefDimensionResult {
  key: string;
  label: string;
  present: boolean;
  note: string;
}

export interface BriefQuestionResult {
  id: string;
  question: string;
  why: string;
}

export interface LocalBriefAnalysis {
  detected_filing_type: string;
  completeness_score: number;
  score_band: string;
  dimensions: BriefDimensionResult[];
  questions: BriefQuestionResult[];
}

// A QUALIFIED court designation — a real forum name, NOT the bare word "court" (which is why
// typing just "court", or any stray text, no longer ticks the box). Bare "sessions"/"magistrate"
// are kept because they unambiguously denote a court tier.
const COURT_DESIGNATION_RE =
  /\b(?:high\s+court|supreme\s+court|district\s+court|family\s+court|sessions\s+court|court\s+of\s+session|sessions\s+judge|district\s+judge|civil\s+judge|chief\s+judicial\s+magistrate|judicial\s+magistrate|metropolitan\s+magistrate|magistrate\s+(?:first|1st)\s+class|jmfc|jmic|cjm|acjm|consumer(?:\s+disputes)?(?:\s+redressal)?\s+(?:commission|forum)|tribunal|lok\s+adalat|sessions|magistrate)\b/;

// Punjab / Haryana / Chandigarh districts. Used only to validate the Court FIELD the lawyer
// deliberately typed — a city merely mentioned in the narrative ("caught in mohali") is the
// crime scene, not the chosen court, so it does not tick Court & place on its own.
const DISTRICTS = [
  "chandigarh", "mohali", "sas nagar", "panchkula", "ludhiana", "amritsar", "jalandhar",
  "patiala", "bathinda", "moga", "firozpur", "ferozepur", "hoshiarpur", "kapurthala",
  "sangrur", "barnala", "mansa", "faridkot", "muktsar", "fazilka", "gurdaspur", "pathankot",
  "rupnagar", "ropar", "nawanshahr", "tarn taran", "fatehgarh sahib", "malerkotla",
  "gurugram", "gurgaon", "faridabad", "hisar", "rohtak", "karnal", "ambala", "panipat",
  "sonipat", "kurukshetra", "yamunanagar", "yamuna nagar", "sirsa", "jind", "kaithal",
  "rewari", "bhiwani", "fatehabad", "palwal", "nuh", "mewat", "mahendragarh", "narnaul",
  "charkhi dadri", "jhajjar",
];
const DISTRICT_RE = new RegExp("\\b(?:" + DISTRICTS.join("|") + ")\\b");

// "FIR" only counts as the legal basis when it carries a number (FIR No. 45 / FIR 45/2024) —
// the bare token "FIR" no longer ticks Legal issue / offence.
const FIR_NUMBER_RE = /\bf\.?\s?i\.?\s?r\.?\s*(?:no\.?|number|#|:)?\s*\d/;

// Canonical six dimensions (order + keys must match the backend brief_analyzer).
const DIMENSIONS: { key: string; label: string }[] = [
  { key: "parties", label: "Parties" },
  { key: "court_place", label: "Court & place" },
  { key: "facts_timeline", label: "Facts & timeline" },
  { key: "legal_issue", label: "Legal issue / offence" },
  { key: "relief", label: "Relief sought" },
  { key: "stage", label: "Procedural stage" },
];

// A missing-dimension → fallback question + note. Shown in realtime until the AI returns sharper,
// type-specific questions. `order` ranks importance when we trim to the top few.
const RULES: Record<
  string,
  { test: (text: string, court: string) => boolean; note: string; question: string; why: string; order: number }
> = {
  parties: {
    test: (t) => /\b(my\s+)?client\b|\b(petitioner|respondent|complainant|accused|plaintiff|defendant|applicant)\b|\bopposite\s+party\b|\bv\/?s\b|\bversus\b/.test(t),
    note: "no client or opposite party named",
    question: "Who is the opposite party or complainant?",
    why: "Both sides are needed for the cause title",
    order: 4,
  },
  court_place: {
    test: (t, court) => {
      const c = court.trim().toLowerCase();
      // Trust the Court field only when it names a real forum or a known district — not any text.
      const fieldOk = c.length > 0 && (COURT_DESIGNATION_RE.test(c) || DISTRICT_RE.test(c));
      return fieldOk || COURT_DESIGNATION_RE.test(t);
    },
    note: "no specific court mentioned",
    question: "Which court and district is this being filed in?",
    why: "Determines the correct forum and heading",
    order: 2,
  },
  facts_timeline: {
    test: (t) =>
      /\b\d{1,2}[\/.\-]\d{1,2}[\/.\-]\d{2,4}\b/.test(t) ||
      /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b/.test(t) ||
      /\b\d+\s*(day|days|week|weeks|month|months|year|years|hour|hours)\b/.test(t) ||
      /\b(dated|since|w\.?e\.?f|on\s+\d)\b/.test(t),
    note: "no key dates or timeline",
    question: "What are the key dates (incident, arrest, notice)?",
    why: "Dates fix limitation and chronology",
    order: 3,
  },
  legal_issue: {
    test: (t) =>
      /\b(?:section|sec\.?|u\/s|under\s+section)\s*\d/.test(t) ||
      /\b(?:bns|bnss|ipc|crpc|cpc|ndps|pocso|hma)\b/.test(t) ||
      FIR_NUMBER_RE.test(t) ||
      /\b138\b|\bnegotiable\s+instrument\b/.test(t),
    note: "no offence sections or FIR number",
    question: "Which sections or FIR number are involved?",
    why: "The legal basis anchors the whole draft",
    order: 1,
  },
  relief: {
    test: (t) =>
      /\b(bail|anticipatory|quash|injunction|maintenance|divorce|custody|stay|compensation|recovery|possession|eviction|probate|restrain|refund|acquittal|discharge|declaration)\b/.test(t) ||
      /\b(seek|pray|apply(ing)?\s+for|want[s]?\s+to|relief|direction)\b/.test(t),
    note: "no relief specified",
    question: "What exact relief do you want the court to grant?",
    why: "The prayer must state the relief precisely",
    order: 5,
  },
  stage: {
    test: (t) =>
      /\b(custody|arrest(ed)?|charge[\s-]?sheet|pending|summon(s|ed)?|remand|investigation|trial|convict(ed|ion)?|acquitt|jail|behind\s+bars|refused|rejected|dismissed|granted|registered)\b/.test(t) ||
      /\bnotice\s+(received|dated|issued|served)\b/.test(t),
    note: "current stage of the case not stated",
    question: "What is the current stage of the matter?",
    why: "Stage decides which application is right",
    order: 6,
  },
};

function guessFilingType(t: string): string {
  if (/\banticipatory\b/.test(t)) return "Anticipatory Bail Application";
  if (/\bbail\b/.test(t)) return "Bail Application";
  if (/\b138\b|cheque\s*(bounce|dishonou?r)|negotiable\s+instrument/.test(t)) return "Complaint under S.138 NI Act";
  if (/\bquash/.test(t)) return "Quashing Petition";
  if (/\bdivorce\b/.test(t)) return "Divorce Petition";
  if (/\bmaintenance\b/.test(t)) return "Maintenance Petition";
  if (/\bwrit\b|article\s*226/.test(t)) return "Writ Petition";
  if (/\binjunction\b/.test(t)) return "Suit for Injunction";
  if (/\brecovery\b/.test(t)) return "Suit for Recovery";
  return "";
}

function band(score: number): string {
  if (score >= 75) return "Strong";
  if (score >= 45) return "Workable";
  if (score > 0) return "Thin";
  return "Empty";
}

export function analyzeBriefLocally(brief: string, court = ""): LocalBriefAnalysis {
  const t = (brief || "").toLowerCase();
  const trimmed = (brief || "").trim();

  const dimensions: BriefDimensionResult[] = DIMENSIONS.map(({ key, label }) => {
    const rule = RULES[key];
    const present = trimmed.length > 0 && rule.test(t, court);
    return { key, label, present, note: present ? "" : rule.note };
  });

  const presentCount = dimensions.filter((d) => d.present).length;
  const score = Math.round((presentCount / DIMENSIONS.length) * 100);

  // Fallback questions for the missing dimensions, ranked by importance, capped at 4. Ids are
  // keyed by dimension so a typed answer survives re-renders. Suppressed while the brief is
  // essentially empty (nothing useful to ask yet).
  const questions: BriefQuestionResult[] =
    trimmed.length < 15
      ? []
      : dimensions
          .filter((d) => !d.present)
          .sort((a, b) => RULES[a.key].order - RULES[b.key].order)
          .slice(0, 4)
          .map((d) => ({ id: `local_${d.key}`, question: RULES[d.key].question, why: RULES[d.key].why }));

  return {
    detected_filing_type: guessFilingType(t),
    completeness_score: score,
    score_band: band(score),
    dimensions,
    questions,
  };
}
