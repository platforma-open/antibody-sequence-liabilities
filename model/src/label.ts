// Abbreviations for liability types
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
  'Missing Cysteines': 'MissCys',
  'Extra Cysteines': 'ExtraCys',
};

// PTM types
const ptmTypes = new Set([
  'Deamidation (N[GS])',
  'Isomerization (D[DGHST])',
  'N-linked Glycosylation (N[^P][ST])',
  'Tryptophan Oxidation (W)',
  'Methionine Oxidation (M)',
]);

// Fragmentation types
const fragTypes = new Set([
  'Fragmentation (DP)',
  'Hydrolysis (NP)',
  'Fragmentation (TS)',
]);

export function getDefaultBlockLabel(data: {
  liabilityTypes: string[];
  allLiabilityTypes: string[];
}) {
  const selectedTypes = data.liabilityTypes;
  if (!selectedTypes || selectedTypes.length === 0) {
    return '';
  }

  // If all liability types are selected, show "All"
  if (selectedTypes.length === data.allLiabilityTypes.length) {
    return 'All';
  }

  const selectedSet = new Set(selectedTypes);
  // Check if all selected types are PTM types
  const allSelectedArePTM = selectedTypes.every((t) => ptmTypes.has(t));
  // Check if all PTM types are selected
  const allPTMSelected = Array.from(ptmTypes).every((t) => selectedSet.has(t));
  // Check if all selected types are Frag types
  const allSelectedAreFrag = selectedTypes.every((t) => fragTypes.has(t));
  // Check if all Frag types are selected
  const allFragSelected = Array.from(fragTypes).every((t) => selectedSet.has(t));

  if (allPTMSelected && allFragSelected) {
    return 'PTM+Frag';
  } else if (allSelectedArePTM && allPTMSelected) {
    return 'PTM';
  } else if (allSelectedAreFrag && allFragSelected) {
    return 'Frag';
  } else {
    // Build label from abbreviations
    const abbrevs = selectedTypes.map((t) => abbreviations[t] || t.substring(0, 4));
    if (abbrevs.length <= 2) {
      // Show all shortcuts if 1 or 2 liabilities selected
      return abbrevs.join('+');
    } else {
      // Show first two + count of remaining types
      const remainingCount = abbrevs.length - 2;
      return `${abbrevs[0]}+${abbrevs[1]}+${remainingCount} type(s)`;
    }
  }
}
