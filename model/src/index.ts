import type {
  ImportFileHandle,
  PColumnSpec,
  PlDataTableStateV2,
  PlRef,
} from '@platforma-sdk/model';
import {
  BlockModelV3,
  DataColumn,
  DataModelBuilder,
  createPlDataTableStateV2,
  createPlDataTableV3,
} from '@platforma-sdk/model';
import { getDefaultBlockLabel } from './label';
export type * from '@milaboratories/helpers';

export type Modality = 'antibody' | 'peptide' | 'amplicon';

export type CustomLiability = {
  name: string;
  pattern: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  fixability: 'easily_fixable' | 'fixable' | 'hard_to_fix';
  regions: string[];
};

type OldArgs = {
  defaultBlockLabel: string;
  customBlockLabel: string;
  inputAnchor?: PlRef;
  usePredefinedLiabilities?: boolean;
  disabledPredefinedLiabilities?: string[];
  customLiabilities?: CustomLiability[];
  importFileHandle?: ImportFileHandle;
  mem?: number;
};

type OldUiState = {
  tableState: PlDataTableStateV2;
};

/** Canonical VDJ region names, in biological order. Mirrors REGION_ORDER_MAP in definitions.py. */
export const allRegions = ['FR1', 'CDR1', 'FR2', 'CDR2', 'FR3', 'CDR3', 'FR4'] as const;
export type Region = (typeof allRegions)[number];

export type BlockData = {
  defaultBlockLabel: string;
  customBlockLabel: string;
  inputAnchor?: PlRef;
  modality?: Modality;
  usePredefinedLiabilities?: boolean;
  disabledPredefinedLiabilities?: string[];
  customLiabilities?: CustomLiability[];
  /** Undefined or empty = scan everything, the pre-feature behaviour — hence absent from
   *  `init()`. Antibody only; whole-sequence modes have no regions. */
  regions?: string[];
  importFileHandle?: ImportFileHandle;
  mem?: number;
  tableState: PlDataTableStateV2;
};

export const liabilityTypes: {
  value: string;
  label: string;
  pattern: string;
  riskLevel: 'Low' | 'Medium' | 'High';
  fixability: 'easily_fixable' | 'fixable' | 'hard_to_fix' | 'structural';
  enabledByDefault: boolean;
  /** Modalities for which this rule is offered. */
  applicableTo: Modality[];
}[] = [
  { value: 'Deamidation (N[GS])', label: 'Deamidation (N[GS])', pattern: 'N[GS]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Fragmentation (DP)', label: 'Fragmentation (DP)', pattern: 'DP', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Isomerization (D[DGHST])', label: 'Isomerization (D[DGHST])', pattern: 'D[DGHST]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'N-linked Glycosylation (N[^P][ST])', label: 'N-linked Glycosylation (N[^P][ST])', pattern: 'N[^P][ST]', riskLevel: 'High', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody'] },
  { value: 'Deamidation (N[AHNT])', label: 'Deamidation (N[AHNT])', pattern: 'N[AHNT]', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Hydrolysis (NP)', label: 'Hydrolysis (NP)', pattern: 'NP', riskLevel: 'Medium', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Fragmentation (TS)', label: 'Fragmentation (TS)', pattern: 'TS', riskLevel: 'Medium', fixability: 'fixable', enabledByDefault: true, applicableTo: ['antibody'] },
  { value: 'Tryptophan Oxidation (W)', label: 'Tryptophan Oxidation (W)', pattern: 'W', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Methionine Oxidation (M)', label: 'Methionine Oxidation (M)', pattern: 'M', riskLevel: 'Medium', fixability: 'easily_fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Deamidation ([STK]N)', label: 'Deamidation ([STK]N)', pattern: '[STK]N', riskLevel: 'Low', fixability: 'easily_fixable', enabledByDefault: true, applicableTo: ['antibody', 'peptide'] },
  { value: 'Integrin binding', label: 'Integrin binding', pattern: 'RGD|RYD|KGD|NGR|LDV|DGE|GPR', riskLevel: 'Low', fixability: 'easily_fixable', enabledByDefault: false, applicableTo: ['antibody', 'peptide'] },
  { value: 'Missing Cysteines', label: 'Missing Cysteines', pattern: '—', riskLevel: 'High', fixability: 'structural', enabledByDefault: true, applicableTo: ['antibody'] },
  { value: 'Extra Cysteines', label: 'Extra Cysteines', pattern: '—', riskLevel: 'High', fixability: 'hard_to_fix', enabledByDefault: true, applicableTo: ['antibody'] },
];

const defaultDisabled = liabilityTypes.filter((l) => !l.enabledByDefault).map((l) => l.value);
const allLiabilityTypeValues = liabilityTypes.map((l) => l.value);
const predefinedLiabilityNames = new Set(allLiabilityTypeValues);

const dataModel = new DataModelBuilder()
  .from<BlockData>('v1')
  .upgradeLegacy<OldArgs, OldUiState>(({ args, uiState }) => ({
    ...args,
    tableState: uiState.tableState,
  }))
  .init(() => ({
    defaultBlockLabel: getDefaultBlockLabel({
      usePredefinedLiabilities: true,
      disabledPredefinedLiabilities: defaultDisabled,
      allLiabilityTypes: allLiabilityTypeValues,
      customLiabilities: [],
    }),
    customBlockLabel: '',
    usePredefinedLiabilities: true,
    disabledPredefinedLiabilities: defaultDisabled,
    customLiabilities: [],
    tableState: createPlDataTableStateV2(),
  }));

export const platforma = BlockModelV3.create(dataModel)

  .args((data) => {
    if (!data.inputAnchor) throw new Error('Input anchor is required');

    const customs = data.customLiabilities ?? [];
    const customNames = customs.map((c) => c.name);
    if (customNames.length !== new Set(customNames).size) throw new Error('Duplicate custom liability names');
    for (const c of customs) {
      if (!c.name || !c.pattern) throw new Error('Custom liability must have name and pattern');
      if (predefinedLiabilityNames.has(c.name)) throw new Error(`"${c.name}" collides with predefined liability name`);
      try {
        new RegExp(c.pattern);
      } catch {
        throw new Error(`Invalid regex: "${c.pattern}"`);
      }
      // Antibody mode: regions selection is required. Whole-sequence modes
      // (peptide / amplicon): regions unused (whole-sequence regex), so empty
      // list is valid.
      // data.modality defaults to undefined until synced; treat as antibody (conservative).
      const wholeSeq = data.modality === 'peptide' || data.modality === 'amplicon';
      if (!wholeSeq && (!c.regions || c.regions.length === 0))
        throw new Error(`Custom liability "${c.name}" must have at least one region selected`);
    }

    // Suppressed in whole-sequence modes and canonicalized to biological order, so that
    // semantically-identical scopes yield identical args bytes and never mark the block stale.
    const wholeSeqModality = data.modality === 'peptide' || data.modality === 'amplicon';
    const selectedRegions = wholeSeqModality ? undefined : data.regions;
    const regions
      = selectedRegions && selectedRegions.length > 0
        ? allRegions.filter((r) => selectedRegions.includes(r))
        : undefined;

    return {
      defaultBlockLabel: data.defaultBlockLabel,
      customBlockLabel: data.customBlockLabel,
      inputAnchor: data.inputAnchor,
      usePredefinedLiabilities: data.usePredefinedLiabilities,
      disabledPredefinedLiabilities: data.disabledPredefinedLiabilities,
      customLiabilities: data.customLiabilities,
      regions,
      importFileHandle: data.importFileHandle,
      mem: data.mem,
    };
  })

  // prerunArgs allows file import to run independently of whether inputAnchor is set
  .prerunArgs((data) => ({ importFileHandle: data.importFileHandle }))

  .output('inputOptions', (ctx) =>
    ctx.resultPool.getOptions([{
      axes: [
        { name: 'pl7.app/sampleId' },
        { name: 'pl7.app/vdj/clonotypeKey' },
      ],
      annotations: { 'pl7.app/isAnchor': 'true' },
    }, {
      axes: [
        { name: 'pl7.app/sampleId' },
        { name: 'pl7.app/vdj/scClonotypeKey' },
      ],
      annotations: { 'pl7.app/isAnchor': 'true' },
    }, {
      axes: [
        { name: 'pl7.app/sampleId' },
        { name: 'pl7.app/variantKey' },
      ],
      annotations: { 'pl7.app/isAnchor': 'true' },
    }]),
  )

  .output('modality', (ctx) => {
    const ref = ctx.data.inputAnchor;
    if (ref === undefined) return undefined;
    const spec = ctx.resultPool.getPColumnSpecByRef(ref);
    if (!spec) return undefined;
    const axis1 = spec.axesSpec[1];
    if (axis1?.name !== 'pl7.app/variantKey') return 'antibody';
    // Three producers key on this axis and only the run-id in its domain separates them.
    // import-vdj-data's bare antibody sets stamp pl7.app/vdj/clonotypingRunId; they are
    // antibody, and calling them peptide picked the peptide liability list and let a custom
    // liability through with no regions selected — meaningless for per-region scanning.
    const domain = axis1.domain ?? {};
    if (domain['pl7.app/repertoire/extractionRunId'] !== undefined) return 'amplicon';
    if (domain['pl7.app/vdj/clonotypingRunId'] !== undefined) return 'antibody';
    return 'peptide';
  }, { retentive: true })

  /** Regions with an upstream sequence column, plus CDR1-3/FR1 which main.py extracts from an
   *  annotation column and so has none. Full list when nothing is found — specs may be loading. */
  .output('availableRegions', (ctx) => {
    const ref = ctx.data.inputAnchor;
    if (ref === undefined) return undefined;

    const cols = ctx.resultPool.getAnchoredPColumns(
      { main: ref },
      (spec: PColumnSpec) =>
        spec.name === 'pl7.app/vdj/sequence'
        && spec.domain?.['pl7.app/alphabet'] === 'aminoacid',
    );

    const found = new Set<string>();
    for (const col of cols ?? []) {
      const rawFeature = col.spec.domain?.['pl7.app/vdj/feature'];
      const feature = rawFeature === 'FR4InFrame' ? 'FR4' : rawFeature;
      if (feature !== undefined && (allRegions as readonly string[]).includes(feature)) {
        found.add(feature);
      }
    }

    // Regions are extracted only from CDRs annotations, which carry the CDR boundaries
    const annotationCols = ctx.resultPool.getAnchoredPColumns(
      { main: ref },
      (spec: PColumnSpec) =>
        spec.name === 'pl7.app/vdj/sequence/annotation'
        && spec.annotations?.['pl7.app/sequence/isAnnotation'] === 'true'
        && spec.domain?.['pl7.app/sequence/annotation/type'] === 'CDRs'
        && spec.domain?.['pl7.app/alphabet'] === 'aminoacid',
    );
    if (annotationCols !== undefined && annotationCols.length > 0) {
      // Mirrors extract_cdrs_fr1 / expected_regions in main.py.
      for (const r of ['CDR1', 'CDR2', 'CDR3', 'FR1']) found.add(r);
    }

    if (found.size === 0) return [...allRegions];
    return allRegions.filter((r) => found.has(r));
  }, { retentive: true })

  .outputWithStatus('pt', (ctx) => {
    const pCols = ctx.outputs?.resolve('outputLiabilities')?.getPColumns();
    if (pCols === undefined || pCols.length === 0) {
      return undefined;
    }
    return createPlDataTableV3(ctx, {
      primaryColumns: [DataColumn.fromColumn(pCols[0])],
      columns: pCols.slice(1).map((c) => DataColumn.fromColumn(c)),
      tableState: ctx.data.tableState,
    });
  })

  .output('isRunning', (ctx) => ctx.outputs?.getIsReadyOrError() === false)

  // isActive forces this output to be evaluated even when nothing subscribes to it.
  // That evaluation is what drives the file upload: getImportProgress() causes the
  // underlying context to begin the upload for each pending ImportFileHandle.
  // Without isActive, the output is never rendered and the prerun never resolves.
  .output('prerunFileImports', (ctx) => {
    return Object.fromEntries(
      ctx.prerun
        ?.resolve({ field: 'fileImports', assertFieldType: 'Input' })
        ?.mapFields(
          (handle, acc) => [handle as ImportFileHandle, acc.getImportProgress()],
          { skipUnresolved: true },
        ) ?? [],
    );
  }, { isActive: true })

  // Blob handle for the uploaded file, readable by ReactiveFileContent in the UI
  .retentiveOutput('importedFile', (ctx) =>
    ctx.prerun?.traverse({ field: 'importedFile' })?.getFileHandle(),
  )

  .title(() => 'Sequence Liabilities')

  .subtitle((ctx) => ctx.data.customBlockLabel || ctx.data.defaultBlockLabel)

  .sections((_) => [
    { type: 'link', href: '/', label: 'Table' },
  ])

  .done();

export { getDefaultBlockLabel } from './label';
export { allLiabilityTypeValues, predefinedLiabilityNames };
