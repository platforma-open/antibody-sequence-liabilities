const abbreviations: Record<string, string> = {
  'Deamidation (N[GS])': 'Deam(N[GS])',
  'Fragmentation (DP)': 'Frag(DP)',
  'Isomerization (D[DGHST])': 'Isom',
  'N-linked Glycosylation (N[^P][ST])': 'Glyc',
  'Deamidation (N[AHNT])': 'Deam(N[AHNT])',
  'Hydrolysis (NP)': 'Hydro',
  'Fragmentation (TS)': 'Frag(TS)',
  'Tryptophan Oxidation (W)': 'TrpOx',
  'Methionine Oxidation (M)': 'MetOx',
  'Deamidation ([STK]N)': 'Deam([STK]N)',
  'Integrin binding': 'IntBind',
  'Missing Cysteines': 'MissCys',
  'Extra Cysteines': 'ExtraCys',
};

// Drives the "Structural liabilities" output column (None / Present)
const structuralTypes = new Set([
  'Missing Cysteines',
  'Extra Cysteines',
]);

// Drives the "Developability risk" and "Developability score" output columns
const developabilityTypes = new Set([
  'Deamidation (N[GS])',
  'Fragmentation (DP)',
  'Isomerization (D[DGHST])',
  'N-linked Glycosylation (N[^P][ST])',
  'Deamidation (N[AHNT])',
  'Hydrolysis (NP)',
  'Fragmentation (TS)',
  'Tryptophan Oxidation (W)',
  'Methionine Oxidation (M)',
  'Deamidation ([STK]N)',
  'Integrin binding',
]);

// Distinguishes two liabilities blocks on the same dataset differing only in scope. Omitted
// when the scan covers everything, so the common case keeps its short label.
function regionScopeSuffix(regions: string[] | undefined, allRegionNames: readonly string[]): string {
  if (!regions || regions.length === 0) return '';
  const scoped = allRegionNames.filter((r) => regions.includes(r));
  if (scoped.length === 0 || scoped.length === allRegionNames.length) return '';
  // The expected common scope; named rather than listed to keep the label short.
  const isAllCDRs = scoped.length === 3 && scoped.every((r) => r.startsWith('CDR'));
  return isAllCDRs ? ' @CDRs' : ` @${scoped.join('/')}`;
}

export function getDefaultBlockLabel(data: {
  usePredefinedLiabilities: boolean;
  disabledPredefinedLiabilities: string[];
  allLiabilityTypes: string[];
  customLiabilities: { name: string }[];
  regions?: string[];
  allRegions?: readonly string[];
}) {
  const base = getLiabilitySetLabel(data);
  // Nothing scanned at all — a scope suffix on an empty base would describe nothing.
  if (base === '') return '';
  return `${base}${regionScopeSuffix(data.regions, data.allRegions ?? [])}`;
}

function getLiabilitySetLabel(data: {
  usePredefinedLiabilities: boolean;
  disabledPredefinedLiabilities: string[];
  allLiabilityTypes: string[];
  customLiabilities: { name: string }[];
}) {
  const customCount = data.customLiabilities.length;
  const customSuffix = customCount === 1 ? ' + 1 Custom' : customCount > 1 ? ` + ${customCount} Custom` : '';

  const disabledSet = new Set(data.disabledPredefinedLiabilities);
  const activePredefined = data.usePredefinedLiabilities
    ? data.allLiabilityTypes.filter((t) => !disabledSet.has(t))
    : [];

  if (activePredefined.length === 0 && customCount === 0) {
    return '';
  }

  if (activePredefined.length === 0) {
    return customCount === 1 ? '1 Custom' : `${customCount} Custom`;
  }

  // Integrin binding is off by default — treat it as optional for the "all" label
  const coreTypes = data.allLiabilityTypes.filter((t) => t !== 'Integrin binding');
  const activeCoreTypes = activePredefined.filter((t) => t !== 'Integrin binding');
  if (activeCoreTypes.length === coreTypes.length) {
    return `All Predefined${customSuffix}`;
  }

  const activeSet = new Set(activePredefined);
  const hasStructural = Array.from(structuralTypes).every((t) => activeSet.has(t));
  const hasDevability = Array.from(developabilityTypes).every((t) => activeSet.has(t));
  const onlyStructural = activePredefined.every((t) => structuralTypes.has(t));
  const onlyDevability = activePredefined.every((t) => developabilityTypes.has(t));

  if (hasStructural && hasDevability) {
    return `Struct+Dev${customSuffix}`;
  }
  if (onlyStructural && hasStructural) {
    return `Structural${customSuffix}`;
  }
  if (onlyDevability && hasDevability) {
    return `Developability${customSuffix}`;
  }

  const abbrevs = activePredefined.map((t) => abbreviations[t] ?? t.substring(0, 4));
  const predefinedLabel
    = abbrevs.length <= 2
      ? abbrevs.join('+')
      : `${abbrevs[0]}+${abbrevs[1]}+${abbrevs.length - 2} more`;

  return `${predefinedLabel}${customSuffix}`;
}
