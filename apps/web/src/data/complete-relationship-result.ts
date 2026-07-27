export type SignalLevel = "低" | "中" | "中高" | "高" | "有條件";

export type QuestionSelectorTrace = {
  version: "western-question-selector-v1";
  questionKey: string;
  role: "evidence_weighting_policy" | string;
  methodClaimIds: string[];
  evidenceClusterKeys?: string[];
};

export type Metric = {
  key: "attraction" | "pressure" | "chance" | "action";
  label: string;
  value: SignalLevel | string;
  helper: string;
  themeKey?: string;
  relationshipThemeLabel?: string;
  source?: string;
  methodClaimIds?: string[];
};

export type Insight = {
  label: string;
  title: string;
  body: string;
  source: string;
};

export type ReasonCard = {
  label: string;
  body: string;
  value: number;
  themeKey?: string;
  relationshipThemeLabel?: string;
  source?: string;
  methodClaimIds?: string[];
  selectorEvidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  nextMove?: string;
  readableInterpretation?: ReadableInterpretation;
};

export type TimelineStep = {
  range: string;
  title: string;
  body: string;
  themeKey?: string;
  relationshipThemeLabel?: string;
  source?: string;
  methodClaimIds?: string[];
  selectorEvidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  nextMove?: string;
  readableInterpretation?: ReadableInterpretation;
};

export type CalculationStep = {
  label: string;
  result: string;
};

export type AuthorityReason = {
  system: string;
  title: string;
  because: string;
  therefore: string;
  avoid: string;
  source: string;
};

export type ChapterEvidence = {
  label: string;
  title: string;
  body: string;
  source: string;
};

export type ReadingChapterId = "thoughts" | "reasons" | "chance";

export type Pillars = {
  year: string;
  month: string;
  day: string;
  hour: string;
};

export type CalculationProofPerson = {
  label: "你" | "對方";
  birth: string;
  dayMaster: string;
  dayPillar: string;
  pillars: Pillars;
};

export type CalculationProof = {
  status: "calculated";
  people: CalculationProofPerson[];
};

export type RelationshipDiagnosisSupport = {
  label: string;
  title: string;
  body: string;
};

export type RelationshipDiagnosis = {
  label: string;
  headline: string;
  body: string;
  support: RelationshipDiagnosisSupport[];
  questionLens: {
    label: string;
    title: string;
    body: string;
  };
};

export type CaseConfidence = "low" | "medium" | "high";

export type CaseFileClaimSupport = {
  claimId: string;
  articleId?: string;
  claim: string;
  confidence: "DOCTRINE" | "INTERPRETATION" | "SPECULATIVE";
  sourceId?: string;
  sourceLocation?: string;
};

export type CaseFileEvidence = {
  system: "bazi" | "western" | "context" | "method";
  label: string;
  technical: string;
  emotionalMeaning: string;
  doesNotProve: string;
  confidence: CaseConfidence;
  source: string;
  strength?: number;
  atomId?: string | null;
  claimIds?: string[];
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternNeedPoint = {
  point: "Moon" | "Mercury" | "Venus" | "Mars" | "Saturn" | "Desc";
  label: string;
  sign: string;
  house?: number | null;
  meaning: string;
  confidence?: CaseConfidence;
  precisionNote?: string;
};

export type WesternBirthPrecision = "exact_time" | "date_only" | "location_fallback" | "unavailable";

export type RelationshipCaseModelTrace = {
  version: "relationship-case-model-trace-v1";
  caseModelVersion: "relationship-case-model-v1";
  sectionId: ResultReadingSectionId | "final-reading";
  primaryDynamicKey: string;
  secondaryDynamicKey: string;
  secondaryRole: RelationshipCaseModelSecondaryRole | string;
  grammarId: string;
  grammarMode: "explicit" | "composed";
  caseEvidenceIds: string[];
};

export type ReadableInterpretation = {
  version: "readable-interpretation-v1";
  module: "person_function_sign" | "fit_summary" | "fit_summary_item" | string;
  locale: "zh-TW";
  headline?: string;
  meaning?: string;
  body: string;
  stuckPattern?: string;
  nextMove?: string;
  caution?: string;
  confidenceNote?: string | null;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  caseModelTrace?: RelationshipCaseModelTrace;
  questionSelector?: QuestionSelectorTrace;
  debug?: Record<string, unknown>;
};

export type ResultReadingSectionId =
  | "chart-positioning"
  | "relationship-fit"
  | "core-answer"
  | "timing-reading"
  | "action-direction";

export type NarrativeEvidence = {
  id: string;
  domain: string;
  role: string;
  conceptKey: string;
  source: string;
  proposition: string;
  confidence: number;
  relevance: number;
  sourceClaimIds: string[];
  methodClaimIds: string[];
  evidenceClusterKeys: string[];
};

export type SectionNarrativeSpec = {
  version: "section-narrative-spec-v1" | "section-narrative-spec-v2" | "section-narrative-spec-v3";
  sectionId: ResultReadingSectionId;
  purpose: string;
  context: {
    stageKey?: string;
    questionKey?: string;
    contactKey?: string;
  };
  semanticSlots: Record<string, unknown>;
  conceptKeys: string[];
  forbiddenConceptKeys: string[];
  evidence: NarrativeEvidence[];
  trace: {
    evidenceIds: string[];
    sourceClaimIds: string[];
    methodClaimIds: string[];
    evidenceClusterKeys: string[];
  };
  caseModelTrace?: RelationshipCaseModelTrace;
  validation: {
    status: "valid" | "invalid";
    errors: string[];
    warnings: string[];
  };
};

export type SectionNarrativeSpecBundle = {
  version: "section-narrative-spec-v1" | "section-narrative-spec-v2" | "section-narrative-spec-v3";
  rendererConsumesSpecs: true;
  rendererVersion: "section-spec-renderer-v1" | "section-spec-renderer-v2" | "section-spec-renderer-v3";
  sections: Record<ResultReadingSectionId, SectionNarrativeSpec>;
  validation: {
    status: "valid" | "invalid";
    errors: string[];
    warnings: string[];
    sectionCount: number;
  };
};

export type FinalReadingInterpretation = {
  version: "final-reading-interpretation-v1";
  locale: "zh-TW";
  questionKey: string;
  questionLabel: string;
  stageKey?: string;
  contextStoryline?: RelationshipContextStoryline;
  sections: Record<ResultReadingSectionId, ReadableInterpretation>;
  sectionSpecs?: SectionNarrativeSpecBundle;
  caseModelTrace?: RelationshipCaseModelTrace;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipThesisEvidenceDomain =
  | "userNatal"
  | "partnerNatal"
  | "synastry"
  | "timing"
  | "relationshipContext"
  | "method";

export type RelationshipThesisEvidenceRole =
  | "supports"
  | "complicates"
  | "activates"
  | "limits";

export type RelationshipThesisEvidenceRef = {
  id: string;
  domain: RelationshipThesisEvidenceDomain;
  proposition: string;
  role: RelationshipThesisEvidenceRole;
  relevance: number;
  confidence: number;
  source?: string;
  evidenceClusterKeys?: string[];
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  allowedInference: string[];
  prohibitedInference: string[];
};

export type RelationshipThesisCandidateDynamic = {
  id: string;
  dynamicKey: string;
  dynamic: string;
  evidenceIds: string[];
  score: number;
  rankingFactors: {
    questionRelevance: number;
    currentActivation: number;
    evidenceStrength: number;
    crossLayerSupport: number;
    caseDistinctiveness: number;
    overreachPenalty: number;
  };
};

export type RelationshipThesis = {
  version: "relationship-thesis-v1";
  questionKey: string;
  questionReframe: string;
  centralThesis: string;
  dominantTension: {
    poleA: string;
    poleB: string;
    currentPattern: string;
    desiredShift: string;
  };
  interactionLoop: {
    userTrigger: string;
    userResponse: string;
    partnerTrigger: string;
    partnerResponse: string;
    reinforcingEffect: string;
  };
  currentActivation: string;
  secondaryModifier?: string;
  observableSigns: Array<{
    behavior: string;
    interpretation: string;
    valence: "supportive" | "caution" | "ambiguous";
    evidenceIds?: string[];
  }>;
  changeCondition: {
    strengthensReadingWhen: string[];
    weakensReadingWhen: string[];
  };
  decisionBoundary: {
    continueWhen: string;
    stepBackWhen: string;
  };
  uncertainty: {
    level: "low" | "medium" | "high";
    reason: string;
    alternativeReading?: string;
  };
  evidencePacket: RelationshipThesisEvidenceRef[];
  candidateDynamics: RelationshipThesisCandidateDynamic[];
  selectedCandidateId: string;
  evidenceMap: Array<{
    thesisField: string;
    evidenceIds: string[];
  }>;
  prohibitedConclusions: string[];
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  validation: {
    passed: boolean;
    failures: string[];
    warnings: string[];
    hardRequirements: string[];
  };
};

export type RelationshipCaseModelSecondaryRole =
  | "amplifier"
  | "blocker"
  | "repairLever"
  | "softener"
  | "timingActivator";

export type RelationshipCaseModelDynamic = {
  key: string;
  label: string;
  score?: number;
  candidateId?: string;
  evidenceIds: string[];
};

export type RelationshipCaseModelPrimaryDynamic = RelationshipCaseModelDynamic & {
  centralThesis: string;
  readerMeaning: string;
};

export type RelationshipCaseModelSecondaryDynamic = RelationshipCaseModelDynamic & {
  role: RelationshipCaseModelSecondaryRole;
  roleLabel: string;
  interactionEffect: string;
  whyItMatters: string;
};

export type RelationshipCaseModelPosture = {
  key: string;
  label: string;
  summary?: string;
  implication?: string;
  interpretation?: string;
  nextMove?: string;
  guidance?: string;
  evidenceIds?: string[];
  evidenceClusterKeys?: string[];
  [key: string]: unknown;
};

export type RelationshipCaseModelSectionPlan = {
  interpretiveJob: string;
  caseBridge: string;
  mustUse: string[];
  avoid: string[];
  evidenceClusterKeys: string[];
};

export type RelationshipContextStoryline = {
  version: "relationship-context-storyline-v1";
  comboKey: string;
  stageKey: string;
  questionKey: string;
  contactKey: string;
  stageLabel: string;
  questionLabel: string;
  contactLabel: string;
  storyTitle: string;
  storyPremise: string;
  storyFocus: string;
  whatMustBeProven: string;
  wrongReadingToAvoid: string;
  nextActionFrame: string;
  sectionDirectives: Record<
    ResultReadingSectionId,
    {
      headline: string;
      meaning: string;
      bridge: string;
      nextMove: string;
      caution: string;
    }
  >;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipCaseModelDynamicInteractionPlan = {
  version: "dynamic-interaction-plan-v1";
  grammarId: string;
  grammarMode: "explicit" | "composed";
  matchedGrammar: boolean;
  primaryKey: string;
  secondaryKey: string;
  secondaryRole: RelationshipCaseModelSecondaryRole | string;
  questionKey: string;
  dynamicInteraction: string;
  whatThisMeans: string;
  whatItDoesNotMean: string;
  repairImplication: string;
  actionBoundary: string;
  timingModifier: string;
  contactModifier: string;
  phrasesToAvoid: string[];
  evidenceIds: string[];
};

export type RelationshipCaseModel = {
  version: "relationship-case-model-v1";
  questionKey: string;
  stageKey: string;
  sourceThesisVersion: string;
  primaryDynamic: RelationshipCaseModelPrimaryDynamic;
  secondaryDynamics: RelationshipCaseModelSecondaryDynamic[];
  centralLoop: {
    summary: string;
    steps: Record<string, string>;
    evidenceIds: string[];
  };
  emotionalBlocker: RelationshipCaseModelPosture;
  repairLever: RelationshipCaseModelPosture;
  contactPosture: RelationshipCaseModelPosture;
  timingPosture: RelationshipCaseModelPosture;
  riskPosture: RelationshipCaseModelPosture;
  answerStrategy: RelationshipCaseModelPosture & {
    questionKey: string;
    questionLabel: string;
    headline: string;
    directAnswer: string;
    principle: string;
    watchFor?: string[];
    stopLine?: string;
  };
  dynamicInteractionPlan: RelationshipCaseModelDynamicInteractionPlan;
  contextStoryline?: RelationshipContextStoryline;
  evidenceMap: Array<Record<string, unknown>>;
  sectionPlans: Record<ResultReadingSectionId, RelationshipCaseModelSectionPlan>;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  validation?: {
    passed: boolean;
    failures: string[];
  };
};

export type RelationshipThemeContext = {
  version: "repeated-theme-result-context-v1";
  themeKey: string;
  label: string;
  count: number;
  selectedCount: number;
  pairKeys: string[];
  selectedEvidenceIds: string[];
  answerFocus: string;
  actionFocus: string;
  timingFocus: string;
  source: string;
  methodClaimIds: string[];
  doesNotProve: string;
};

export type RelationshipInsightAspectItem = {
  id: string;
  pairKey: string;
  title: string;
  personAPoint?: string;
  personBPoint?: string;
  aspect?: string;
  aspectLabel?: string;
  orb?: number | null;
  contactType?: string;
  strength?: number;
  technical: string;
  meaning: string;
  everydaySignal: string;
  advice: string;
  doesNotProve: string;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipDynamicsBlock = {
  version: "relationship-dynamics-v1";
  key: "attractionDynamics" | "conflictDynamics" | "growthDynamics" | string;
  label: string;
  headline: string;
  summary: string;
  items: RelationshipInsightAspectItem[];
  gaps?: Array<{
    label?: string;
    status: string;
    reason: string;
  }>;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type RelationshipArchetypeBlock = {
  version: "relationship-archetype-v1";
  title: string;
  subtitle: string;
  meaning: string;
  whySelected: string[];
  strengths: string[];
  risks: string[];
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type PartnerNeedItem = {
  point: string;
  title: string;
  need: string;
  relationshipStyleWanted?: string;
  emotionalSafetyCondition?: string;
  affectionLanguage?: string;
  conflictDefense?: string;
  commitmentPace?: string;
  whatOpensHimUp?: string;
  whatShutsHimDown?: string;
  commonMisread?: string;
  finalActionSuggestion?: string;
  howItShowsUp: string;
  whatHelps: string;
  confidence?: CaseConfidence | string;
  precisionNote?: string;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type PartnerNeedsBlock = {
  version: "partner-needs-v1";
  label: string;
  framing: string;
  profile?: {
    title?: string;
    relationshipStyleWanted?: string;
    emotionalSafetyCondition?: string;
    affectionLanguage?: string;
    communicationNeed?: string;
    conflictDefense?: string;
    commitmentPace?: string;
    whatOpensHimUp?: string;
    whatShutsHimDown?: string;
    commonMisread?: string;
    boundaryNote?: string;
  };
  items: PartnerNeedItem[];
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type FightLandmineItem = {
  title: string;
  trigger: string;
  whyItHappens: string;
  whatToDoInstead: string;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type FightLandminesBlock = {
  version: "fight-landmines-v1";
  label: string;
  items: FightLandmineItem[];
  gaps?: Array<{ status: string; reason: string }>;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type SurvivalGuideItem = {
  title: string;
  body: string;
  why: string;
  evidenceClusterKeys?: string[];
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
};

export type SurvivalGuideBlock = {
  version: "survival-guide-v1";
  label: string;
  items: SurvivalGuideItem[];
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type RelationshipTurningWindowItem = {
  title: string;
  windowLabel: string;
  periodLabel?: string;
  categoryLabel?: string;
  technical: string;
  meaning: string;
  suggestion: string;
  whatToAvoid: string;
  transitPoint?: string;
  natalPoint?: string;
  aspect?: string;
  strength?: number;
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipTurningWindowsBlock = {
  version: "relationship-turning-windows-v1";
  label: string;
  saferLabel: string;
  precision: "climate_window_not_exact_date" | string;
  preciseDatesAvailable: false;
  summary: string;
  items: RelationshipTurningWindowItem[];
  source: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type RelationshipInsightLayer = {
  version: "relationship-insight-layer-v1";
  relationshipArchetype: RelationshipArchetypeBlock;
  attractionDynamics: RelationshipDynamicsBlock;
  conflictDynamics: RelationshipDynamicsBlock;
  growthDynamics: RelationshipDynamicsBlock;
  partnerNeeds: PartnerNeedsBlock;
  fightLandmines: FightLandminesBlock;
  survivalGuide: SurvivalGuideBlock;
  relationshipTurningWindows: RelationshipTurningWindowsBlock;
  methodClaimIds?: string[];
  source: string;
};

export type ActionGuidance = {
  statusKey?: string;
  statusLabel?: string;
  actionScale?: number;
  actionMode?: string;
  blockedActions?: string[];
  nextMove?: string;
  relationshipTheme?: RelationshipThemeContext | Record<string, never>;
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  readableInterpretation: ReadableInterpretation;
};

export type TimingSignal = {
  key: string;
  title: string;
  state: "support" | "caution" | "none" | string;
  body: string;
};

export type TimingGuidance = {
  version: "timing-guidance-v1";
  recommendedAction?: string;
  recommendedActionLabel?: string;
  contactMode?: string;
  topBand?: string;
  topBandLabel?: string;
  sampleCount?: number;
  preciseDatesAvailable?: boolean;
  selectedSignals?: TimingSignal[];
  nextMove?: string;
  relationshipTheme?: RelationshipThemeContext | Record<string, never>;
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  readableInterpretation: ReadableInterpretation;
};

export type AnswerGuidance = {
  version: "answer-guidance-v1";
  questionKey: string;
  questionLabel: string;
  ruleId?: string | null;
  ruleConfidence?: string | null;
  shortAnswer?: string;
  evidenceHighlights?: Array<{
    key: string;
    title: string;
    body: string;
  }>;
  nextMove?: string;
  relationshipTheme?: RelationshipThemeContext | Record<string, never>;
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  readableInterpretation: ReadableInterpretation;
  normalUserAnswer?: NormalUserAnswer;
};

export type NormalUserAnswer = {
  version: "normal-user-answer-v1";
  questionKey: string;
  questionLabel: string;
  stageKey?: string;
  contactStatusKey?: string;
  tone?: string;
  headline: string;
  directAnswer: string;
  whyThisMatters: string;
  whatToWatch: string[];
  nextStep: string;
  stopLine: string;
  evidenceBridge: string;
  blocks: Array<{
    key: "directAnswer" | "whyThisMatters" | "whatToWatch" | "nextStep" | "stopLine" | string;
    label: string;
    body?: string;
    items?: string[];
  }>;
  relationshipTheme?: RelationshipThemeContext | Record<string, never>;
  sourceTraceIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
};

export type ReadableQuestionAnswer = {
  version: "readable-question-answer-v1";
  locale: "zh-TW";
  questionKey: string;
  questionLabel: string;
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  questionSelector?: QuestionSelectorTrace;
  sections: {
    answer?: AnswerGuidance;
    action?: ActionGuidance;
    timing?: TimingGuidance;
    finalInterpretation?: FinalReadingInterpretation;
    thoughts: Array<{
      body: string;
      methodClaimIds?: string[];
      evidenceClusterKeys?: string[];
      questionSelector?: QuestionSelectorTrace;
      readableInterpretation: ReadableInterpretation;
    }>;
    reasons: ReasonCard[];
    chance: {
      value: number;
      notes: string[];
      nextMove?: string;
      relationshipTheme?: RelationshipThemeContext | Record<string, never>;
      methodClaimIds?: string[];
      selectorEvidenceClusterKeys?: string[];
      questionSelector?: QuestionSelectorTrace;
      readableInterpretation?: ReadableInterpretation;
    };
    timeline: TimelineStep[];
    donts: Array<{
      body: string;
      themeKey?: string;
      relationshipThemeLabel?: string;
      source?: string;
      methodClaimIds?: string[];
      evidenceClusterKeys?: string[];
      questionSelector?: QuestionSelectorTrace;
      readableInterpretation: ReadableInterpretation;
    }>;
  };
};

export type RelationshipProfileCard = {
  key: "emotionalSafety" | "communicationRepair" | "affectionAttraction" | "pursuitConflict" | "defenseDelay";
  point: "Moon" | "Mercury" | "Venus" | "Mars" | "Saturn";
  title: string;
  placement: string;
  sign?: string;
  signLabel?: string;
  element?: string;
  elementLabel?: string;
  modality?: string;
  modalityLabel?: string;
  style: string;
  suitableFor: string;
  doesNotFit: string;
  naturalResponse?: string;
  tensionPattern?: string;
  relationshipUse: string;
  elementStyle?: string;
  modalityStyle?: string;
  readableInterpretation?: ReadableInterpretation;
  confidence: CaseConfidence;
};

export type RelationshipProfilePerson = {
  role: "person_a" | "person_b";
  label: "你" | "對方";
  headline: string;
  summary: string;
  precision?: WesternBirthPrecision;
  confidence: CaseConfidence;
  cards: RelationshipProfileCard[];
  translationBaseline?: RelationshipTranslationBaselinePerson;
  suitableFor: string[];
  doesNotFit: string[];
  partnerExpectation?: {
    point: "Desc";
    placement?: string;
    style?: string;
    confidence?: CaseConfidence;
    precisionNote?: string;
  } | null;
  precisionWarnings: string[];
};

export type RelationshipTranslationBaselinePerson = {
  roleLabel: string;
  emotionalNeed: string;
  loveLanguage: string;
  communicationStyle: string;
  conflictResponse: string;
  commitmentRhythm: string;
  closenessTrigger: string;
  withdrawalTrigger: string;
  misunderstandingRisk: string;
  summary: string;
};

export type RelationshipProfileFitItem = {
  point: "Moon" | "Mercury" | "Venus" | "Mars" | "Saturn" | "MoonVenus" | "PivotalAspect";
  title: string;
  relation: "natural" | "effort" | "friction";
  relationLabel: string;
  personA: string;
  personB: string;
  body: string;
  nextMove?: string;
  readableInterpretation?: ReadableInterpretation;
  source: string;
  confidence: CaseConfidence;
};

export type RelationshipProfiles = {
  version: "relationship-profiles-v1";
  principle: string;
  personA: RelationshipProfilePerson;
  personB: RelationshipProfilePerson;
  translationBaseline?: {
    version: "relationship-translation-baseline-v1" | string;
    personA: RelationshipTranslationBaselinePerson;
    personB: RelationshipTranslationBaselinePerson;
    principle: string;
  };
  fitSummary: {
    headline: string;
    summary: string;
    natural: RelationshipProfileFitItem[];
    effort: RelationshipProfileFitItem[];
    friction: RelationshipProfileFitItem[];
    pivotalAspect?: RelationshipProfileFitItem | null;
    safetyValidationLanguage?: Record<string, unknown>;
    readableInterpretation?: ReadableInterpretation;
    doesNotProve: string;
    source: string;
    atomId?: string | null;
    claimIds?: string[];
    claimSupport?: CaseFileClaimSupport[];
  };
  precisionWarnings: string[];
  answerBridge: string;
  sourceClusters: string[];
};

export type RelationshipFitLensRating = {
  key: string;
  label: string;
  rating: "高" | "中高" | "中" | "偏低" | "需要觀察" | string;
  value: number;
  becauseA: string;
  becauseB: string;
  proof: string;
  reason: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipFitLensPoint = {
  title: string;
  becauseA: string;
  becauseB: string;
  proof: string;
  body: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipFitLensLoop = {
  title: string;
  summary: string;
  steps: Array<{
    label: string;
    body: string;
  }>;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
};

export type RelationshipFitLensCondition = {
  label: string;
  body: string;
  watchFor: string;
  evidenceClusterKeys?: string[];
};

export type RelationshipFitLens = {
  version: "relationship-fit-lens-v1";
  relationshipType: {
    title: string;
    subtitle: string;
    meaning: string;
    reasons: string[];
	    becauseA: string;
	    becauseB: string;
	    sideNote?: string;
	    doesNotProve: string;
	  };
  radar: RelationshipFitLensRating[];
  bestPlaces: RelationshipFitLensPoint[];
  stuckLoop: RelationshipFitLensLoop;
  conditions: RelationshipFitLensCondition[];
  summary: string;
  sourceClaimIds?: string[];
  methodClaimIds?: string[];
  evidenceClusterKeys?: string[];
  doesNotProve: string;
};

export type WesternBirthDataQuality = {
  role: "person_a" | "person_b";
  label: "你" | "對方";
  precision: WesternBirthPrecision;
  timeKnown: boolean;
  locationKnown: boolean;
  housesAllowed: boolean;
  moonConfidence: CaseConfidence;
  warnings: string[];
};

export type WesternCalculationSettings = {
  engine: string;
  engineVersion?: string | null;
  zodiac: "tropical";
  houseSystem: "placidus";
  aspectPolicy: "relationship-v1";
  timingMethod: "western-current-transits-v1";
  analysisDate?: string;
  analysisDateTime?: string | null;
  analysisTimezone?: string | null;
  timingPrecision?: "analysis_datetime" | "analysis_date_noon_fallback" | string;
};

export type WesternPrecisionGate = {
  requiresBirthTime: boolean;
  requiresKnownPlace: boolean;
  display: "allowed" | "allowed_with_uncertainty" | "blocked";
  reason: string;
};

export type WesternHouseAnglePrecisionGate = {
  version: "house-angle-precision-gate-v1" | string;
  status: "allowed_by_precision" | "blocked_by_birth_time" | "blocked_by_location" | "partially_allowed" | string;
  role: "precision_context_layer" | string;
  requiresReliableBirthTime: boolean;
  requiresReliableLocation: boolean;
  allowsAngles: boolean;
  allowsNatalHouses: boolean;
  allowsHouseOverlaysByPrecision: boolean;
  canCreateAstrologyConclusion: boolean;
  requiresCalculatedHouseOrAngleEvidence: boolean;
  contextLayerOnly: boolean;
  blockedClaims: string[];
  missingBirthTimeCount: number;
  missingLocationCount: number;
  housesAllowedCount: number;
  people: Array<{
    role: "person_a" | "person_b" | string;
    label: string;
    hasReliableBirthTime: boolean;
    hasReliableLocation: boolean;
    housesAllowed: boolean;
  }>;
  sourceArticleIds: string[];
  sourceClaimIds: string[];
  houseOverlayCalculationAvailable?: boolean;
};

export type WesternEvidenceClusterCategory =
  | "attraction"
  | "emotionalSafety"
  | "pressure"
  | "communication"
  | "repair"
  | "currentTransits"
  | "timingWindowBand"
  | "timingMercuryCommunication"
  | "timingVenusSoftening"
  | "timingMarsActivation"
  | "timingSaturnPressure"
  | "timingMoonWeather"
  | "timingContactReducer"
  | "birthDataQuality"
  | "identityNeeds"
  | "relationshipStage"
  | "contactStatus"
  | "contactSituationPolicy"
  | "emotionalRisk"
  | "desiredOutcome"
  | "methodOrder"
  | "natalSymbolFoundation"
  | "planetaryFunctions"
  | "signClassificationFoundation"
  | "elementStyleFoundation"
  | "modalityResponseFoundation"
  | "planetSignStyle"
  | "moonSignEmotionalSafety"
  | "mercurySignCommunicationRepair"
  | "venusSignAffectionStyle"
  | "marsSignPursuitConflict"
  | "saturnSignDefenseDelay"
  | "functionElementMatrix"
  | "functionModalityMatrix"
  | "relationshipPotential"
  | "elementComparison"
  | "luminaryComparison"
  | "ascendantImpression"
  | "houseRelationshipFactors"
  | "angleHouseFramework"
  | "aspectPriority"
  | "aspectContactModifier"
  | "aspectPairContactTemplate"
  | "aspectPairPhraseTemplateMethod"
  | "aspectFunctionCombination"
  | "aspectInterpretationFoundation"
  | "aspectSynthesisCrossCheck"
  | "relationshipChartLayer"
  | "consultationSafety"
  | "nonfatalSynastrySafety"
  | "relationshipArchetype"
  | "attractionDynamics"
  | "conflictDynamics"
  | "growthDynamics"
  | "partnerNeeds"
  | "fightLandmines"
  | "survivalGuide"
  | "relationshipTurningWindows"
  | "relationshipThesis"
  | "relationshipContextStoryline";

export type WesternAspectContactModifier = {
  type: string;
  aspect: string;
  label: string;
  source: string;
  atomId?: string | null;
  claimIds?: string[];
  interpretation: string;
  doesNotProve: string;
  reducerInstruction: string;
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternAspectPairContactTemplate = {
  id?: string | null;
  label: string;
  source: string;
  atomId?: string | null;
  claimIds?: string[];
  contactType: string;
  interpretation: string;
  doesNotProve: string;
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternAspectEvidence = {
  id: string;
  atomId?: string | null;
  claimIds?: string[];
  category: "attraction" | "emotionalSafety" | "pressure" | "communication" | "repair";
  personAPoint: string;
  personBPoint: string;
  aspect: string;
  aspectLabel: string;
  orb?: number | null;
  maxOrb?: number | null;
  applying: boolean;
  strength: number;
  contactType?: string;
  contactModifier?: WesternAspectContactModifier | null;
  contactModifierLabel?: string | null;
  contactModifierMeaning?: string | null;
  pairContactTemplate?: WesternAspectPairContactTemplate | null;
  pairContactTemplateLabel?: string | null;
  pairContactTemplateMeaning?: string | null;
  readingRole?: string;
  technical: string;
  emotionalMeaning: string;
  doesNotProve: string;
  confidence: CaseConfidence;
  source: string;
  precision: WesternPrecisionGate;
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternTransitEvidence = {
  id: string;
  person: "person_a" | "person_b";
  label: string;
  transitPoint: string;
  natalPoint: string;
  aspect: string;
  orb?: number | null;
  category?: string;
  technical: string;
  emotionalMeaning: string;
  doesNotProve: string;
  confidence: CaseConfidence;
  source: string;
  precision: WesternPrecisionGate;
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternAnswerContractEvidenceItem = {
  kind: "calculation" | "currentTransit" | "context";
  label: string;
  technical: string;
  emotionalMeaning: string;
  doesNotProve: string;
  confidence: CaseConfidence;
  source: string;
  atomId?: string | null;
  claimIds?: string[];
};

export type WesternAnswerEvidenceContract = {
  version: "western-answer-evidence-contract-v1";
  calculationEvidence: WesternAnswerContractEvidenceItem[];
  currentTransitEvidence: WesternAnswerContractEvidenceItem[];
  contextModifier: {
    role?: string;
    canCreateAstrologyConclusion?: boolean;
    requiresCalculationEvidenceForConclusion?: boolean;
    requiresTransitEvidenceForTimingAction?: boolean;
    sourceClaimIds?: string[];
    methodClaimIds?: string[];
    contextEvidenceBoundary?: {
      version: string;
      role: string;
      contextInputs: string[];
      allowedUses: string[];
      cannotSatisfyEvidenceFor: string[];
      canCreateAstrologyConclusion: boolean;
      requiresCalculationEvidenceForConclusion: boolean;
      requiresTransitEvidenceForTimingAction: boolean;
      sourceClaimIds?: string[];
      methodClaimIds?: string[];
    };
    stageKey: string;
    stageLabel: string;
    contactStatusKey: string;
    contactStatusLabel: string;
    actionBoundary: string;
    contactActionScale?: number;
    contactActionMode?: string;
    contactAllowedAction?: string;
    contactBlockedActions?: string[];
    canSuggestDirectContact?: boolean;
    requiresEasyExit?: boolean;
    requiresSharedSpaceBoundary?: boolean;
    requiresCalculationSupport?: boolean;
    timingCanOverrideBoundary?: boolean;
    evidence: WesternAnswerContractEvidenceItem[];
  };
  questionSelector?: {
    version: "western-question-selector-v1";
    questionKey: string;
    role: "evidence_weighting_policy" | string;
    methodClaimIds: string[];
    usesCalculationEvidence?: boolean;
    usesContextAsBoundary?: boolean;
    canCreateAstrologyConclusion?: boolean;
    requiresCalculationEvidenceForConclusion?: boolean;
  };
  synthesis: string;
  contractRules: string[];
  precision: {
    inputQuality?: CaseConfidence;
    timingPrecision?: "analysis_datetime" | "analysis_date_noon_fallback" | string;
  };
};

export type WesternTimingBand = "better" | "neutral" | "avoid";

export type WesternTimingWindowScan = {
  method: "western-transit-window-scan-v1";
  status: "calculated" | "not_calculated";
  scanDays: number;
  granularityDays: number;
  sampleCount: number;
  topBand: WesternTimingBand;
  topBandLabel: string;
  bandCounts: Record<WesternTimingBand, number>;
  betterWindowCount: number;
  avoidWindowCount: number;
  categoryCounts: Record<string, number>;
  exactTimingPolicy: WesternExactTimingPolicy;
  preciseDatesAvailable: false;
  timingSummary: string;
};

export type WesternExactTimingPolicy = {
  precision: "trend_only" | string;
  preciseDatesAvailable: false;
  reason: string;
};

export type WesternFunctionSignStyle = {
  person: "person_a" | "person_b";
  roleLabel: "你" | "對方";
  point: "Sun" | "Moon" | "Mercury" | "Venus" | "Mars" | "Saturn";
  sign: string;
  signLabel: string;
  element?: string;
  elementLabel?: string;
  elementStyle?: string;
  modality?: string;
  modalityLabel?: string;
  modalityStyle?: string;
  style: string;
  confidence: CaseConfidence;
};

export type WesternRepeatedTheme = {
  themeKey: string;
  label: string;
  count: number;
  selectedCount: number;
  contactTypes: string[];
  pairKeys: string[];
  relationshipFunctions: string[];
  selectedEvidenceIds: string[];
  maxStrength: number;
  averageStrength: number;
  interpretation: string;
  reducerInstruction: string;
  doesNotProve: string;
};

export type WesternRepeatedThemeReducer = {
  version: "repeated-theme-reducer-v1";
  source: string;
  methodClaimIds: string[];
  selectedThemeKeys: string[];
  repeatedThemes: WesternRepeatedTheme[];
  reinforcedThemeKeys: string[];
  reinforcedThemeCount: number;
  dominantRepeatedTheme?: WesternRepeatedTheme | null;
  dominantRepeatedThemeKey?: string;
  dominantRepeatedThemeLabel?: string;
  summary: string;
  reducerInstruction: string;
  doesNotProve: string;
  hasRepeatedThemeEvidence: boolean;
  hasRepeatedSaturnPressure?: boolean;
  hasRepeatedEmotionalSafety?: boolean;
  hasRepeatedCommunicationRepair?: boolean;
  hasRepeatedAttractionPursuit?: boolean;
  hasRepeatedActionConflict?: boolean;
  hasRepeatedIdentityRhythm?: boolean;
  hasRepeatedOuterIntensity?: boolean;
};

export type WesternDetectedAspectPairDetail = {
  pairKey: string;
  aspectSource: string;
  contactType: string;
  relationshipFunction: string;
  personAPoint: string;
  personBPoint: string;
  aspect: string;
  orb?: number | null;
  applying: boolean;
  strength: number;
  selectedEvidenceId?: string;
};

export type WesternAspectFunctionCombination = {
  id: string;
  pairKey: string;
  label: string;
  source: string;
  sourceClaimId?: string;
  aspectAtomId?: string | null;
  aspectSource?: string;
  aspectClaimIds?: string[];
  claimIds?: string[];
  personAPoint: string;
  personBPoint: string;
  aspect: string;
  aspectLabel: string;
  orb?: number | null;
  applying: boolean;
  strength: number;
  contactType: string;
  relationshipFunction: string;
  technical: string;
  functionSynthesis: string;
  contactText?: string;
  reducerInstruction: string;
  pointStyles?: WesternFunctionSignStyle[];
  contactModifier?: WesternAspectContactModifier | null;
  pairContactTemplate?: WesternAspectPairContactTemplate | null;
  themeKeys?: string[];
  themeLabels?: string[];
  reinforcedThemeKeys?: string[];
  reinforcedThemeLabels?: string[];
  precision?: WesternPrecisionGate;
};

export type WesternTimingContactReducer = {
  id: string;
  category: string;
  label: string;
  source: string;
  sourceClaimId?: string;
  polarity: "support" | "caution";
  relationshipFunction: string;
  sampleCount: number;
  windowCount: number;
  instruction: string;
  preciseDatesAvailable?: false;
};

export type WesternEvidenceCluster = {
  category: WesternEvidenceClusterCategory;
  label: string;
  atomId?: string | null;
  claimIds?: string[];
  itemCount: number;
  strongestStrength: number;
  averageStrength: number;
  dominantContactType?: string;
  dominantContactModifier?: WesternAspectContactModifier | null;
  contactModifierSummary?: string;
  selectedModifiers?: Array<
    WesternAspectContactModifier & {
      evidenceId?: string | null;
      technical?: string | null;
      strength?: number | null;
    }
  >;
  selectedTemplates?: Array<
    WesternAspectPairContactTemplate & {
      pairKey?: string | null;
      evidenceId?: string | null;
      technical?: string | null;
      strength?: number | null;
    }
  >;
  strongestEvidenceId?: string | null;
  summary: string;
  interpretation: string;
  doesNotProve: string;
  confidence: CaseConfidence;
  source: string;
  allowedCount?: number;
  blockedCount?: number;
  hasAllowedTiming?: boolean;
  windowCount?: number;
  sampleCount?: number;
  topBand?: WesternTimingBand;
  topBandLabel?: string;
  betterCount?: number;
  neutralCount?: number;
  avoidCount?: number;
  betterWindowCount?: number;
  avoidWindowCount?: number;
  hasBetterWindow?: boolean;
  hasAvoidWindow?: boolean;
  supportSignalCount?: number;
  cautionSignalCount?: number;
  hasLowPressureContactWindow?: boolean;
  hasAvoidPressureWindow?: boolean;
  hasMercuryCommunicationWindow?: boolean;
  hasMercuryCommunicationPressure?: boolean;
  hasVenusSofteningWindow?: boolean;
  hasMarsActivationRisk?: boolean;
  hasSaturnBoundaryRisk?: boolean;
  recommendedAction?: string;
  recommendedActionLabel?: string;
  contactMode?: string;
  contactInstruction?: string;
  avoidInstruction?: string;
  lowPressureInstruction?: string;
  selectedTimingReducers?: WesternTimingContactReducer[];
  dominantTimingCategory?: string;
  dominantWindow?: string;
  bandCounts?: Record<string, number>;
  categoryCounts?: Record<string, number>;
  exactTimingPolicy?: WesternExactTimingPolicy;
  preciseDatesAvailable?: false;
  overallQuality?: CaseConfidence;
  hasPrecisionLimit?: boolean;
  exactTimeCount?: number;
  dateOnlyCount?: number;
  locationFallbackCount?: number;
  unavailableCount?: number;
  housesAllowedCount?: number;
  lowMoonConfidenceCount?: number;
  blockedByPrecision?: boolean;
  hasReliableAngles?: boolean;
  personACount?: number;
  personBCount?: number;
  lowConfidenceCount?: number;
  hasBothPeopleNeeds?: boolean;
  point?: "Moon" | "Mercury" | "Venus" | "Mars" | "Saturn";
  selectedSigns?: string[];
  selectedElements?: string[];
  selectedModalities?: string[];
  dominantElement?: string;
  dominantElementLabel?: string;
  dominantModality?: string;
  dominantModalityLabel?: string;
  fireCount?: number;
  earthCount?: number;
  airCount?: number;
  waterCount?: number;
  cardinalCount?: number;
  fixedCount?: number;
  mutableCount?: number;
  hasFireMarsOrVenus?: boolean;
  hasWaterMoonOrVenus?: boolean;
  hasEarthMoonOrSaturn?: boolean;
  hasAirMercuryOrMars?: boolean;
  hasCardinalMarsOrVenus?: boolean;
  hasFixedMoonOrSaturn?: boolean;
  hasMutableMercuryOrMars?: boolean;
  personStyles?: WesternFunctionSignStyle[];
  hasBothPeopleStyle?: boolean;
  selectedPairs?: string[];
  selectedSources?: string[];
  detectedPairs?: string[];
  detectedSources?: string[];
  detectedPairDetails?: WesternDetectedAspectPairDetail[];
  selectedCombinations?: WesternAspectFunctionCombination[];
  repeatedThemeReducer?: WesternRepeatedThemeReducer;
  repeatedThemes?: WesternRepeatedTheme[];
  repeatedThemeSummary?: string;
  dominantRepeatedTheme?: WesternRepeatedTheme | null;
  dominantRepeatedThemeKey?: string;
  dominantRepeatedThemeLabel?: string;
  repeatedThemeMethodClaimIds?: string[];
  hasRepeatedThemeEvidence?: boolean;
  hasRepeatedSaturnPressure?: boolean;
  hasRepeatedEmotionalSafety?: boolean;
  hasRepeatedCommunicationRepair?: boolean;
  hasRepeatedAttractionPursuit?: boolean;
  hasRepeatedActionConflict?: boolean;
  hasRepeatedIdentityRhythm?: boolean;
  hasRepeatedOuterIntensity?: boolean;
  dominantPairKey?: string;
  hasMercurySunHard?: boolean;
  hasMoonSaturnPressure?: boolean;
  hasVenusSaturnPressure?: boolean;
  hasMarsSaturnPressure?: boolean;
  hasSaturnFunctionPressure?: boolean;
  hasHardFunctionCombination?: boolean;
  stageKey?: string;
  stageGroup?: string;
  isBreakupStage?: boolean;
  isActiveStage?: boolean;
  isAmbiguousStage?: boolean;
  isRecentBreakup?: boolean;
  isLongSeparation?: boolean;
  requiresDefinition?: boolean;
  statusKey?: string;
  contactAccess?: string;
  isBlocked?: boolean;
  isNoContact?: boolean;
  hasLimitedContact?: boolean;
  hasLiveContact?: boolean;
  hasContactFriction?: boolean;
  riskKey?: string;
  riskLevel?: number;
  isHighRisk?: boolean;
  isSelfBlaming?: boolean;
  needsSoftTone?: boolean;
  outcomeKey?: string;
  actionPressure?: number;
  wantsReconnect?: boolean;
  wantsDecide?: boolean;
  wantsUnderstand?: boolean;
  wantsRelease?: boolean;
  wantsStabilize?: boolean;
  hasNatalBeforeSynastry?: boolean;
  hasQuestionLast?: boolean;
  hasRelationshipChartDeferred?: boolean;
  naturalElementCount?: number;
  effortElementCount?: number;
  frictionElementCount?: number;
  hasSunMoonContact?: boolean;
  hasSunSunContact?: boolean;
  hasMoonMoonContact?: boolean;
  hasDirectionality?: boolean;
  tightestOrb?: number | null;
  hasTightOrb?: boolean;
  hasHardContactModifier?: boolean;
  hasSoftContactModifier?: boolean;
  hasConjunctionModifier?: boolean;
  hasHardOrConjunctionContact?: boolean;
  hasSoftRepairContact?: boolean;
  hasPairTemplate?: boolean;
  hasHardPairTemplate?: boolean;
  hasSoftPairTemplate?: boolean;
  hasConjunctionPairTemplate?: boolean;
  hasSaturnPairTemplate?: boolean;
  hasMercuryPairTemplate?: boolean;
  hasMoonPairTemplate?: boolean;
  hasPrivacyBoundary?: boolean;
  hasUnsafeContactBlock?: boolean;
  requiresSoftTone?: boolean;
  claimSupport?: CaseFileClaimSupport[];
};

export type WesternRelationshipCaseFile = {
  version: "western-relationship-case-file-v1";
  principle: string;
  calculationSettings: WesternCalculationSettings;
  inputQuality: {
    personA: WesternBirthDataQuality;
    personB: WesternBirthDataQuality;
    overall: CaseConfidence;
  };
  identityLayer: {
    personA: {
      role: "person_a";
      label: "你";
      needs: WesternNeedPoint[];
    };
    personB: {
      role: "person_b";
      label: "對方";
      needs: WesternNeedPoint[];
    };
  };
  synastryLayer: {
    attraction: WesternAspectEvidence[];
    emotionalSafety: WesternAspectEvidence[];
    pressure: WesternAspectEvidence[];
    communication: WesternAspectEvidence[];
    repair: WesternAspectEvidence[];
  };
  evidenceClusters: Record<WesternEvidenceClusterCategory, WesternEvidenceCluster>;
  relationshipInsightLayer?: RelationshipInsightLayer;
  relationshipThesis?: RelationshipThesis;
  relationshipCaseModel?: RelationshipCaseModel;
  relationshipContextStoryline?: RelationshipContextStoryline;
  sectionNarrativeSpecs?: SectionNarrativeSpecBundle;
  houseOverlayLayer?: {
    status: "not_available" | "blocked_by_birth_time" | "blocked_by_location";
    reason: string;
    source?: string;
    claimIds?: string[];
    precisionGate?: WesternHouseAnglePrecisionGate;
  };
  compositeLayer?: {
    status: "not_calculated";
    reason: string;
    source?: string;
    atomId?: string | null;
    claimIds?: string[];
    methodClaimIds?: string[];
    canCreateAstrologyConclusion?: boolean;
    requiresCalculatedRelationshipChart?: boolean;
  };
  timingLayer: {
    currentTransits: WesternTransitEvidence[];
    windowScan: WesternTimingWindowScan;
    methodLimits: string[];
  };
  answerLayer: {
    selectedQuestion: string;
    shortAnswer: string;
    because: string[];
    therefore: string;
    ruleId?: string | null;
    rulesetId?: string | null;
    ruleConfidence?: CaseConfidence | null;
    questionBlueprintId?: string | null;
    questionSourceArticleId?: string | null;
    questionClaimIds?: string[];
    questionMethodClaimIds?: string[];
    questionSelector?: {
      version: "western-question-selector-v1";
      questionKey: string;
      methodClaimIds: string[];
      role: "evidence_weighting_policy" | string;
    };
    answerContract?: string | null;
    evidenceContract?: WesternAnswerEvidenceContract;
    repeatedThemeContext?: RelationshipThemeContext | Record<string, never>;
    includedSections: string[];
  };
  methodGaps: string[];
};

export type CaseFilePerson = {
  role: "person_a" | "person_b";
  label: "你" | "對方";
  bazi: {
    dayMaster: string;
    dayPillar: string;
    monthCommand: string;
    monthCommandMeaning: string;
    strengthLabel: string;
    strengthScore: number;
    strengthSummary: string;
    balanceElements: string[];
    spouseStarSummary: string;
    birthPrecision: string;
  };
  westernNeeds: WesternNeedPoint[];
};

export type CaseFileCrossRole = {
  label: string;
  technical: string;
  emotionalMeaning: string;
};

export type RelationshipCaseDimension = {
  key: "coreAttachment" | "emotionalSafety" | "pressure" | "repair" | "timing";
  title: string;
  summary: string;
  confidence: CaseConfidence;
  baziEvidence: CaseFileEvidence[];
  westernEvidence: CaseFileEvidence[];
  contextEvidence: CaseFileEvidence[];
  emotionalMeaning: string;
  doesNotProve: string;
};

export type RelationshipCaseFile = {
  version: "relationship-case-file-v1";
  principle: string;
  identityLayer: {
    personA: CaseFilePerson;
    personB: CaseFilePerson;
    crossTenGods: CaseFileCrossRole[];
    methodLimits: string[];
  };
  dimensions: {
    coreAttachment: RelationshipCaseDimension;
    emotionalSafety: RelationshipCaseDimension;
    pressure: RelationshipCaseDimension;
    repair: RelationshipCaseDimension;
    timing: RelationshipCaseDimension;
  };
  freeFindingOrder: Array<RelationshipCaseDimension["key"]>;
  paidExpansionFocus: string[];
  methodGaps: string[];
};

export type ReadingBlueprintChapter = {
  id: ReadingChapterId;
  title: string;
  sourceDimensions: Array<RelationshipCaseDimension["key"]>;
  coreSummary: string;
  chapterAngle?: string;
  mustAnswer?: string[];
  doNotRepeat?: string[];
  technicalFocus: string;
  psychologicalFocus: string;
  evidence: CaseFileEvidence[];
  emotionalDirection: string;
  methodBoundary: string;
  forbiddenClaims: string[];
  nextBridge: string;
};

export type ReadingBlueprint = {
  version: "reading-blueprint-v1";
  mainConclusion: string;
  suggestedResultTitle: string;
  resultTitleSeeds: string[];
  titleDirection: string;
  storyArc: string;
  chapterOrder: ReadingChapterId[];
  chapters: ReadingBlueprintChapter[];
  includedReadingPlan: string[];
  includedQuestions?: string[];
  freeChapters?: ReadingBlueprintChapter[];
  paidExpansionPlan?: string[];
  lockedQuestions?: string[];
  forbiddenClaims: string[];
  styleRules: string[];
};

export type ElementBar = {
  label: string;
  value: number;
};

export type EvidencePoint = {
  label: string;
  title: string;
  body: string;
};

export type BaziClimate = {
  title: string;
  headline: string;
  summary: string;
  primary: EvidencePoint;
  gap: EvidencePoint;
  action: string;
  disclaimer: string;
  method: string;
};

export type ElementDistribution = {
  label: string;
  bars: ElementBar[];
};

export type WesternVisual = {
  title: string;
  personA: {
    point: string;
    label: string;
    caption: string;
  };
  personB: {
    point: string;
    label: string;
    caption: string;
  };
  aspect: string;
  orb: string;
  summary: string;
  climateTitle: string;
  climateHeadline: string;
  climateSummary: string;
  disclaimer: string;
};

export type IncludedReadingItem = {
  title: string;
  preview: string[];
  themeKey?: string;
  relationshipThemeLabel?: string;
  source?: string;
  methodClaimIds?: string[];
};

export type PaidUnlockItem = IncludedReadingItem;

export type BaziDiagnosisModuleId = string;

export type BaziDiagnosticFactor = {
  label: string;
  value: string;
  meaning: string;
};

export type BaziDiagnosticPattern = {
  id: string;
  label: string;
  summary: string;
  evidenceTags: string[];
};

export type BaziModuleReading = {
  technicalEvidence: string;
  plainMeaning: string;
  relationshipPattern: string;
  doesNotMean: string;
  actionHint: string;
  methodSource: string;
};

export type BaziDiagnosisModule = {
  id: BaziDiagnosisModuleId;
  title: string;
  score: number;
  level: SignalLevel;
  coreFinding: string;
  factors: BaziDiagnosticFactor[];
  diagnosticTags: string[];
  primaryPattern: string;
  reading: BaziModuleReading;
  technicalSummary: string;
  meaning: string;
  caution: string;
  evidence: string[];
  paidUnlock: string;
};

export type BaziQuestionAnswer = {
  question: string;
  answer: string;
  shortAnswer: string;
  because: string[];
  therefore: string;
  avoid: string[];
  paidUnlock: string[];
};

export type BaziCompatibilityDiagnosis = {
  version: "bazi-compatibility-diagnosis-v1";
  overall: {
    score: number;
    type: string;
    verdict: string;
    summary: string;
  };
  patterns: BaziDiagnosticPattern[];
  modules: BaziDiagnosisModule[];
  questionAnswer: BaziQuestionAnswer;
  methodNotes: string[];
};

export type CompleteRelationshipResultViewModel = {
  contractVersion?: "complete-relationship-result-v1";
  id: string;
  label: string;
  context: Record<string, string>;
  brand: {
    title: string;
    subtitle: string;
  };
  calculationProof?: CalculationProof;
  relationshipCaseFile?: RelationshipCaseFile;
  westernRelationshipCaseFile?: WesternRelationshipCaseFile;
  relationshipProfiles?: RelationshipProfiles;
  relationshipFitLens?: RelationshipFitLens;
  relationshipArchetype?: RelationshipArchetypeBlock;
  attractionDynamics?: RelationshipDynamicsBlock;
  conflictDynamics?: RelationshipDynamicsBlock;
  growthDynamics?: RelationshipDynamicsBlock;
  partnerNeeds?: PartnerNeedsBlock;
  fightLandmines?: FightLandminesBlock;
  survivalGuide?: SurvivalGuideBlock;
  relationshipTurningWindows?: RelationshipTurningWindowsBlock;
  relationshipThesis?: RelationshipThesis;
  relationshipCaseModel?: RelationshipCaseModel;
  relationshipContextStoryline?: RelationshipContextStoryline;
  baziCompatibilityDiagnosis?: BaziCompatibilityDiagnosis;
  readingBlueprint?: ReadingBlueprint;
  relationshipDiagnosis?: RelationshipDiagnosis;
  reading: {
    badge: string;
    question: string;
    stage: string;
    answer: string;
    score: number;
    safety: string;
  };
  metrics: Metric[];
  calculationSteps: CalculationStep[];
  authorityReasons: AuthorityReason[];
  chapterEvidence: {
    thoughts: ChapterEvidence[];
    reasons: ChapterEvidence[];
    chance: ChapterEvidence[];
  };
  insights: Insight[];
  thoughts: string[];
  reasons: ReasonCard[];
  chance: {
    value: number;
    notes: string[];
    nextMove?: string;
    relationshipTheme?: RelationshipThemeContext | Record<string, never>;
    methodClaimIds?: string[];
    selectorEvidenceClusterKeys?: string[];
    questionSelector?: QuestionSelectorTrace;
    readableInterpretation?: ReadableInterpretation;
  };
  timeline: TimelineStep[];
  answerGuidance?: AnswerGuidance;
  normalUserAnswer?: NormalUserAnswer;
  timingGuidance?: TimingGuidance;
  donts: string[];
  readableQuestionAnswer?: ReadableQuestionAnswer;
  actionGuidance?: ActionGuidance;
  finalInterpretation?: FinalReadingInterpretation;
  evidence: {
    bazi?: {
      title: string;
      dayMaster: string;
      signal: string;
      summary: string;
      points: EvidencePoint[];
      climate: BaziClimate;
      pillarsA: Pillars;
      pillarsB: Pillars;
      elementDistributions: ElementDistribution[];
    };
    western: {
      title: string;
      signal: string;
      summary: string;
      visual: WesternVisual;
      points: EvidencePoint[];
      chips: string[];
      aspects: Array<{
        label: string;
        value: string;
        meaning: string;
      }>;
    };
  };
  includedReadingRows: IncludedReadingItem[];
  lockedRows?: IncludedReadingItem[];
  sources: string[];
  debug: {
    stageSlot: string | null;
    questionSlot: string | null;
    baziSlot?: string | null;
    westernSlot: string | null;
    safetySlot?: string | null;
    calculationWarnings?: string[];
    engineVersions?: Record<string, string | null>;
    structuredKbSource?: "local" | "supabase";
  };
};

export type FreeResultViewModel = CompleteRelationshipResultViewModel;
